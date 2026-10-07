'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Database, Download, Loader, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/auth-context';
import { SearchableSelect } from '@/components/app/searchable-select';
import { getContratos } from '@/lib/api/contratos';
import type { Contrato } from '@/types/api';

/**
 * Administração: backup, restauração e limpeza.
 *
 * Existe para essas operações deixarem de exigir linha de comando no servidor.
 *
 * A tela só aparece para quem tem o papel local de admin — mas isso é
 * conveniência de navegação. Quem barra de verdade é o `get_current_admin` em
 * cada rota de `/manutencao`: uma página escondida não é uma página protegida.
 */

interface Backup {
  nome: string;
  bytes: number;
  criado_em: string;
}

interface Alvo {
  chave: string;
  rotulo: string;
  aceita_cc: boolean;
}

/** O botão grava "inventario-…"; o sidecar agendado, "backup_…". */
function origem(nome: string): 'manual' | 'automático' {
  return nome.startsWith('inventario-') ? 'manual' : 'automático';
}

function tamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function api<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(`/api/manutencao${caminho}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(corpo.detail ?? 'Operação não concluída.');
  return corpo as T;
}

export default function AdministracaoPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [carregando, setCarregando] = useState(true);

  const [backups, setBackups] = useState<Backup[]>([]);
  const [alvos, setAlvos] = useState<Alvo[]>([]);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null);

  const [alvo, setAlvo] = useState('');
  const [centroCusto, setCentroCusto] = useState('');
  const [confirmaLimpeza, setConfirmaLimpeza] = useState('');

  const [arquivo, setArquivo] = useState('');
  const [confirmaRestauracao, setConfirmaRestauracao] = useState('');
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [contagem, setContagem] = useState<{ texto: string; detalhes: Record<string, number> } | null>(null);

  const recarregar = useCallback(async () => {
    const [lista, opcoes] = await Promise.all([
      api<Backup[]>('/backups'),
      api<Alvo[]>('/alvos'),
    ]);
    setBackups(lista);
    setAlvos(opcoes);
    if (!alvo && opcoes.length) setAlvo(opcoes[0].chave);
  }, [alvo]);

  useEffect(() => {
    if (isLoading) return;
    if (user?.tipo !== 'Admin') {
      router.replace('/');
      return;
    }
    getContratos().then(setContratos).catch(() => {});
    recarregar()
      .catch((e) => setAviso({ tipo: 'erro', texto: e.message }))
      .finally(() => setCarregando(false));
    // recarregar muda a cada render por causa de `alvo`; queremos só no mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, user, router]);

  async function executar(nome: string, acao: () => Promise<string>) {
    setOcupado(nome);
    setAviso(null);
    try {
      setAviso({ tipo: 'ok', texto: await acao() });
      await recarregar();
    } catch (e) {
      setAviso({ tipo: 'erro', texto: e instanceof Error ? e.message : 'Falhou.' });
    } finally {
      setOcupado(null);
    }
  }

  if (isLoading || carregando || user?.tipo !== 'Admin') {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const alvoAtual = alvos.find((a) => a.chave === alvo);

  return (
    <div className="mx-auto max-w-6xl space-y-6 py-2">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Backup e manutenção</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Backup, limpeza e restauração do banco. Só administradores.
        </p>
      </header>

      {aviso && (
        <p
          className={`rounded-lg border px-4 py-3 text-sm ${
            aviso.tipo === 'ok'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100'
              : 'border-destructive/30 bg-destructive/10 text-destructive'
          }`}
        >
          {aviso.texto}
        </p>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[1.2fr_1fr]">
      {/* ── Backup ─────────────────────────────────────────────────────── */}
      <section className="rounded-xl border bg-card p-5 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 font-medium">
              <Database className="h-4 w-4" /> Backup
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Gera um dump agora. Cai na mesma pasta dos backups automáticos.
            </p>
          </div>
          <Button
            onClick={() =>
              executar('backup', async () => {
                const b = await api<Backup>('/backups', { method: 'POST' });
                return `Backup gerado: ${b.nome} (${tamanho(b.bytes)}).`;
              })
            }
            disabled={ocupado !== null}
          >
            {ocupado === 'backup' ? 'Gerando…' : 'Fazer backup'}
          </Button>
        </div>

        <ul className="mt-4 divide-y text-sm">
          {backups.length === 0 && (
            <li className="py-3 text-muted-foreground">Nenhum backup ainda.</li>
          )}
          {backups.map((b) => (
            <li key={b.nome} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="truncate font-mono text-[13px]">{b.nome}</p>
                <p className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span
                    className={`rounded-full px-2 py-0.5 font-medium ${
                      origem(b.nome) === 'manual' ? 'bg-info-bg text-info' : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {origem(b.nome)}
                  </span>
                  {new Date(b.criado_em).toLocaleString('pt-BR')} · {tamanho(b.bytes)}
                </p>
              </div>
              <a
                href={`/api/manutencao/backups/${encodeURIComponent(b.nome)}`}
                className="inline-flex shrink-0 items-center gap-1.5 text-sm underline-offset-4 hover:underline"
              >
                <Download className="h-3.5 w-3.5" /> Baixar
              </a>
            </li>
          ))}
        </ul>
      </section>

      <div className="space-y-5">
      {/* ── Limpeza ────────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-destructive/30 bg-card p-5 shadow-xs">
        <h2 className="flex items-center gap-2 font-medium text-destructive">
          <Trash2 className="h-4 w-4" /> Limpeza de dados
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Apaga dados de negócio. <strong>Irreversível</strong> — faça um backup
          antes. Usuários e centros de custo não são apagados.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block sm:col-span-2">
            <span className="text-sm font-medium">O que apagar</span>
            <select
              value={alvo}
              onChange={(e) => {
                setAlvo(e.target.value);
                setContagem(null);
              }}
              className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            >
              {alvos.map((a) => (
                <option key={a.chave} value={a.chave}>
                  {a.rotulo}
                </option>
              ))}
            </select>
          </label>

          {alvoAtual?.aceita_cc && (
            <label className="block">
              <span className="text-sm font-medium">Centro de custo (opcional)</span>
              <div className="mt-1">
                <SearchableSelect
                  value={centroCusto}
                  onChange={(v) => {
                    setCentroCusto(v);
                    setContagem(null);
                  }}
                  options={[
                    { value: '', label: 'Todos os centros de custo' },
                    ...contratos.map((c) => ({
                      value: c.centro_custo,
                      label: `${c.centro_custo} · ${c.descricao}`,
                    })),
                  ]}
                  placeholder="Todos os centros de custo"
                />
              </div>
            </label>
          )}

          <label className="block">
            <span className="text-sm font-medium">
              Digite <code className="font-mono">LIMPAR</code> para confirmar
            </span>
            <Input
              value={confirmaLimpeza}
              onChange={(e) => setConfirmaLimpeza(e.target.value)}
              placeholder="LIMPAR"
              className="mt-1"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={ocupado !== null || !alvo}
            onClick={async () => {
              try {
                const r = await api<{ mensagem: string; detalhes: Record<string, number> }>('/contagem', {
                  method: 'POST',
                  body: JSON.stringify({ alvo, centro_custo: alvoAtual?.aceita_cc ? centroCusto || null : null }),
                });
                setContagem({ texto: r.mensagem, detalhes: r.detalhes ?? {} });
              } catch (e) {
                setAviso({ tipo: 'erro', texto: e instanceof Error ? e.message : 'Falhou.' });
              }
            }}
          >
            Contar antes
          </Button>
          {contagem && (
            <span className="text-sm">
              <strong className="text-destructive">{contagem.texto}</strong>
              <span className="ml-1 text-xs text-muted-foreground">
                {Object.entries(contagem.detalhes)
                  .filter(([, n]) => n > 0)
                  .map(([t, n]) => `${t.replace(/^tb_/, '').replace(/_/g, ' ')}: ${n}`)
                  .join(' · ')}
              </span>
            </span>
          )}
        </div>
        <Button
          variant="destructive"
          className="mt-4"
          disabled={ocupado !== null || confirmaLimpeza !== 'LIMPAR'}
          onClick={() =>
            executar('limpeza', async () => {
              const r = await api<{ mensagem: string }>('/limpeza', {
                method: 'POST',
                body: JSON.stringify({
                  alvo,
                  centro_custo: centroCusto || null,
                  confirmacao: confirmaLimpeza,
                }),
              });
              setConfirmaLimpeza('');
              return r.mensagem;
            })
          }
        >
          {ocupado === 'limpeza' ? 'Apagando…' : 'Limpar'}
        </Button>
      </section>

      {/* ── Restauração ────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-destructive/30 bg-card p-5 shadow-xs">
        <h2 className="flex items-center gap-2 font-medium text-destructive">
          <AlertTriangle className="h-4 w-4" /> Restauração
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Substitui <strong>todos</strong> os dados atuais pelos do arquivo. O que
          foi lançado depois do backup se perde.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium">Backup</span>
            <select
              value={arquivo}
              onChange={(e) => setArquivo(e.target.value)}
              className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"
            >
              <option value="">Escolha…</option>
              {backups.map((b) => (
                <option key={b.nome} value={b.nome}>
                  {b.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-medium">
              Digite <code className="font-mono">RESTAURAR</code> para confirmar
            </span>
            <Input
              value={confirmaRestauracao}
              onChange={(e) => setConfirmaRestauracao(e.target.value)}
              placeholder="RESTAURAR"
              className="mt-1"
            />
          </label>
        </div>

        <Button
          variant="destructive"
          className="mt-4"
          disabled={
            ocupado !== null || !arquivo || confirmaRestauracao !== 'RESTAURAR'
          }
          onClick={() =>
            executar('restauracao', async () => {
              const r = await api<{ mensagem: string }>('/restauracao', {
                method: 'POST',
                body: JSON.stringify({
                  nome: arquivo,
                  confirmacao: confirmaRestauracao,
                }),
              });
              setConfirmaRestauracao('');
              return r.mensagem;
            })
          }
        >
          {ocupado === 'restauracao' ? 'Restaurando…' : 'Restaurar'}
        </Button>
      </section>
      </div>
      </div>
    </div>
  );
}
