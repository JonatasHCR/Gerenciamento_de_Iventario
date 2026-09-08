"""Backup, restauração e limpeza do banco — a tela de Administração.

`pg_dump`/`pg_restore` rodam neste container. Mandar num sidecar exigiria o
socket do Docker, o que daria a qualquer falha no app o poder de criar
containers na máquina.

Os arquivos caem no diretório do sidecar, então os agendados e os do botão
ficam na mesma lista.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.settings import Settings

DIRETORIO_BACKUPS = Path(os.environ.get('BACKUP_DIR', '/backups'))

# Só nomes gerados por nós. Fecha a porta para `../../etc/passwd` chegar ao
# download ou à restauração por um parâmetro de rota.
NOME_VALIDO = re.compile(r'^[A-Za-z0-9._-]+\.(dump|sql\.gz|sql)$')


# O `pg_restore` sai com código 1 se ignorou QUALQUER erro, inclusive o
# inofensivo `SET transaction_timeout` que o cliente 17 escreve e o servidor 16
# não conhece. Aceitar o código em bloco daria por boa uma restauração que
# perdeu tabelas; tolerar pelo nome, não.
TOLERADOS_NO_RESTORE = ('unrecognized configuration parameter "transaction_timeout"',)

# O mesmo problema, do lado do dump em texto: o pg_dump 17 escreve
# `SET transaction_timeout` no cabecalho e o servidor 16 nao conhece o
# parametro. No formato custom o pg_restore apenas avisa; num .sql lido pelo
# psql com ON_ERROR_STOP a restauracao morreria na primeira linha, entao a
# linha e retirada do arquivo antes de ele chegar ao psql.
PREFIXO_INCOMPATIVEL = b'SET transaction_timeout'


class ErroDeManutencao(RuntimeError):
    """Falha esperada, para virar 4xx/5xx com mensagem útil."""


@dataclass(frozen=True)
class Backup:
    nome: str
    bytes: int
    criado_em: datetime


# Ordem de dependência: filhos antes dos pais. Duas ausências deliberadas:
#   `tb_contratos` — a receita é a dona; limpar aqui seria desfeito no próximo
#     sync. Para tirar um CC, remova-o lá.
#   `tb_users` — levaria junto o histórico e o vínculo com o Keycloak. Para
#     tirar alguém, remova-o do grupo no portal.
ALVOS: dict[str, dict] = {
    'eletronicos': {
        'rotulo': 'Eletrônicos (e vínculos, cessões e solicitações deles)',
        'tabelas': [
            'tb_associacao_user_eletronico',
            'tb_cessao_eletronico',
            'tb_cessao_periferico',
            'tb_solicitacao_eletronico',
            'tb_solicitacao_periferico',
            'tb_eletronicos',
        ],
        'aceita_cc': True,
    },
    'cessoes': {
        'rotulo': 'Cessões (histórico de movimentação)',
        'tabelas': ['tb_cessao_eletronico', 'tb_cessao_periferico', 'tb_cessoes'],
        'aceita_cc': True,
    },
    'solicitacoes': {
        'rotulo': 'Solicitações',
        'tabelas': [
            'tb_solicitacao_eletronico',
            'tb_solicitacao_periferico',
            'tb_solicitacoes',
        ],
        'aceita_cc': True,
    },
    'catalogo': {
        'rotulo': 'Catálogo (marcas, modelos, tipos e localizações)',
        'tabelas': [
            'tb_marcas',
            'tb_modelos',
            'tb_tipos_eletronico',
            'tb_localizacoes',
        ],
        'aceita_cc': False,
    },
    'auditoria': {
        'rotulo': 'Auditoria (histórico de alterações)',
        'tabelas': ['tb_audit_log'],
        'aceita_cc': False,
    },
    'tudo': {
        'rotulo': 'Tudo (dados de negócio — NÃO inclui usuários, '
                  'centros de custo nem auditoria)',
        'tabelas': [
            'tb_associacao_user_eletronico',
            'tb_cessao_eletronico',
            'tb_cessao_periferico',
            'tb_solicitacao_eletronico',
            'tb_solicitacao_periferico',
            'tb_cessoes',
            'tb_solicitacoes',
            'tb_eletronicos',
        ],
        'aceita_cc': False,
    },
}

# Como cada tabela se liga a um centro de custo, quando o filtro é usado.
FILTRO_POR_CC: dict[str, str] = {
    'tb_eletronicos': 'centro_custo = :cc',
    'tb_cessoes': 'centro_custo_destino = :cc',
    'tb_solicitacoes': 'centro_custo = :cc OR centro_custo_destino = :cc',
    'tb_associacao_user_eletronico':
        'eletronico_id IN (SELECT id FROM tb_eletronicos WHERE centro_custo = :cc)',
    'tb_cessao_eletronico':
        'cessao_id IN (SELECT id FROM tb_cessoes WHERE centro_custo_destino = :cc)',
    'tb_cessao_periferico':
        'cessao_id IN (SELECT id FROM tb_cessoes WHERE centro_custo_destino = :cc)',
    'tb_solicitacao_eletronico':
        'solicitacao_id IN (SELECT id FROM tb_solicitacoes '
        'WHERE centro_custo = :cc OR centro_custo_destino = :cc)',
    'tb_solicitacao_periferico':
        'solicitacao_id IN (SELECT id FROM tb_solicitacoes '
        'WHERE centro_custo = :cc OR centro_custo_destino = :cc)',
}


class ManutencaoService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None):
        self.session = session
        self.settings = settings or Settings()

    # -- utilidades ---------------------------------------------------------

    def _ambiente_pg(self) -> dict[str, str]:
        return {**os.environ, 'PGPASSWORD': self.settings.DB_PASSWORD}

    def _conexao(self) -> list[str]:
        return [
            '-h', self.settings.DB_HOST,
            '-p', str(self.settings.DB_PORT),
            '-U', self.settings.DB_USER,
            '-d', self.settings.DB_NAME,
        ]

    async def _rodar(self, *args: str, tolerar: tuple[str, ...] = ()) -> str:
        """Roda um utilitário do Postgres. Devolve o stderr; levanta se falhou.

        O código de saída sozinho não serve de veredito — ver
        TOLERADOS_NO_RESTORE.
        """
        processo = await asyncio.create_subprocess_exec(
            *args,
            env=self._ambiente_pg(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, saida = await processo.communicate()
        erro = saida.decode(errors='replace').strip()
        if processo.returncode == 0:
            return erro

        linhas = [linha for linha in erro.splitlines() if ': error: ' in linha]
        graves = [
            linha for linha in linhas
            if not any(trecho in linha for trecho in tolerar)
        ]
        # Sem nenhuma linha de erro reconhecível a falha é desconhecida, e dá-la
        # por boa seria pior do que reclamar sem saber o motivo.
        if graves or not linhas:
            detalhe = (graves or erro.splitlines() or ['sem detalhe'])[-1]
            raise ErroDeManutencao(f'{args[0]} falhou: {detalhe}')

        return erro

    def resolver_arquivo(self, nome: str) -> Path:
        """Traduz um nome de backup em caminho, recusando qualquer travessia."""
        if not NOME_VALIDO.match(nome):
            raise ErroDeManutencao('Nome de arquivo inválido.')

        caminho = (DIRETORIO_BACKUPS / nome).resolve()
        if caminho.parent != DIRETORIO_BACKUPS.resolve() or not caminho.is_file():
            raise ErroDeManutencao('Backup não encontrado.')
        return caminho

    # -- operações ----------------------------------------------------------

    def listar(self) -> list[Backup]:
        if not DIRETORIO_BACKUPS.is_dir():
            return []

        achados = [
            Backup(
                nome=f.name,
                bytes=f.stat().st_size,
                criado_em=datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc),
            )
            for f in DIRETORIO_BACKUPS.iterdir()
            if f.is_file() and NOME_VALIDO.match(f.name)
        ]
        return sorted(achados, key=lambda b: b.criado_em, reverse=True)

    async def gerar_backup(self) -> Backup:
        DIRETORIO_BACKUPS.mkdir(parents=True, exist_ok=True)
        nome = f'inventario-{datetime.now().strftime("%Y%m%d-%H%M%S")}.sql'
        destino = DIRETORIO_BACKUPS / nome

        # Texto puro (formato padrao do pg_dump), o mesmo do sidecar e do
        # scripts/backup.sh — um so formato para as tres origens.
        # --clean/--if-exists embutem os DROP no proprio arquivo, que e o que
        # torna a restauracao sobre um banco povoado possivel com psql.
        await self._rodar(
            'pg_dump',
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            *self._conexao(),
            '-f', str(destino),
        )

        if not destino.is_file() or destino.stat().st_size == 0:
            raise ErroDeManutencao('O pg_dump terminou mas não gerou arquivo.')

        return Backup(
            nome=nome,
            bytes=destino.stat().st_size,
            criado_em=datetime.now(timezone.utc),
        )

    async def restaurar(self, nome: str) -> str:
        """Substitui os dados atuais pelos do arquivo. Irreversível."""
        arquivo = self.resolver_arquivo(nome)

        # O pg_restore derruba as tabelas que a sessão mantém abertas, e uma
        # conexão presa vira deadlock.
        await self.session.close()

        # Os backups novos sao .sql; os .dump antigos continuam restauraveis
        # para nao inutilizar o que ja esta na pasta.
        if arquivo.suffix == '.dump':
            await self._rodar(
                'pg_restore',
                '--clean',
                '--if-exists',
                '--no-owner',
                '--no-privileges',
                *self._conexao(),
                str(arquivo),
                tolerar=TOLERADOS_NO_RESTORE,
            )
        else:
            await self._restaurar_sql(arquivo)

        return arquivo.name

    async def _restaurar_sql(self, arquivo: Path) -> None:
        """Aplica um dump em texto com psql, abortando no primeiro erro."""
        limpo = await asyncio.to_thread(self._sem_linhas_incompativeis, arquivo)
        try:
            # ON_ERROR_STOP=1: sem isto o psql segue apos um erro e devolveria
            # codigo 0 depois de restaurar pela metade.
            await self._rodar(
                'psql',
                '-v', 'ON_ERROR_STOP=1',
                '-q',
                *self._conexao(),
                '-f', str(limpo),
            )
        finally:
            limpo.unlink(missing_ok=True)

    @staticmethod
    def _sem_linhas_incompativeis(arquivo: Path) -> Path:
        """Copia o dump sem as linhas que o servidor nao entende."""
        with tempfile.NamedTemporaryFile(
            'wb', suffix='.sql', delete=False
        ) as destino:
            with arquivo.open('rb') as fonte:
                for linha in fonte:
                    if linha.lstrip().startswith(PREFIXO_INCOMPATIVEL):
                        continue
                    destino.write(linha)
            return Path(destino.name)

    async def limpar(
        self, alvo: str, centro_custo: str | None = None
    ) -> dict[str, int]:
        """Apaga dados de negócio. Devolve quantas linhas saíram de cada tabela."""
        config = ALVOS.get(alvo)
        if config is None:
            raise ErroDeManutencao(f'Alvo de limpeza inválido: {alvo!r}.')

        cc = (centro_custo or '').strip() or None
        if cc and not config['aceita_cc']:
            raise ErroDeManutencao(
                f'O alvo "{config["rotulo"]}" não aceita filtro por centro de custo.'
            )

        removidos: dict[str, int] = {}
        for tabela in config['tabelas']:
            if cc and tabela in FILTRO_POR_CC:
                comando = text(f'DELETE FROM {tabela} WHERE {FILTRO_POR_CC[tabela]}')
                parametros = {'cc': cc}
            elif cc:
                # Sem ligação com CC: pular é mais seguro que apagar inteira.
                continue
            else:
                comando = text(f'DELETE FROM {tabela}')
                parametros = {}

            resultado = await self.session.execute(comando, parametros)
            removidos[tabela] = resultado.rowcount or 0

        await self.session.commit()
        return removidos
