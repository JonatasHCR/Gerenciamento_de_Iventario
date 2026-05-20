import { apiFetch } from './client'
import type {
  AssociacaoUserContrato,
  AssociacaoUserEletronico,
  Ocupacao,
} from '@/types/api'

export async function getAssociacoesContrato(): Promise<
  AssociacaoUserContrato[]
> {
  const res = await apiFetch<{ associacoes: AssociacaoUserContrato[] }>(
    '/associacoes/contratos/',
  )
  return res.associacoes
}

export async function createAssociacaoContrato(data: {
  user_id: number
  centro_custo: string
  ocupacao: Ocupacao
}): Promise<AssociacaoUserContrato> {
  return apiFetch<AssociacaoUserContrato>('/associacoes/contratos/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAssociacaoContrato(
  user_id: number,
  centro_custo: string,
): Promise<AssociacaoUserContrato> {
  return apiFetch<AssociacaoUserContrato>(
    `/associacoes/contratos/${user_id}/${centro_custo}`,
    { method: 'DELETE' },
  )
}

export async function updateAssociacaoContrato(
  user_id: number,
  centro_custo: string,
  ocupacao: 'Gestor' | 'Subgestor' | 'Funcionario',
): Promise<AssociacaoUserContrato> {
  return apiFetch<AssociacaoUserContrato>(
    `/associacoes/contratos/${user_id}/${centro_custo}`,
    {
      method: 'PUT',
      body: JSON.stringify({ user_id, centro_custo, ocupacao }),
    },
  )
}

export async function getAssociacoesEletronico(): Promise<
  AssociacaoUserEletronico[]
> {
  const res = await apiFetch<{ associacoes: AssociacaoUserEletronico[] }>(
    '/associacoes/eletronicos/',
  )
  return res.associacoes
}

export async function createAssociacaoEletronico(data: {
  user_id: number
  eletronico_id: number
}): Promise<AssociacaoUserEletronico> {
  return apiFetch<AssociacaoUserEletronico>('/associacoes/eletronicos/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAssociacaoEletronico(
  user_id: number,
  eletronico_id: number,
): Promise<AssociacaoUserEletronico> {
  return apiFetch<AssociacaoUserEletronico>(
    `/associacoes/eletronicos/${user_id}/${eletronico_id}`,
    { method: 'DELETE' },
  )
}
