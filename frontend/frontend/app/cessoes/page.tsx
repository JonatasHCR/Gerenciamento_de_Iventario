'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
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
import { FileText, FileCheck, Undo2, Plus, Trash2 } from 'lucide-react'

export default function CessoesPage() {
  const { user } = useAuth()
  const router = useRouter()
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

  const renderStatusBadge = (c: Cessao) => {
    if (c.status === 'devolvida') {
      return <Badge variant="secondary">Devolvida</Badge>
    }
    if (c.status === 'parcial') {
      return (
        <Badge className="bg-amber-500 hover:bg-amber-500 text-white">
          Parcial · {c.total_devolvidos}/{c.total_eletronicos}
        </Badge>
      )
    }
    return <Badge>Ativa</Badge>
  }

  const renderItem = (c: Cessao) => {
    const podeDevolver =
      canDevolver(c) && (c.status === 'ativa' || c.status === 'parcial')
    const podeExcluir = canDelete(c)
    return (
      <div key={c.id} className="rounded-md border bg-card p-4 space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              {renderStatusBadge(c)}
              <span className="text-sm font-medium">#{c.id}</span>
            </div>
            <p className="mt-1 text-sm">
              <strong>Responsável:</strong> {c.responsavel}
            </p>
            <p className="text-sm text-muted-foreground">
              CC destino: <strong>{c.centro_custo_destino}</strong>
              {' · '}
              {c.total_eletronicos} equipamento(s)
              {c.status === 'parcial' &&
                ` · ${c.total_pendentes} pendente(s)`}
            </p>
            <p className="text-xs text-muted-foreground">
              Cedida em {formatDate(c.cedido_em)}
              {c.devolvida_em && ` · Devolvida em ${formatDate(c.devolvida_em)}`}
            </p>
          </div>
          <div className="flex flex-wrap gap-1">
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Cessões</h1>
        {canRequest && (
          <Link href="/equipamentos/ceder">
            <Button size="sm">
              <Plus className="mr-1 h-4 w-4" />
              {canManage ? 'Nova cessão' : 'Solicitar cessão'}
            </Button>
          </Link>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Carregando…</p>
      ) : cessoes.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhuma cessão registrada.</p>
      ) : (
        <>
          <div>
            <h2 className="mb-3 font-semibold">Em aberto ({ativas.length})</h2>
            {ativas.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma cessão em aberto.</p>
            ) : (
              <div className="space-y-2">{ativas.map(renderItem)}</div>
            )}
          </div>

          {devolvidas.length > 0 && (
            <div>
              <h2 className="mb-3 font-semibold">Histórico</h2>
              <div className="space-y-2">{devolvidas.map(renderItem)}</div>
            </div>
          )}
        </>
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
