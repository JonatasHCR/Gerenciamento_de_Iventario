'use client'

import { useMemo, useState } from 'react'
import { Popover } from 'radix-ui'
import { Filter } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export interface OpcaoFiltro {
  value: string
  label: string
}

const semAcento = (t: string) =>
  t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

/**
 * Filtro de várias escolhas com busca, em botão compacto. A busca ignora
 * acentos e maiúsculas; o número no botão diz quantas opções estão marcadas.
 */
export function FiltroMulti({
  titulo,
  opcoes,
  valor,
  onChange,
}: {
  titulo: string
  opcoes: OpcaoFiltro[]
  valor: string[]
  onChange: (v: string[]) => void
}) {
  const [busca, setBusca] = useState('')
  const visiveis = useMemo(() => {
    const q = semAcento(busca.trim())
    return q ? opcoes.filter((o) => semAcento(o.label).includes(q)) : opcoes
  }, [busca, opcoes])

  const alternar = (v: string) =>
    onChange(valor.includes(v) ? valor.filter((x) => x !== v) : [...valor, v])

  return (
    <Popover.Root onOpenChange={(aberto) => !aberto && setBusca('')}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={cn(
            'inline-flex h-8 items-center gap-1.5 rounded-md border border-dashed px-2.5 text-sm text-muted-foreground transition-colors hover:border-ring hover:text-foreground',
            valor.length > 0 && 'border-solid border-primary bg-primary/5 text-primary',
          )}
        >
          <Filter className="h-3.5 w-3.5" />
          {titulo}
          {valor.length > 0 && (
            <span className="rounded-full bg-primary px-1.5 text-[11px] font-bold text-primary-foreground">
              {valor.length}
            </span>
          )}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={6}
          className="z-50 w-72 rounded-lg border bg-popover p-1.5 text-popover-foreground shadow-lg"
        >
          <input
            autoFocus
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder={`Buscar ${titulo.toLowerCase()}…`}
            className="mb-1 h-8 w-full rounded-md border bg-background px-2 text-sm outline-none focus:ring-2 focus:ring-ring/50"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && visiveis.length === 1) {
                e.preventDefault()
                alternar(visiveis[0].value)
              }
            }}
          />
          <ul className="max-h-64 overflow-y-auto">
            {visiveis.map((o) => (
              <li key={o.value}>
                <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted">
                  <input
                    type="checkbox"
                    className="accent-primary"
                    checked={valor.includes(o.value)}
                    onChange={() => alternar(o.value)}
                  />
                  <span className="truncate">{o.label}</span>
                </label>
              </li>
            ))}
            {visiveis.length === 0 && (
              <li className="px-2 py-3 text-center text-sm text-muted-foreground">Nada encontrado.</li>
            )}
          </ul>
          <div className="mt-1 flex justify-between border-t pt-1.5">
            <Button size="sm" variant="ghost" onClick={() => onChange([])} disabled={!valor.length}>
              Limpar
            </Button>
            <Popover.Close asChild>
              <Button size="sm">Pronto</Button>
            </Popover.Close>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
