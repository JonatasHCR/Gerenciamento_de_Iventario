'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Database, Download, Loader, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/auth-context';

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
    <div className="mx-auto max-w-3xl space-y-6 py-2">
      <header>
        <h1 className="text-xl font-semibold">Administração</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Backup, restauração e limpeza do banco. Restrito aos administradores.
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

      {/* ── Backup ─────────────────────────────────────────────────────── */}
      <section className="rounded-xl border p-5">
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
                <p className="truncate font-medium">{b.nome}</p>
                <p className="text-xs text-muted-foreground">
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

      {/* ── Limpeza ────────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-destructive/30 p-5">
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
              onChange={(e) => setAlvo(e.target.value)}
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
              <Input
                value={centroCusto}
                onChange={(e) => setCentroCusto(e.target.value)}
                placeholder="deixe vazio para todos"
                className="mt-1"
              />
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
      <section className="rounded-xl border border-destructive/30 p-5">
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
  );
}
