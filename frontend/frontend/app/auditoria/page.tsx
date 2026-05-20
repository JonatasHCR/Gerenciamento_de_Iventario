'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/context/auth-context'
import { getAuditLog, type AuditLogEntry } from '@/lib/api/audit_log'
import { getUsers } from '@/lib/api/users'
import type { User } from '@/types/api'
import { formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChevronLeft, ChevronRight, RefreshCw, X } from 'lucide-react'

const ACTIONS = [
  { value: '', label: 'Todas' },
  // Cessões
  { value: 'cessao.create', label: 'Cessão criada' },
  { value: 'cessao.devolver', label: 'Cessão devolvida' },
  { value: 'cessao.delete', label: 'Cessão excluída' },
  // Solicitações
  { value: 'solicitacao.aprovar', label: 'Solicitação aprovada' },
  { value: 'solicitacao.rejeitar', label: 'Solicitação rejeitada' },
  { value: 'solicitacao.cancelar', label: 'Solicitação cancelada' },
  { value: 'solicitacao.delete', label: 'Solicitação excluída (Admin)' },
  // Usuários
  { value: 'user.delete', label: 'Usuário excluído' },
  { value: 'user.tipo_change', label: 'Tipo de usuário alterado' },
  // Centros de Custo
  { value: 'contrato.create', label: 'CC criado' },
  { value: 'contrato.update', label: 'CC editado' },
  { value: 'contrato.delete', label: 'CC excluído' },
  { value: 'cc.membro.add', label: 'Entrada de membro no CC' },
  {
    value: 'cc.membro.ocupacao_change',
    label: 'Ocupação de membro alterada',
  },
  { value: 'cc.membro.remove', label: 'Saída/remoção de membro' },
  { value: 'cc.membro.self_remove', label: 'Membro saiu do CC' },
] as const

const TARGETS = [
  { value: '', label: 'Todos' },
  { value: 'cessao', label: 'Cessão' },
  { value: 'solicitacao', label: 'Solicitação' },
  { value: 'user', label: 'Usuário' },
  { value: 'contrato', label: 'Centro de Custo' },
] as const

const PAGE_SIZE = 50

function actionLabel(a: string): string {
  return ACTIONS.find((x) => x.value === a)?.label ?? a
}

function actionVariant(
  a: string,
): 'default' | 'secondary' | 'destructive' {
  if (
    a.endsWith('.delete') ||
    a.endsWith('.cancelar') ||
    a.endsWith('.remove') ||
    a.endsWith('.self_remove')
  )
    return 'destructive'
  if (a.endsWith('.rejeitar') || a.endsWith('.ocupacao_change'))
    return 'secondary'
  return 'default'
}

export default function AuditoriaPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const isAdmin = user?.tipo === 'Admin'

  const [items, setItems] = useState<AuditLogEntry[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)

  const [filtroAction, setFiltroAction] = useState('')
  const [filtroTarget, setFiltroTarget] = useState('')
  const [filtroUserId, setFiltroUserId] = useState('')

  useEffect(() => {
    if (!isLoading && user && !isAdmin) {
      router.replace('/')
    }
  }, [user, isAdmin, isLoading, router])

  useEffect(() => {
    if (!isAdmin) return
    setLoading(true)
    getAuditLog({
      action: filtroAction || undefined,
      target_type: filtroTarget || undefined,
      user_id: filtroUserId ? parseInt(filtroUserId) : undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => {
        setItems(res.items)
        setTotal(res.total)
        setPages(res.pages)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isAdmin, filtroAction, filtroTarget, filtroUserId, page])

  useEffect(() => {
    if (!isAdmin) return
    getUsers().then(setUsers).catch(() => {})
  }, [isAdmin])

  useEffect(() => {
    setPage(1)
  }, [filtroAction, filtroTarget, filtroUserId])

  const userNome = useMemo(() => {
    const map = new Map(users.map((u) => [u.id, u.nome]))
    return (id: number | null | undefined) => {
      if (id == null) return '—'
      return map.get(id) ?? `#${id}`
    }
  }, [users])

  function refresh() {
    setPage(1)
    setFiltroAction('')
    setFiltroTarget('')
    setFiltroUserId('')
  }

  if (!isAdmin) return null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Auditoria</h1>
          <p className="text-sm text-muted-foreground">
            Histórico de ações críticas do sistema (append-only).
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh}>
          <RefreshCw className="mr-1 h-4 w-4" />
          Limpar filtros
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div className="space-y-1">
          <Label className="text-xs">Ação</Label>
          <Select
            value={filtroAction || '__all__'}
            onValueChange={(v) =>
              setFiltroAction(v === '__all__' ? '' : v)
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACTIONS.map((a) => (
                <SelectItem
                  key={a.value || 'all'}
                  value={a.value || '__all__'}
                >
                  {a.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Recurso</Label>
          <Select
            value={filtroTarget || '__all__'}
            onValueChange={(v) =>
              setFiltroTarget(v === '__all__' ? '' : v)
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TARGETS.map((t) => (
                <SelectItem
                  key={t.value || 'all'}
                  value={t.value || '__all__'}
                >
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">User ID (autor)</Label>
          <div className="flex gap-1">
            <Input
              type="number"
              value={filtroUserId}
              onChange={(e) => setFiltroUserId(e.target.value)}
              placeholder="ID do usuário"
            />
            {filtroUserId && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setFiltroUserId('')}
                className="shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[700px] text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-3 py-2 text-left font-medium">Quando</th>
              <th className="px-3 py-2 text-left font-medium">Ação</th>
              <th className="px-3 py-2 text-left font-medium">Recurso</th>
              <th className="px-3 py-2 text-left font-medium">Autor</th>
              <th className="px-3 py-2 text-left font-medium">Detalhes</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  Nenhuma entrada de auditoria com esses filtros.
                </td>
              </tr>
            ) : (
              items.map((e) => (
                <tr key={e.id} className="border-b last:border-0 align-top">
                  <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(e.criado_em)}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={actionVariant(e.action)}>
                      {actionLabel(e.action)}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-sm">
                    {e.target_type}
                    {e.target_id ? ` #${e.target_id}` : ''}
                  </td>
                  <td className="px-3 py-2 text-sm">
                    {userNome(e.user_id)}
                  </td>
                  <td className="px-3 py-2">
                    {e.payload ? (
                      <details className="cursor-pointer">
                        <summary className="text-xs text-muted-foreground">
                          ver
                        </summary>
                        <pre className="mt-1 max-w-md overflow-x-auto rounded bg-muted/30 p-2 text-[10px] leading-tight">
                          {JSON.stringify(e.payload, null, 2)}
                        </pre>
                      </details>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        —
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/30 px-4 py-2 text-sm">
          <span className="text-muted-foreground">
            Mostrando{' '}
            <strong>
              {(page - 1) * PAGE_SIZE + 1}–
              {Math.min(page * PAGE_SIZE, total)}
            </strong>{' '}
            de <strong>{total}</strong>
          </span>
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-xs text-muted-foreground">
              Página {page} de {pages}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= pages || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
