import { apiFetch } from './client'

export interface TipoEletronico {
  id: number
  nome: string
  descricao: string | null
  ativo: boolean
  criado_em: string
}

export interface TipoEletronicoPayload {
  nome: string
  descricao?: string | null
}

export interface TipoEletronicoUpdatePayload {
  nome?: string
  descricao?: string | null
  ativo?: boolean
}

export async function getTipos(apenas_ativos = false): Promise<TipoEletronico[]> {
  const qs = apenas_ativos ? '?apenas_ativos=true' : ''
  const res = await apiFetch<{ tipos: TipoEletronico[] }>(
    `/tipos-eletronico/${qs}`,
  )
  return res.tipos
}

export async function createTipo(
  data: TipoEletronicoPayload,
): Promise<TipoEletronico> {
  return apiFetch<TipoEletronico>('/tipos-eletronico/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTipo(
  id: number,
  data: TipoEletronicoUpdatePayload,
): Promise<TipoEletronico> {
  return apiFetch<TipoEletronico>(`/tipos-eletronico/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteTipo(id: number): Promise<TipoEletronico> {
  return apiFetch<TipoEletronico>(`/tipos-eletronico/${id}`, {
    method: 'DELETE',
  })
}
