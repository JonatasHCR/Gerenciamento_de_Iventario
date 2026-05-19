import { apiFetch } from './client'
import type { Eletronico } from '@/types/api'

export interface EletronicoPayload {
  numero_serie: string
  numero_patrimonio: string
  nome: string
  marca?: string
  tipo: string
  modelo?: string
  status: string
  ip?: string
  localizacao?: string
  descricao?: string
  centro_custo: string
}

export type CampoBuscaEletronico =
  | 'todos'
  | 'nome'
  | 'numero_serie'
  | 'numero_patrimonio'
  | 'marca'
  | 'modelo'
  | 'ip'
  | 'localizacao'
  | 'responsavel'
  | 'sem_responsavel'

export interface EletronicoQuery {
  q?: string
  campo?: CampoBuscaEletronico
  centro_custo?: string[]
  status?: string[]
  tipo?: string[]
  page?: number
  page_size?: number
}

export interface EletronicoPaginatedResponse {
  eletronicos: Eletronico[]
  total: number
  page: number
  page_size: number
  pages: number
}

function buildQueryString(query?: EletronicoQuery): string {
  if (!query) return ''
  const params = new URLSearchParams()
  if (query.q) params.append('q', query.q)
  if (query.campo && query.campo !== 'todos') {
    params.append('campo', query.campo)
  }
  query.centro_custo?.forEach((v) => params.append('centro_custo', v))
  query.status?.forEach((v) => params.append('status', v))
  query.tipo?.forEach((v) => params.append('tipo', v))
  if (query.page) params.append('page', String(query.page))
  if (query.page_size) params.append('page_size', String(query.page_size))
  const s = params.toString()
  return s ? `?${s}` : ''
}

export async function getEletronicosPaginated(
  query?: EletronicoQuery,
): Promise<EletronicoPaginatedResponse> {
  return apiFetch<EletronicoPaginatedResponse>(
    `/eletronicos/${buildQueryString(query)}`,
  )
}

export async function getEletronicos(): Promise<Eletronico[]> {
  // Compatibilidade: retorna todos (até 1000) sem paginação visível
  const res = await getEletronicosPaginated({ page_size: 1000 })
  return res.eletronicos
}

export async function createEletronico(
  data: EletronicoPayload,
): Promise<Eletronico> {
  return apiFetch<Eletronico>('/eletronicos/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEletronico(
  id: number,
  data: EletronicoPayload,
): Promise<Eletronico> {
  return apiFetch<Eletronico>(`/eletronicos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEletronico(id: number): Promise<Eletronico> {
  return apiFetch<Eletronico>(`/eletronicos/${id}`, { method: 'DELETE' })
}

export interface CessaoPayload {
  eletronico_ids: number[]
  responsavel: string
  centro_custo_destino: string
}

export interface CessaoResponse {
  eletronicos: Eletronico[]
  responsavel: string
  centro_custo_destino: string
}

export async function cederEletronicos(
  data: CessaoPayload,
): Promise<CessaoResponse> {
  return apiFetch<CessaoResponse>('/eletronicos/ceder', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
