import { apiFetch } from './client'

export interface AuditLogEntry {
  id: number
  action: string
  user_id: number | null
  target_type: string
  target_id: number | null
  payload: Record<string, unknown> | null
  criado_em: string
}

export interface AuditLogList {
  items: AuditLogEntry[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AuditLogQuery {
  action?: string
  target_type?: string
  user_id?: number
  page?: number
  page_size?: number
}

export async function getAuditLog(
  q: AuditLogQuery = {},
): Promise<AuditLogList> {
  const params = new URLSearchParams()
  if (q.action) params.append('action', q.action)
  if (q.target_type) params.append('target_type', q.target_type)
  if (q.user_id != null) params.append('user_id', String(q.user_id))
  if (q.page) params.append('page', String(q.page))
  if (q.page_size) params.append('page_size', String(q.page_size))
  const qs = params.toString()
  return apiFetch<AuditLogList>(`/audit-log/${qs ? `?${qs}` : ''}`)
}
