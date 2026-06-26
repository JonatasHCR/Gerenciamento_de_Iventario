export type UserTipo = 'Admin' | 'Gestor' | 'Subgestor' | 'Funcionario' | 'Tecnico_TI'
export type Ocupacao = 'Gestor' | 'Subgestor' | 'Funcionario'
export type EletronicoStatus = 'Interno' | 'Externo' | 'Em Manutenção'
export type SolicitacaoTipo = 'entrada_cc' | 'cargo_inicial' | 'cessao'
export type SolicitacaoStatus = 'pendente' | 'aprovada' | 'rejeitada'

export interface User {
  id: number
  nome: string
  email: string
  tipo: UserTipo
}

export interface Contrato {
  centro_custo: string
  descricao: string
  gestor_nome?: string | null
  total_membros?: number
}

export interface Eletronico {
  id: number
  numero_serie: string
  numero_patrimonio: string
  nome: string
  marca?: string
  tipo: string
  modelo?: string
  status: EletronicoStatus
  ip?: string
  localizacao?: string
  descricao?: string
  centro_custo: string
}

export interface AssociacaoUserContrato {
  user_id: number
  centro_custo: string
  ocupacao: Ocupacao
}

export interface AssociacaoUserEletronico {
  user_id: number
  eletronico_id: number
}

export interface Solicitacao {
  id: number
  tipo: SolicitacaoTipo
  status: SolicitacaoStatus
  solicitante_id: number
  centro_custo?: string
  ocupacao_solicitada?: Ocupacao
  convidado_por_id?: number
  cargo_solicitado?: string
  centro_custo_destino?: string
  responsavel?: string
  eletronicos?: Eletronico[]
  perifericos?: { nome: string; quantidade: number }[]
  criado_em: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
