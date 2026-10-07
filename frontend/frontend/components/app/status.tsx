import { cn } from '@/lib/utils'
import type { EletronicoStatus } from '@/types/api'
import type { CessaoStatus } from '@/lib/api/cessoes'

const BASE =
  'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full py-0.5 pr-2.5 pl-2 text-xs font-medium before:size-1.5 before:rounded-full before:bg-current'

const EQUIPAMENTO: Record<EletronicoStatus, [string, string]> = {
  Interno: ['Interno', 'bg-ok-bg text-ok'],
  Externo: ['Cedido', 'bg-warn-bg text-warn'],
  'Em Manutenção': ['Em manutenção', 'bg-crit-bg text-destructive'],
}

export const ROTULO_STATUS: Record<EletronicoStatus, string> = {
  Interno: 'Interno',
  Externo: 'Cedido',
  'Em Manutenção': 'Em manutenção',
}

export function StatusEquipamento({ status }: { status: EletronicoStatus }) {
  const [rotulo, cor] = EQUIPAMENTO[status] ?? [status, 'bg-muted text-muted-foreground']
  return <span className={cn(BASE, cor)}>{rotulo}</span>
}

const CESSAO: Record<CessaoStatus, [string, string]> = {
  ativa: ['Ativa', 'bg-info-bg text-info'],
  parcial: ['Parcial', 'bg-warn-bg text-warn'],
  devolvida: ['Devolvida', 'bg-muted text-muted-foreground'],
}

export function StatusCessao({ status, detalhe }: { status: CessaoStatus; detalhe?: string }) {
  const [rotulo, cor] = CESSAO[status]
  return (
    <span className={cn(BASE, cor)}>
      {rotulo}
      {detalhe && <span className="opacity-80">· {detalhe}</span>}
    </span>
  )
}
