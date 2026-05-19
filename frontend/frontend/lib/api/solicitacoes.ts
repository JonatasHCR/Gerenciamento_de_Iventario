import { apiFetch } from './client'
import type { Solicitacao, Ocupacao } from '@/types/api'

export async function getSolicitacoes(): Promise<Solicitacao[]> {
  const res = await apiFetch<{ solicitacoes: Solicitacao[] }>('/solicitacoes/')
  return res.solicitacoes
}

export async function createEntradaCC(data: {
  centro_custo: string
  ocupacao_solicitada: Ocupacao
}): Promise<Solicitacao> {
  return apiFetch<Solicitacao>('/solicitacoes/entrada-cc', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createConviteCC(data: {
  solicitante_id: number
  centro_custo: string
  ocupacao_solicitada: Ocupacao
}): Promise<Solicitacao> {
  return apiFetch<Solicitacao>('/solicitacoes/convite-cc', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createCargoInicial(data: {
  cargo_solicitado: string
}): Promise<Solicitacao> {
  return apiFetch<Solicitacao>('/solicitacoes/cargo-inicial', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createSolicitacaoCessao(data: {
  eletronico_ids: number[]
  responsavel: string
  centro_custo_destino: string
}): Promise<Solicitacao> {
  return apiFetch<Solicitacao>('/solicitacoes/cessao', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function aprovarSolicitacao(id: number): Promise<Solicitacao> {
  return apiFetch<Solicitacao>(`/solicitacoes/${id}/aprovar`, {
    method: 'PUT',
  })
}

export async function rejeitarSolicitacao(id: number): Promise<Solicitacao> {
  return apiFetch<Solicitacao>(`/solicitacoes/${id}/rejeitar`, {
    method: 'PUT',
  })
}

export async function cancelarSolicitacao(id: number): Promise<Solicitacao> {
  return apiFetch<Solicitacao>(`/solicitacoes/${id}`, { method: 'DELETE' })
}
