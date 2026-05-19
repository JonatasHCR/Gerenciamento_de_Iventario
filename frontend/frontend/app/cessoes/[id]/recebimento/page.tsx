'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getCessao } from '@/lib/api/cessoes'

export default function RecebimentoIndexPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()

  useEffect(() => {
    const id = parseInt(params.id)
    if (Number.isNaN(id)) return
    getCessao(id)
      .then((c) => {
        if (c.devolucoes.length === 0) return
        const ultimoLote = Math.max(
          ...c.devolucoes.map((d) => d.lote),
        )
        router.replace(`/cessoes/${id}/recebimento/${ultimoLote}`)
      })
      .catch(() => {})
  }, [params.id, router])

  return (
    <div className="mx-auto max-w-[800px] p-8 text-center">
      <p className="text-muted-foreground">Carregando recebimento…</p>
    </div>
  )
}
