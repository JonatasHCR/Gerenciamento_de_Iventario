import { apiFetch } from './client'
import type { Eletronico } from '@/types/api'

export type CessaoStatus = 'ativa' | 'parcial' | 'devolvida'

export interface EletronicoCessao extends Eletronico {
  devolvido_em: string | null
  devolvida_por_id: number | null
  devolucao_lote: number | null
}

export interface Devolucao {
  lote: number
  devolvida_em: string
  devolvida_por_id: number | null
  gestor_visto_em: string | null
  eletronicos: Eletronico[]
}

export interface RecebimentoPendenteItem {
  cessao_id: number
  lote: number
  devolvida_em: string
  devolvida_por_id: number | null
}

export interface RecebimentosPendentesGestor {
  count: number
  items: RecebimentoPendenteItem[]
}

export interface Periferico {
  nome: string
  quantidade: number
}

export interface Cessao {
  id: number
  responsavel: string
  centro_custo_destino: string
  cedido_em: string
  cedido_por_id: number | null
  devolvida_em: string | null
  devolvida_por_id: number | null
  status: CessaoStatus
  total_eletronicos: number
  total_devolvidos: number
  total_pendentes: number
  eletronicos: EletronicoCessao[]
  devolucoes: Devolucao[]
  perifericos: Periferico[]
}

export interface CessaoCreate {
  eletronico_ids: number[]
  responsavel: string
  centro_custo_destino: string
  cedido_em?: string | null
  perifericos?: Periferico[]
}

export interface CessaoDevolverPayload {
  eletronico_ids: number[]
  devolvida_em?: string | null
}

export async function getCessoes(): Promise<Cessao[]> {
  const res = await apiFetch<{ cessoes: Cessao[] }>('/cessoes/')
  return res.cessoes
}

export async function getCessao(id: number): Promise<Cessao> {
  return apiFetch<Cessao>(`/cessoes/${id}`)
}

export async function createCessao(data: CessaoCreate): Promise<Cessao> {
  return apiFetch<Cessao>('/cessoes/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function devolverCessao(
  id: number,
  payload: CessaoDevolverPayload,
): Promise<Cessao> {
  return apiFetch<Cessao>(`/cessoes/${id}/devolver`, {
    method: 'PUT',
    body: JSON.stringify({
      eletronico_ids: payload.eletronico_ids,
      devolvida_em: payload.devolvida_em ?? null,
    }),
  })
}

export async function deleteCessao(id: number): Promise<Cessao> {
  return apiFetch<Cessao>(`/cessoes/${id}`, { method: 'DELETE' })
}

export async function getRecebimentosPendentesGestor(): Promise<RecebimentosPendentesGestor> {
  return apiFetch<RecebimentosPendentesGestor>(
    '/cessoes/recebimentos/pendentes-gestor',
  )
}

export async function marcarRecebimentosVistos(): Promise<{ marcadas: number }> {
  return apiFetch<{ marcadas: number }>('/cessoes/recebimentos/visto', {
    method: 'PUT',
  })
}
