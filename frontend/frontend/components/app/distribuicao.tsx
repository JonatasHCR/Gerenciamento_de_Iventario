'use client'

import { useEffect, useMemo, useState } from 'react'
import { getEletronicos } from '@/lib/api/eletronicos'
import type { Eletronico, EletronicoStatus } from '@/types/api'
import { ROTULO_STATUS } from './status'

export type Contagem = Record<EletronicoStatus, number> & { total: number }

const VAZIA = (): Contagem => ({ Interno: 0, Externo: 0, 'Em Manutenção': 0, total: 0 })

/** Quantos equipamentos de cada situação há em cada CC ou localização. */
export function useResumoPor(chave: 'centro_custo' | 'localizacao') {
  const [equipamentos, setEquipamentos] = useState<Eletronico[]>([])
  useEffect(() => {
    getEletronicos().then(setEquipamentos).catch(() => {})
  }, [])
  return useMemo(() => {
    const mapa = new Map<string, Contagem>()
    for (const e of equipamentos) {
      const k = e[chave] || ''
      const c = mapa.get(k) ?? VAZIA()
      c[e.status] += 1
      c.total += 1
      mapa.set(k, c)
    }
    return (k: string) => mapa.get(k) ?? VAZIA()
  }, [equipamentos, chave])
}

const COR: Record<EletronicoStatus, string> = {
  Interno: 'bg-ok',
  Externo: 'bg-accent',
  'Em Manutenção': 'bg-primary',
}

/** Barra fina interno / cedido / em manutenção. */
export function BarraSituacao({ c }: { c: Contagem }) {
  if (!c.total) return <div className="h-1.5 rounded-full bg-muted" />
  return (
    <div
      className="flex h-1.5 overflow-hidden rounded-full bg-muted"
      title={(Object.keys(COR) as EletronicoStatus[]).map((s) => `${ROTULO_STATUS[s]}: ${c[s]}`).join(' · ')}
    >
      {(Object.keys(COR) as EletronicoStatus[]).map((s) => (
        <div key={s} className={COR[s]} style={{ width: `${(c[s] / c.total) * 100}%` }} />
      ))}
    </div>
  )
}
