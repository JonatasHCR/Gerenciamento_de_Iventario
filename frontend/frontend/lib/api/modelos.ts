import { apiFetch } from './client'

export interface Modelo {
  id: number
  nome: string
  descricao: string | null
  marca_id: number
  marca_nome: string | null
  criado_em: string
}

export interface ModeloPayload {
  nome: string
  descricao?: string | null
  marca_id: number
}

export interface ModeloUpdatePayload {
  nome?: string
  descricao?: string | null
  marca_id?: number
}

export async function getModelos(marcaId?: number): Promise<Modelo[]> {
  const qs = marcaId != null ? `?marca_id=${marcaId}` : ''
  const res = await apiFetch<{ modelos: Modelo[] }>(`/modelos/${qs}`)
  return res.modelos
}

export async function createModelo(data: ModeloPayload): Promise<Modelo> {
  return apiFetch<Modelo>('/modelos/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateModelo(
  id: number,
  data: ModeloUpdatePayload,
): Promise<Modelo> {
  return apiFetch<Modelo>(`/modelos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteModelo(id: number): Promise<Modelo> {
  return apiFetch<Modelo>(`/modelos/${id}`, {
    method: 'DELETE',
  })
}
