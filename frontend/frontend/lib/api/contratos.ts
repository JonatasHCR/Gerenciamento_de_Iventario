import { apiFetch } from './client'
import type { Contrato } from '@/types/api'

export interface ContratoPayload {
  centro_custo: string
  descricao: string
}

export async function getContratos(): Promise<Contrato[]> {
  const res = await apiFetch<{ contratos: Contrato[] }>('/contratos/')
  return res.contratos
}

export async function createContrato(data: ContratoPayload): Promise<Contrato> {
  return apiFetch<Contrato>('/contratos/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateContrato(
  cc: string,
  data: ContratoPayload,
): Promise<Contrato> {
  return apiFetch<Contrato>(`/contratos/${cc}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteContrato(cc: string): Promise<Contrato> {
  return apiFetch<Contrato>(`/contratos/${cc}`, { method: 'DELETE' })
}
