'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getCessoes,
  devolverCessao,
  deleteCessao,
  marcarRecebimentosVistos,
  type Cessao,
} from '@/lib/api/cessoes'
import { getUsers } from '@/lib/api/users'
import type { User } from '@/types/api'
import { formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FileText, FileCheck, Undo2, Plus, Trash2, Search, Building2 } from 'lucide-react'
import { StatusCessao } from '@/components/app/status'
import { cn } from '@/lib/utils'

type Aba = 'abertas' | 'recebimentos' | 'devolvidas'

const temRecebimentoNovo = (c: Cessao) => c.devolucoes.some((d) => d.gestor_visto_em === null)

function CessoesConteudo() {
  const { user } = useAuth()
  const router = useRouter()
  const busca = useSearchParams()
  const destacada = Number(busca.get('id')) || null
  // Sem escolha da pessoa, a aba segue a cessão do link (ou o ?aba=).
  const [abaEscolhida, setAba] = useState<Aba | null>(() =>
    busca.get('aba') === 'recebimentos' ? 'recebimentos' : null,
  )
  const [texto, setTexto] = useState('')
  const [cessoes, setCessoes] = useState<Cessao[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [devolverCessaoState, setDevolverCessaoState] =
    useState<Cessao | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [dataDevolucao, setDataDevolucao] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const isAdmin = user?.tipo === 'Admin'
  const canManage =
    isAdmin ||
    user?.tipo === 'Tecnico_TI' ||
    user?.tipo === 'Gestor'
  const canRequest = canManage || user?.tipo === 'Subgestor'

  const load = () => {
    getCessoes()
      .then(setCessoes)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    getUsers().then(setUsers).catch(() => {})
    // Marca recebimentos como vistos pelo gestor (no-op se não for gestor de nenhum CC)
    marcarRecebimentosVistos().catch(() => {})
  }, [])

  const userNome = (id: number | null | undefined): string => {
    if (id == null) return '—'
    const u = users.find((x) => x.id === id)
    return u?.nome ?? `#${id}`
  }

  function canDelete(c: Cessao): boolean {
    if (isAdmin) return true
    if (user?.tipo !== 'Gestor') return false
    // Mostra o botão; backend revalida ocupação per-CC do gestor.
    return c.eletronicos.length > 0
  }

  function canDevolver(c: Cessao): boolean {
    // Backend libera para qualquer associado dos CCs origem. UI mostra
    // o botão para todos os autenticados; backend revalida.
    return c.status !== 'devolvida' && user != null
  }

  async function handleDelete(c: Cessao) {
    if (!confirm(`Excluir cessão #${c.id}? Itens em aberto voltam a Interno.`)) return
    try {
      await deleteCessao(c.id)
      toast.success('Cessão excluída.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao excluir.')
    }
  }

  function abrirDevolver(c: Cessao) {
    setDevolverCessaoState(c)
    const pendentes = c.eletronicos.filter((e) => e.devolvido_em === null)
    setSelectedIds(new Set(pendentes.map((e) => e.id)))
    setDataDevolucao('')
  }

  function toggleItem(id: number) {
    setSelectedIds((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  const pendentesDialog = useMemo(
    () =>
      devolverCessaoState
        ? devolverCessaoState.eletronicos.filter(
            (e) => e.devolvido_em === null,
          )
        : [],
    [devolverCessaoState],
  )

  function toggleAllDialog() {
    if (selectedIds.size === pendentesDialog.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(pendentesDialog.map((e) => e.id)))
    }
  }

  async function confirmarDevolucao(e: React.FormEvent) {
    e.preventDefault()
    if (!devolverCessaoState) return
    if (selectedIds.size === 0) {
      toast.error('Selecione ao menos um equipamento.')
      return
    }
    if (dataDevolucao) {
      const retirada = devolverCessaoState.cedido_em.slice(0, 10)
      if (dataDevolucao < retirada) {
        toast.error(
          `A data de devolução não pode ser anterior à data de retirada (${formatDate(devolverCessaoState.cedido_em)}).`,
        )
        return
      }
    }
    setSubmitting(true)
    try {
      const iso = dataDevolucao
        ? new Date(dataDevolucao + 'T12:00:00').toISOString()
        : null
      const result = await devolverCessao(devolverCessaoState.id, {
        eletronico_ids: Array.from(selectedIds),
        devolvida_em: iso,
      })
      const proxLote = result.devolucoes.length
        ? Math.max(...result.devolucoes.map((d) => d.lote))
        : 1
      const parcial = result.status === 'parcial'
      toast.success(
        parcial
          ? `Devolução parcial registrada (${result.total_pendentes} pendente(s)). Abrindo recebimento…`
          : 'Cessão totalmente devolvida! Abrindo recebimento…',
      )
      setDevolverCessaoState(null)
      router.push(
        `/cessoes/${devolverCessaoState.id}/recebimento/${proxLote}`,
      )
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao devolver.')
    } finally {
      setSubmitting(false)
    }
  }

  const ativas = cessoes.filter((c) => c.status !== 'devolvida')
  const devolvidas = cessoes.filter((c) => c.status === 'devolvida')
  const comRecebimentoNovo = cessoes.filter(temRecebimentoNovo)
  const semAcento = (t: string) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const q = semAcento(texto.trim())
  const doLink = cessoes.find((x) => x.id === destacada)
  const aba: Aba = abaEscolhida ?? (doLink?.status === 'devolvida' ? 'devolvidas' : 'abertas')
  const daAba = aba === 'abertas' ? ativas : aba === 'devolvidas' ? devolvidas : comRecebimentoNovo
  const visiveis = q
    ? daAba.filter((c) =>
        semAcento(
          `#${c.id} ${c.responsavel} ${c.centro_custo_destino} ${c.eletronicos.map((e) => `${e.nome} ${e.numero_patrimonio}`).join(' ')}`,
        ).includes(q),
      )
    : daAba

  // Aberta por link (?id=): leva até o cartão, na aba em que ele está.
  useEffect(() => {
    if (!destacada || loading) return
    document.getElementById(`cessao-${destacada}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [destacada, loading, cessoes, aba])


  const renderStatusBadge = (c: Cessao) => (
    <StatusCessao
      status={c.status}
      detalhe={c.status === 'parcial' ? `${c.total_devolvidos}/${c.total_eletronicos}` : undefined}
    />
  )

  const renderItem = (c: Cessao) => {
    const podeDevolver =
      canDevolver(c) && (c.status === 'ativa' || c.status === 'parcial')
    const podeExcluir = canDelete(c)
    return (
      <div
        key={c.id}
        id={`cessao-${c.id}`}
        className={cn(
          'space-y-3 rounded-xl border bg-card p-4 shadow-xs',
          destacada === c.id && 'border-primary ring-2 ring-primary/30',
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-semibold">
              #{c.id} · {c.responsavel}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {renderStatusBadge(c)}
              <span className="inline-flex items-center gap-1">
                <Building2 className="h-3.5 w-3.5" /> CC {c.centro_custo_destino}
              </span>
              <span>cedida em {formatDate(c.cedido_em).slice(0, 10)}</span>
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-1">
            <Link href={`/cessoes/${c.id}/termo`}>
              <Button size="sm" variant="outline">
                <FileText className="mr-1 h-4 w-4" />
                Termo
              </Button>
            </Link>
            {podeDevolver && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => abrirDevolver(c)}
              >
                <Undo2 className="mr-1 h-4 w-4" />
                Devolver
              </Button>
            )}
            {podeExcluir && (
              <Button
                size="sm"
                variant="outline"
                className="text-destructive hover:text-destructive"
                onClick={() => handleDelete(c)}
              >
                <Trash2 className="mr-1 h-4 w-4" />
                Excluir
              </Button>
            )}
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {c.total_devolvidos} de {c.total_eletronicos} devolvido(s)
              {c.perifericos.length > 0 &&
                ` · + ${c.perifericos.map((p) => `${p.quantidade} ${p.nome.toLowerCase()}`).join(', ')}`}
            </span>
            {c.devolvida_em && <span>devolvida em {formatDate(c.devolvida_em).slice(0, 10)}</span>}
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-ok"
              style={{ width: `${(c.total_devolvidos / Math.max(1, c.total_eletronicos)) * 100}%` }}
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {c.eletronicos.map((e) => (
              <Link
                key={e.id}
                href={`/equipamentos?id=${e.id}`}
                title={`${e.numero_patrimonio} · ${e.numero_serie}`}
                className={cn(
                  'rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground',
                  e.devolvido_em && 'line-through opacity-60',
                )}
              >
                {e.nome}
              </Link>
            ))}
          </div>
        </div>

        {c.devolucoes.length > 0 && (
          <div className="border-t pt-2">
            <p className="text-xs font-medium text-muted-foreground mb-1">
              Recebimentos:
            </p>
            <div className="space-y-1">
              {c.devolucoes.map((d) => (
                <div
                  key={d.lote}
                  className="flex flex-wrap items-center gap-2 text-xs"
                >
                  <Link href={`/cessoes/${c.id}/recebimento/${d.lote}`}>
                    <Button size="sm" variant="ghost" className="h-7 text-xs">
                      <FileCheck className="mr-1 h-3 w-3" />
                      Recebimento #{d.lote} · {formatDate(d.devolvida_em)} ·{' '}
                      {d.eletronicos.length} item(ns)
                    </Button>
                  </Link>
                  <span className="text-muted-foreground">
                    Recebido por <strong>{userNome(d.devolvida_por_id)}</strong>
                  </span>
                  {d.gestor_visto_em === null && (
                    <Badge variant="destructive" className="h-5 text-[10px]">
                      Novo
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cessões</h1>
          <p className="text-sm text-muted-foreground">
            Equipamentos emprestados para fora do patrimônio e as devoluções.
          </p>
        </div>
        {canRequest && (
          <Link href="/equipamentos/ceder">
            <Button size="sm">
              <Plus className="mr-1 h-4 w-4" />
              {canManage ? 'Nova cessão' : 'Solicitar cessão'}
            </Button>
          </Link>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg bg-muted p-0.5 text-sm" role="tablist">
          {(
            [
              ['abertas', 'Em aberto', ativas.length],
              ['recebimentos', 'Recebimentos novos', comRecebimentoNovo.length],
              ['devolvidas', 'Devolvidas', devolvidas.length],
            ] as const
          ).map(([k, rotulo, n]) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={aba === k}
              onClick={() => setAba(k)}
              className="rounded-md px-3 py-1 font-medium text-muted-foreground aria-selected:bg-card aria-selected:text-foreground aria-selected:shadow-xs"
            >
              {rotulo} <span className="ml-1 text-xs tabular-nums opacity-70">{n}</span>
            </button>
          ))}
        </div>
        <div className="relative min-w-56 flex-1 sm:max-w-xs">
          <Search className="absolute top-2.5 left-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Responsável, CC, número ou equipamento"
          />
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : visiveis.length === 0 ? (
        <div className="rounded-xl border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
          {texto
            ? `Nenhuma cessão com “${texto}”.`
            : aba === 'recebimentos'
              ? 'Nenhum recebimento esperando conferência.'
              : aba === 'abertas'
                ? 'Nenhuma cessão em aberto.'
                : 'Nenhuma cessão devolvida ainda.'}
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">{visiveis.map(renderItem)}</div>
      )}

      <Dialog
        open={devolverCessaoState !== null}
        onOpenChange={(o) => !o && setDevolverCessaoState(null)}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Devolver cessão #{devolverCessaoState?.id}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={confirmarDevolucao} className="space-y-3">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <Label>Equipamentos sendo devolvidos</Label>
                <button
                  type="button"
                  onClick={toggleAllDialog}
                  className="text-xs text-primary underline"
                >
                  {selectedIds.size === pendentesDialog.length
                    ? 'Limpar'
                    : 'Selecionar todos'}
                </button>
              </div>
              <div className="max-h-72 overflow-y-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr className="border-b">
                      <th className="w-10 px-3 py-2"></th>
                      <th className="px-3 py-2 text-left font-medium">Nome</th>
                      <th className="px-3 py-2 text-left font-medium">Série</th>
                      <th className="px-3 py-2 text-left font-medium">Patrimônio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendentesDialog.map((e) => (
                      <tr
                        key={e.id}
                        className="border-b last:border-0 cursor-pointer hover:bg-muted/30"
                        onClick={() => toggleItem(e.id)}
                      >
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(e.id)}
                            onChange={() => toggleItem(e.id)}
                            onClick={(ev) => ev.stopPropagation()}
                          />
                        </td>
                        <td className="px-3 py-2">{e.nome}</td>
                        <td className="px-3 py-2 font-mono text-xs">{e.numero_serie}</td>
                        <td className="px-3 py-2 font-mono text-xs">{e.numero_patrimonio}</td>
                      </tr>
                    ))}
                    {pendentesDialog.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                          Nenhum equipamento pendente.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {selectedIds.size} de {pendentesDialog.length} selecionado(s)
                {selectedIds.size > 0 &&
                  selectedIds.size < pendentesDialog.length &&
                  ' — devolução parcial'}
              </p>
            </div>

            <div className="space-y-1">
              <Label>Data da devolução</Label>
              <Input
                type="date"
                value={dataDevolucao}
                min={devolverCessaoState?.cedido_em.slice(0, 10)}
                onChange={(e) => setDataDevolucao(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Em branco usa hoje · mínimo: data de retirada (
                {devolverCessaoState
                  ? formatDate(devolverCessaoState.cedido_em)
                  : '—'}
                )
              </p>
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={submitting || selectedIds.size === 0}
            >
              {submitting ? 'Processando…' : 'Confirmar devolução'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function CessoesPage() {
  return (
    <Suspense fallback={null}>
      <CessoesConteudo />
    </Suspense>
  )
}
