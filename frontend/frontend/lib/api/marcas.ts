import { apiFetch } from './client'

export interface Marca {
  id: number
  nome: string
  criado_em: string
}

export interface MarcaPayload {
  nome: string
}

export interface MarcaUpdatePayload {
  nome?: string
}

export async function getMarcas(): Promise<Marca[]> {
  const res = await apiFetch<{ marcas: Marca[] }>('/marcas/')
  return res.marcas
}

export async function createMarca(data: MarcaPayload): Promise<Marca> {
  return apiFetch<Marca>('/marcas/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateMarca(
  id: number,
  data: MarcaUpdatePayload,
): Promise<Marca> {
  return apiFetch<Marca>(`/marcas/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteMarca(id: number): Promise<Marca> {
  return apiFetch<Marca>(`/marcas/${id}`, {
    method: 'DELETE',
  })
}
