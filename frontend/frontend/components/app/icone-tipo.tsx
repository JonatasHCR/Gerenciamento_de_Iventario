import { Box, Cpu, Laptop, Monitor, Printer, ScanLine } from 'lucide-react'
import { cn } from '@/lib/utils'

const semAcento = (t: string) =>
  t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

type Simbolo = 'cpu' | 'laptop' | 'monitor' | 'printer' | 'scan' | 'box'

// Pelo começo do nome: os tipos são cadastráveis, e "Notbook" existe na base.
const POR_TIPO: [string, Simbolo][] = [
  ['comput', 'cpu'],
  ['desktop', 'cpu'],
  ['note', 'laptop'],
  ['notb', 'laptop'],
  ['lapt', 'laptop'],
  ['monit', 'monitor'],
  ['impress', 'printer'],
  ['scan', 'scan'],
]

function simboloDe(tipo: string): Simbolo {
  const t = semAcento(tipo)
  return POR_TIPO.find(([inicio]) => t.startsWith(inicio))?.[1] ?? 'box'
}

/** Só o desenho do tipo, sem fundo. */
export function SimboloTipo({ tipo, className }: { tipo: string; className?: string }) {
  switch (simboloDe(tipo)) {
    case 'cpu':
      return <Cpu className={className} />
    case 'laptop':
      return <Laptop className={className} />
    case 'monitor':
      return <Monitor className={className} />
    case 'printer':
      return <Printer className={className} />
    case 'scan':
      return <ScanLine className={className} />
    default:
      return <Box className={className} />
  }
}

/** O quadradinho com o ícone do tipo, usado na lista, nos cartões e na ficha. */
export function IconeTipo({ tipo, className }: { tipo: string; className?: string }) {
  return (
    <span className={cn('grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground', className)}>
      <SimboloTipo tipo={tipo} className="h-4 w-4" />
    </span>
  )
}
