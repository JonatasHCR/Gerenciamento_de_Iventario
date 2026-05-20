'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronsUpDown, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'

interface Option {
  value: string
  label: string
  /**
   * Texto usado pra filtragem quando diferente do label. Útil quando
   * o label é só o nome (visualização limpa) mas a busca deve casar
   * com nome + email + outros campos.
   */
  searchKey?: string
}

interface Props {
  value: string
  onChange: (v: string) => void
  options: Option[]
  placeholder?: string
  className?: string
}

export function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = 'Selecione',
  className,
}: Props) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = options.find((o) => o.value === value)
  const term = search.toLowerCase()
  const filtered = options.filter((o) =>
    (o.searchKey ?? o.label).toLowerCase().includes(term),
  )

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm hover:bg-accent"
      >
        <span className={cn(!selected && 'text-muted-foreground')}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronsUpDown className="h-4 w-4 opacity-50" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          <div className="flex items-center border-b px-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar..."
              className="h-8 border-0 shadow-none focus-visible:ring-0"
            />
          </div>
          <div className="max-h-60 overflow-auto p-1">
            {filtered.length === 0 ? (
              <div className="py-2 text-center text-sm text-muted-foreground">
                Nenhum resultado
              </div>
            ) : (
              filtered.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => {
                    onChange(o.value)
                    setOpen(false)
                    setSearch('')
                  }}
                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                >
                  <Check
                    className={cn(
                      'h-4 w-4',
                      value === o.value ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                  {o.label}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
