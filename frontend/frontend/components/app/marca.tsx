import { cn } from '@/lib/utils'

export function Marca({ recolhida = false }: { recolhida?: boolean }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-xs font-bold tracking-tight text-primary-foreground">
        IC
      </span>
      {!recolhida && (
        <span className="min-w-0 leading-tight">
          <span className="block truncate text-sm font-semibold tracking-tight">InvControl</span>
          <span className="block truncate text-[11px] text-muted-foreground">Inventário de TI · UFC</span>
        </span>
      )}
    </span>
  )
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean)
  if (!partes.length) return '?'
  const [primeira] = partes
  const ultima = partes.length > 1 ? partes[partes.length - 1] : ''
  return (primeira[0] + (ultima[0] ?? '')).toUpperCase()
}

export function Iniciais({ nome, className }: { nome: string; className?: string }) {
  return (
    <span
      className={cn(
        'grid size-8 shrink-0 place-items-center rounded-full bg-muted text-xs font-semibold text-muted-foreground',
        className,
      )}
      aria-hidden
    >
      {iniciais(nome)}
    </span>
  )
}
