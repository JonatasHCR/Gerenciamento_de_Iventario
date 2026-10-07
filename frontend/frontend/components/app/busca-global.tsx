'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, FileText, Monitor, Search } from 'lucide-react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { getEletronicosPaginated } from '@/lib/api/eletronicos'
import { getCessoes, type Cessao } from '@/lib/api/cessoes'
import type { Eletronico } from '@/types/api'
import { ROTULO_STATUS } from './status'
import { cn } from '@/lib/utils'

const PAGINAS = [
  ['/equipamentos', 'Ir para Equipamentos'],
  ['/cessoes', 'Ir para Cessões'],
  ['/solicitacoes', 'Ir para Solicitações'],
  ['/relatorios', 'Montar relatório'],
  ['/equipamentos/ceder', 'Ceder equipamentos'],
] as const

const semAcento = (t: string) =>
  t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

interface Resultado {
  grupo: string
  href: string
  titulo: string
  detalhe?: string
  icone: 'eq' | 'cessao' | 'pagina'
}

/** Busca de qualquer tela: equipamento, cessão ou página. Abre com Ctrl+K. */
export function BuscaGlobal() {
  const router = useRouter()
  const [aberta, setAberta] = useState(false)
  const [texto, setTexto] = useState('')
  const [equipamentos, setEquipamentos] = useState<Eletronico[]>([])
  const [cessoes, setCessoes] = useState<Cessao[]>([])
  const [ativo, setAtivo] = useState(0)

  const abrir = useCallback((sim: boolean) => {
    if (sim) {
      setTexto('')
      setAtivo(0)
      getCessoes().then(setCessoes).catch(() => {})
    }
    setAberta(sim)
  }, [])

  useEffect(() => {
    const atalho = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        abrir(true)
      }
    }
    window.addEventListener('keydown', atalho)
    return () => window.removeEventListener('keydown', atalho)
  }, [abrir])

  useEffect(() => {
    const q = texto.trim()
    if (!q) return
    const t = setTimeout(() => {
      getEletronicosPaginated({ q, page_size: 6 })
        .then((r) => setEquipamentos(r.eletronicos))
        .catch(() => {})
    }, 200)
    return () => clearTimeout(t)
  }, [texto])

  const resultados = useMemo<Resultado[]>(() => {
    const q = semAcento(texto.trim())
    const ces = q
      ? cessoes
          .filter((c) => semAcento(`#${c.id} ${c.id} ${c.responsavel} ${c.centro_custo_destino}`).includes(q))
          .slice(0, 4)
      : []
    return [
      ...(q ? equipamentos : []).map((e) => ({
        grupo: 'Equipamentos',
        href: `/equipamentos?id=${e.id}`,
        titulo: `${e.nome} · ${e.numero_patrimonio}`,
        detalhe: ROTULO_STATUS[e.status],
        icone: 'eq' as const,
      })),
      ...ces.map((c) => ({
        grupo: 'Cessões',
        href: `/cessoes?id=${c.id}`,
        titulo: `Cessão #${c.id} · ${c.responsavel}`,
        detalhe: `CC ${c.centro_custo_destino}`,
        icone: 'cessao' as const,
      })),
      ...PAGINAS.filter(([, t]) => !q || semAcento(t).includes(q)).map(([href, titulo]) => ({
        grupo: 'Páginas',
        href,
        titulo,
        icone: 'pagina' as const,
      })),
    ]
  }, [texto, equipamentos, cessoes])

  const ir = (r: Resultado | undefined) => {
    if (!r) return
    setAberta(false)
    router.push(r.href)
  }

  const Icone = ({ tipo }: { tipo: Resultado['icone'] }) =>
    tipo === 'eq' ? (
      <Monitor className="h-4 w-4 text-muted-foreground" />
    ) : tipo === 'cessao' ? (
      <FileText className="h-4 w-4 text-muted-foreground" />
    ) : (
      <ArrowRight className="h-4 w-4 text-muted-foreground" />
    )

  return (
    <>
      <button
        type="button"
        onClick={() => abrir(true)}
        className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-md border bg-background px-3 text-sm text-muted-foreground transition-colors hover:border-ring md:max-w-md"
      >
        <Search className="h-4 w-4 shrink-0" />
        <span className="truncate text-left">Buscar patrimônio, série, pessoa ou cessão…</span>
        <kbd className="ml-auto hidden rounded border bg-card px-1.5 font-mono text-[11px] sm:inline">Ctrl K</kbd>
      </button>

      <Dialog open={aberta} onOpenChange={abrir}>
        <DialogContent className="top-[12vh] translate-y-0 gap-0 overflow-hidden p-0 sm:max-w-xl" showCloseButton={false}>
          <DialogTitle className="sr-only">Buscar</DialogTitle>
          <div className="flex items-center gap-2 border-b px-4">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              autoFocus
              value={texto}
              onChange={(e) => {
                setTexto(e.target.value)
                setAtivo(0)
              }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown') {
                  e.preventDefault()
                  setAtivo((a) => Math.min(a + 1, resultados.length - 1))
                }
                if (e.key === 'ArrowUp') {
                  e.preventDefault()
                  setAtivo((a) => Math.max(a - 1, 0))
                }
                if (e.key === 'Enter') ir(resultados[ativo])
              }}
              placeholder="Patrimônio, série, nome, pessoa, CC ou nº da cessão…"
              className="h-12 flex-1 bg-transparent text-[15px] outline-none"
            />
          </div>
          <ul className="max-h-96 overflow-y-auto p-1.5">
            {resultados.map((r, i) => (
              <li key={r.href + r.titulo}>
                {(i === 0 || resultados[i - 1].grupo !== r.grupo) && (
                  <p className="px-2.5 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {r.grupo}
                  </p>
                )}
                <button
                  type="button"
                  onMouseEnter={() => setAtivo(i)}
                  onClick={() => ir(r)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm',
                    i === ativo && 'bg-muted',
                  )}
                >
                  <Icone tipo={r.icone} />
                  <span className="min-w-0 flex-1 truncate">{r.titulo}</span>
                  {r.detalhe && <span className="text-xs text-muted-foreground">{r.detalhe}</span>}
                </button>
              </li>
            ))}
            {resultados.length === 0 && (
              <li className="px-3 py-8 text-center text-sm text-muted-foreground">
                Nada encontrado para “{texto}”.
              </li>
            )}
          </ul>
        </DialogContent>
      </Dialog>
    </>
  )
}
