import { apiFetch } from './client'

export interface Localizacao {
  id: number
  nome: string
  descricao: string | null
  criado_em: string
}

export interface LocalizacaoPayload {
  nome: string
  descricao?: string | null
}

export interface LocalizacaoUpdatePayload {
  nome?: string
  descricao?: string | null
}

export async function getLocalizacoes(): Promise<Localizacao[]> {
  const res = await apiFetch<{ localizacoes: Localizacao[] }>(
    '/localizacoes/',
  )
  return res.localizacoes
}

export async function createLocalizacao(
  data: LocalizacaoPayload,
): Promise<Localizacao> {
  return apiFetch<Localizacao>('/localizacoes/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLocalizacao(
  id: number,
  data: LocalizacaoUpdatePayload,
): Promise<Localizacao> {
  return apiFetch<Localizacao>(`/localizacoes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteLocalizacao(id: number): Promise<Localizacao> {
  return apiFetch<Localizacao>(`/localizacoes/${id}`, {
    method: 'DELETE',
  })
}
