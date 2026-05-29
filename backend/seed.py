"""
Script de seed — popula o banco com dados de teste diversificados.
Idempotente: usa ON CONFLICT DO NOTHING, pode rodar mais de uma vez.

Uso:
    docker compose exec backend python seed.py
    teste
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.core.settings import Settings
from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.associacao_user_eletronico import AssociacaoUserEletronico
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.localizacao import Localizacao
from backend.model.tipo_eletronico import TipoEletronico
from backend.model.user import User
from backend.security.security import Security

settings = Settings()
security = Security()


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

USUARIOS = [
    # (nome, email, senha_plain, tipo)
    ('Admin UFC', 'admin@ufc.br', 'admin123', 'Admin'),
    ('Carlos Silva', 'carlos.ti@ufc.br', 'carlos123', 'Tecnico_TI'),
    ('Roberto Santos', 'roberto.gestor@ufc.br', 'roberto123', 'Gestor'),
    ('Ana Oliveira', 'ana.gestor@ufc.br', 'ana123', 'Gestor'),
    ('Marcos Lima', 'marcos.gestor@ufc.br', 'marcos123', 'Gestor'),
    ('Fernanda Costa', 'fernanda.gestor@ufc.br', 'fernanda123', 'Gestor'),
    ('Pedro Alves', 'pedro.sub@ufc.br', 'pedro123', 'Subgestor'),
    ('Julia Mendes', 'julia.sub@ufc.br', 'julia123', 'Subgestor'),
    ('Lucas Pereira', 'lucas.func@ufc.br', 'lucas123', 'Funcionario'),
    ('Maria Souza', 'maria.func@ufc.br', 'maria123', 'Funcionario'),
    ('João Ferreira', 'joao.func@ufc.br', 'joao123', 'Funcionario'),
    ('Patrícia Lima', 'patricia.func@ufc.br', 'patricia123', 'Funcionario'),
    ('Diego Rodrigues', 'diego.func@ufc.br', 'diego123', 'Funcionario'),
]

CONTRATOS = [
    ('INFR', 'Infraestrutura e Redes'),
    ('LABI', 'Laboratório de Informática'),
    ('ADMI', 'Administração Geral'),
    ('BLIO', 'Biblioteca e Acervo'),
]

LOCALIZACOES = [
    ('Sala de TI', 'Andar 1 — setor de infraestrutura'),
    ('Lab. Computação A', 'Laboratório principal, andar 2'),
    ('Lab. Computação B', 'Laboratório secundário, andar 2'),
    ('Sala da Direção', 'Diretoria — acesso restrito'),
    ('Secretaria', 'Secretaria geral do departamento'),
    ('Almoxarifado', 'Depósito de equipamentos e suprimentos'),
    ('Recepção', 'Recepção do bloco principal'),
    ('Sala de Reuniões', 'Sala de reuniões do andar 1'),
    ('Biblioteca Principal', 'Setor de atendimento e acervo'),
    ('Depósito', 'Depósito de equipamentos sem uso'),
]

# (numero_serie, numero_patrimonio, nome, marca, tipo, modelo,
#  status, ip, localizacao, descricao, centro_custo)
ELETRONICOS = [
    # ── INFR ──────────────────────────────────────────────────────────────
    ('SN-DELL-001', 'UFC-0001', 'Desktop Suporte 01', 'Dell', 'Computador',
     'OptiPlex 7090', 'Interno', '10.0.1.1', 'Sala de TI',
     'Computador principal da equipe de suporte', 'INFR'),

    ('SN-DELL-002', 'UFC-0002', 'Desktop Suporte 02', 'Dell', 'Computador',
     'OptiPlex 7090', 'Interno', '10.0.1.2', 'Sala de TI',
     'Computador secundário da equipe de suporte', 'INFR'),

    ('SN-HP-001', 'UFC-0003', 'Desktop HP Infra', 'HP', 'Computador',
     'ProDesk 400 G7', 'Interno', '10.0.1.3', 'Sala de TI',
     'Estação de trabalho da equipe de redes', 'INFR'),

    ('SN-LEN-001', 'UFC-0004', 'Notebook Gestor Infra', 'Lenovo', 'Notbook',
     'ThinkPad E15 Gen 4', 'Externo', None, None,
     'Notebook em uso externo pelo gestor de infraestrutura', 'INFR'),

    ('SN-APP-001', 'UFC-0005', 'MacBook TI', 'Apple', 'Notbook',
     'MacBook Pro 14"', 'Interno', '10.0.1.5', 'Sala de TI',
     'Notebook do técnico de TI para desenvolvimento', 'INFR'),

    ('SN-SAM-001', 'UFC-0006', 'Monitor Dell Suporte 01', 'Samsung', 'Monitor',
     'LS27AG320NLXZD', 'Interno', None, 'Sala de TI',
     'Monitor do desktop SN-DELL-001', 'INFR'),

    ('SN-SAM-002', 'UFC-0007', 'Monitor Samsung Suporte 02', 'Samsung', 'Monitor',
     'LS27AG320NLXZD', 'Interno', None, 'Sala de TI',
     'Monitor do desktop SN-DELL-002', 'INFR'),

    ('SN-LG-001', 'UFC-0008', 'Monitor LG Infra', 'LG', 'Monitor',
     '24MK430H-B', 'Interno', None, 'Sala de TI',
     'Monitor adicional para multitarefa', 'INFR'),

    ('SN-HPP-001', 'UFC-0009', 'Impressora HP Infra', 'HP', 'Impressora',
     'LaserJet Pro M404dn', 'Em Manutenção', None, 'Almoxarifado',
     'Em manutenção — problema no fusor', 'INFR'),

    ('SN-EPS-001', 'UFC-0010', 'Impressora Epson Infra', 'Epson', 'Impressora',
     'EcoTank L3150', 'Interno', None, 'Sala de TI',
     'Impressora colorida da equipe de TI', 'INFR'),

    # ── LABI ──────────────────────────────────────────────────────────────
    ('SN-DELL-003', 'UFC-0011', 'Lab A - PC 01', 'Dell', 'Computador',
     'OptiPlex 5090', 'Interno', '10.0.2.1', 'Lab. Computação A',
     'Estação de trabalho do laboratório A', 'LABI'),

    ('SN-DELL-004', 'UFC-0012', 'Lab A - PC 02', 'Dell', 'Computador',
     'OptiPlex 5090', 'Interno', '10.0.2.2', 'Lab. Computação A',
     'Estação de trabalho do laboratório A', 'LABI'),

    ('SN-DELL-005', 'UFC-0013', 'Lab A - PC 03', 'Dell', 'Computador',
     'OptiPlex 5090', 'Interno', '10.0.2.3', 'Lab. Computação A',
     'Estação de trabalho do laboratório A', 'LABI'),

    ('SN-DELL-006', 'UFC-0014', 'Lab B - PC 01', 'Dell', 'Computador',
     'OptiPlex 5090', 'Em Manutenção', '10.0.2.4', 'Lab. Computação B',
     'Aguardando troca de memória RAM', 'LABI'),

    ('SN-HP-002', 'UFC-0015', 'Notebook Gestora Lab', 'HP', 'Notbook',
     'ProBook 450 G9', 'Interno', '10.0.2.10', 'Lab. Computação B',
     'Notebook da gestora do laboratório', 'LABI'),

    ('SN-LEN-002', 'UFC-0016', 'Notebook Lab B', 'Lenovo', 'Notbook',
     'IdeaPad 3 Gen 7', 'Externo', None, None,
     'Notebook cedido para atividade de campo', 'LABI'),

    ('SN-SAM-003', 'UFC-0017', 'Monitor Lab A - 01', 'Samsung', 'Monitor',
     'LS24R356FHLXZD', 'Interno', None, 'Lab. Computação A',
     'Monitor do PC 01 do Lab A', 'LABI'),

    ('SN-SAM-004', 'UFC-0018', 'Monitor Lab A - 02', 'Samsung', 'Monitor',
     'LS24R356FHLXZD', 'Interno', None, 'Lab. Computação A',
     'Monitor do PC 02 do Lab A', 'LABI'),

    ('SN-LG-002', 'UFC-0019', 'Monitor LG Lab B', 'LG', 'Monitor',
     '27UK850-W', 'Interno', None, 'Lab. Computação B',
     'Monitor 4K para design gráfico', 'LABI'),

    ('SN-CAN-001', 'UFC-0020', 'Impressora Canon Lab', 'Canon', 'Impressora',
     'PIXMA G3160', 'Interno', None, 'Secretaria',
     'Impressora colorida do laboratório', 'LABI'),

    ('SN-EPSW-001', 'UFC-0021', 'Scanner Epson Lab', 'Epson', 'Scanner',
     'WorkForce ES-400 II', 'Interno', None, 'Lab. Computação B',
     'Scanner para digitalização de documentos', 'LABI'),

    ('SN-HPS-001', 'UFC-0022', 'Scanner HP Lab', 'HP', 'Scanner',
     'ScanJet Pro 3600 f1', 'Em Manutenção', None, 'Almoxarifado',
     'Aguardando peça de reposição', 'LABI'),

    # ── ADMI ──────────────────────────────────────────────────────────────
    ('SN-DELL-007', 'UFC-0023', 'Desktop Direção', 'Dell', 'Computador',
     'Vostro 3910', 'Interno', '10.0.3.1', 'Sala da Direção',
     'Desktop do gestor administrativo', 'ADMI'),

    ('SN-HP-003', 'UFC-0024', 'Desktop Secretaria', 'HP', 'Computador',
     'EliteDesk 800 G9', 'Interno', '10.0.3.2', 'Secretaria',
     'Computador da secretaria geral', 'ADMI'),

    ('SN-LEN-003', 'UFC-0025', 'Desktop Reuniões', 'Lenovo', 'Computador',
     'ThinkCentre M70q Gen 3', 'Interno', '10.0.3.3', 'Sala de Reuniões',
     'Mini PC da sala de reuniões para apresentações', 'ADMI'),

    ('SN-HPP-002', 'UFC-0026', 'Impressora Secretaria', 'HP', 'Impressora',
     'LaserJet 408dn', 'Interno', None, 'Secretaria',
     'Impressora mono da secretaria', 'ADMI'),

    ('SN-BRO-001', 'UFC-0027', 'Impressora Direção', 'Brother', 'Impressora',
     'MFC-L2750DW', 'Interno', None, 'Sala da Direção',
     'Multifuncional da diretoria', 'ADMI'),

    ('SN-CANS-001', 'UFC-0028', 'Scanner Secretaria', 'Canon', 'Scanner',
     'CanoScan LiDE 400', 'Interno', None, 'Secretaria',
     'Scanner de documentos da secretaria', 'ADMI'),

    ('SN-FUJ-001', 'UFC-0029', 'Scanner Portátil', 'Fujitsu', 'Scanner',
     'ScanSnap iX1300', 'Externo', None, None,
     'Scanner portátil cedido para evento externo', 'ADMI'),

    ('SN-SAM-005', 'UFC-0030', 'Monitor Direção', 'Samsung', 'Monitor',
     'T24E390EI', 'Interno', None, 'Sala da Direção',
     'Monitor do desktop da diretoria', 'ADMI'),

    ('SN-DELL-008', 'UFC-0031', 'Monitor Secretaria', 'Dell', 'Monitor',
     'P2422H', 'Interno', None, 'Secretaria',
     'Monitor do desktop da secretaria', 'ADMI'),

    # ── BLIO ──────────────────────────────────────────────────────────────
    ('SN-DELL-009', 'UFC-0032', 'Desktop Biblioteca 01', 'Dell', 'Computador',
     'OptiPlex 3080', 'Interno', '10.0.4.1', 'Biblioteca Principal',
     'Computador de consulta do acervo', 'BLIO'),

    ('SN-HP-004', 'UFC-0033', 'Desktop Biblioteca 02', 'HP', 'Computador',
     'All-in-One 24-dd1022', 'Interno', '10.0.4.2', 'Biblioteca Principal',
     'All-in-One da gestora da biblioteca', 'BLIO'),

    ('SN-EPS-002', 'UFC-0034', 'Impressora Biblioteca', 'Epson', 'Impressora',
     'EcoTank L4260', 'Interno', None, 'Biblioteca Principal',
     'Impressora colorida da biblioteca', 'BLIO'),

    ('SN-CANS-002', 'UFC-0035', 'Scanner Biblioteca', 'Canon', 'Scanner',
     'imageFORMULA DR-C225 II', 'Interno', None, 'Biblioteca Principal',
     'Scanner de alta velocidade para digitalização do acervo', 'BLIO'),

    ('SN-LG-003', 'UFC-0036', 'Monitor Recepção Blio', 'LG', 'Monitor',
     '27MP400-B', 'Interno', None, 'Recepção',
     'Monitor de consulta na recepção da biblioteca', 'BLIO'),

    ('SN-LEN-004', 'UFC-0037', 'Notebook Gestora Blio', 'Lenovo', 'Notbook',
     'ThinkPad L15 Gen 3', 'Externo', None, None,
     'Notebook da gestora em uso externo', 'BLIO'),
]

# (email_user, numero_serie_eq)
ASSOCS_USER_ELETRONICO = [
    ('lucas.func@ufc.br', 'SN-DELL-001'),
    ('maria.func@ufc.br', 'SN-DELL-002'),
    ('pedro.sub@ufc.br', 'SN-HP-001'),
    ('roberto.gestor@ufc.br', 'SN-LEN-001'),
    ('carlos.ti@ufc.br', 'SN-APP-001'),
    ('lucas.func@ufc.br', 'SN-SAM-001'),
    ('maria.func@ufc.br', 'SN-SAM-002'),
    ('joao.func@ufc.br', 'SN-DELL-003'),
    ('patricia.func@ufc.br', 'SN-DELL-004'),
    ('ana.gestor@ufc.br', 'SN-HP-002'),
    ('joao.func@ufc.br', 'SN-SAM-003'),
    ('patricia.func@ufc.br', 'SN-SAM-004'),
    ('marcos.gestor@ufc.br', 'SN-DELL-007'),
    ('marcos.gestor@ufc.br', 'SN-SAM-005'),
    ('diego.func@ufc.br', 'SN-HP-003'),
    ('diego.func@ufc.br', 'SN-DELL-008'),
    ('lucas.func@ufc.br', 'SN-DELL-009'),
    ('fernanda.gestor@ufc.br', 'SN-HP-004'),
    ('fernanda.gestor@ufc.br', 'SN-LEN-004'),
]

# (email_user, centro_custo, ocupacao)
ASSOCS_USER_CONTRATO = [
    ('roberto.gestor@ufc.br', 'INFR', 'Gestor'),
    ('pedro.sub@ufc.br', 'INFR', 'Subgestor'),
    ('lucas.func@ufc.br', 'INFR', 'Funcionario'),
    ('maria.func@ufc.br', 'INFR', 'Funcionario'),

    ('ana.gestor@ufc.br', 'LABI', 'Gestor'),
    ('pedro.sub@ufc.br', 'LABI', 'Subgestor'),
    ('joao.func@ufc.br', 'LABI', 'Funcionario'),
    ('patricia.func@ufc.br', 'LABI', 'Funcionario'),

    ('marcos.gestor@ufc.br', 'ADMI', 'Gestor'),
    ('julia.sub@ufc.br', 'ADMI', 'Subgestor'),
    ('diego.func@ufc.br', 'ADMI', 'Funcionario'),

    ('fernanda.gestor@ufc.br', 'BLIO', 'Gestor'),
    ('julia.sub@ufc.br', 'BLIO', 'Subgestor'),
    ('lucas.func@ufc.br', 'BLIO', 'Funcionario'),
]

TIPOS_CATALOGO = ['Computador', 'Notbook', 'Monitor', 'Impressora', 'Scanner']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def upsert(session: AsyncSession, table, values: dict) -> None:
    stmt = pg_insert(table).values(**values).on_conflict_do_nothing()
    await session.execute(stmt)


async def get_user_id(session: AsyncSession, email: str) -> int:
    result = await session.execute(select(User.id).where(User.email == email))
    uid = result.scalar_one_or_none()
    if uid is None:
        raise RuntimeError(f'Usuário não encontrado: {email}')
    return uid


async def get_eletronico_id(session: AsyncSession, numero_serie: str) -> int:
    result = await session.execute(
        select(Eletronico.id).where(Eletronico.numero_serie == numero_serie)
    )
    eid = result.scalar_one_or_none()
    if eid is None:
        raise RuntimeError(f'Eletrônico não encontrado: {numero_serie}')
    return eid


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    engine = create_async_engine(settings.database_url_async(), echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        print('── Tipos de eletrônico ─────────────────────────────────────')
        for nome in TIPOS_CATALOGO:
            await upsert(
                session, TipoEletronico.__table__,
                {'nome': nome, 'ativo': True},
            )
        await session.flush()
        print(f'   {len(TIPOS_CATALOGO)} tipo(s) garantidos.')

        print('── Usuários ────────────────────────────────────────────────')
        for nome, email, senha, tipo in USUARIOS:
            await upsert(
                session, User.__table__,
                {
                    'nome': nome,
                    'email': email,
                    'senha': security.get_senha_hash(senha),
                    'tipo': tipo,
                },
            )
        await session.flush()
        print(f'   {len(USUARIOS)} usuário(s) garantidos.')

        print('── Contratos (CCs) ─────────────────────────────────────────')
        for cc, desc in CONTRATOS:
            await upsert(
                session, Contrato.__table__,
                {'centro_custo': cc, 'descricao': desc},
            )
        await session.flush()
        print(f'   {len(CONTRATOS)} contrato(s) garantidos.')

        print('── Localizações ────────────────────────────────────────────')
        for nome, desc in LOCALIZACOES:
            await upsert(
                session, Localizacao.__table__,
                {'nome': nome, 'descricao': desc},
            )
        await session.flush()
        print(f'   {len(LOCALIZACOES)} localização(ões) garantidas.')

        print('── Eletrônicos ─────────────────────────────────────────────')
        for row in ELETRONICOS:
            sn, pat, nome, marca, tipo, modelo, status, ip, loc, desc, cc = row
            await upsert(
                session, Eletronico.__table__,
                {
                    'numero_serie': sn,
                    'numero_patrimonio': pat,
                    'nome': nome,
                    'marca': marca,
                    'tipo': tipo,
                    'modelo': modelo,
                    'status': status,
                    'ip': ip,
                    'localizacao': loc,
                    'descricao': desc,
                    'centro_custo': cc,
                },
            )
        await session.flush()
        print(f'   {len(ELETRONICOS)} eletrônico(s) garantidos.')

        print('── Associações usuário ↔ CC ────────────────────────────────')
        for email, cc, ocupacao in ASSOCS_USER_CONTRATO:
            uid = await get_user_id(session, email)
            await upsert(
                session, AssociacaoUserContrato.__table__,
                {'user_id': uid, 'centro_custo': cc, 'ocupacao': ocupacao},
            )
        await session.flush()
        print(f'   {len(ASSOCS_USER_CONTRATO)} associação(ões) CC garantidas.')

        print('── Associações usuário ↔ eletrônico ────────────────────────')
        for email, sn in ASSOCS_USER_ELETRONICO:
            uid = await get_user_id(session, email)
            eid = await get_eletronico_id(session, sn)
            await upsert(
                session, AssociacaoUserEletronico.__table__,
                {'user_id': uid, 'eletronico_id': eid},
            )
        await session.flush()
        print(f'   {len(ASSOCS_USER_ELETRONICO)} associação(ões) equipamento garantidas.')

        await session.commit()

    await engine.dispose()
    print()
    print('✓ Seed concluído com sucesso!')
    print()
    print('Credenciais de acesso:')
    print('  admin@ufc.br          / admin123    (Admin)')
    print('  carlos.ti@ufc.br      / carlos123   (Tecnico_TI)')
    print('  roberto.gestor@ufc.br / roberto123  (Gestor — INFR)')
    print('  ana.gestor@ufc.br     / ana123      (Gestor — LABI)')
    print('  marcos.gestor@ufc.br  / marcos123   (Gestor — ADMI)')
    print('  fernanda.gestor@ufc.br/ fernanda123 (Gestor — BLIO)')
    print('  pedro.sub@ufc.br      / pedro123    (Subgestor — INFR, LABI)')
    print('  julia.sub@ufc.br      / julia123    (Subgestor — ADMI, BLIO)')
    print('  lucas.func@ufc.br     / lucas123    (Funcionário — INFR, BLIO)')
    print('  maria.func@ufc.br     / maria123    (Funcionário — INFR)')
    print('  joao.func@ufc.br      / joao123     (Funcionário — LABI)')
    print('  patricia.func@ufc.br  / patricia123 (Funcionário — LABI)')
    print('  diego.func@ufc.br     / diego123    (Funcionário — ADMI)')


if __name__ == '__main__':
    asyncio.run(main())
