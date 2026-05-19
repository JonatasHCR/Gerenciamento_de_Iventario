'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getSolicitacoes } from '@/lib/api/solicitacoes'
import type { Solicitacao } from '@/types/api'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Printer } from 'lucide-react'

const MESES_PT = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

function dataExtenso(iso: string): string {
  const d = new Date(iso)
  return `${d.getDate()} de ${MESES_PT[d.getMonth()]} de ${d.getFullYear()}`
}

export default function SolicitacaoTermoPage() {
  const params = useParams<{ id: string }>()
  const [sol, setSol] = useState<Solicitacao | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const id = parseInt(params.id)
    if (Number.isNaN(id)) return
    getSolicitacoes()
      .then((list) => {
        setSol(list.find((s) => s.id === id) ?? null)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [params.id])

  if (loading) {
    return (
      <div className="mx-auto max-w-[800px] p-8 text-center">
        <p className="text-muted-foreground">Carregando…</p>
      </div>
    )
  }

  if (!sol || sol.tipo !== 'cessao') {
    return (
      <div className="mx-auto max-w-[800px] p-8 text-center space-y-3">
        <p className="text-muted-foreground">
          Solicitação não encontrada ou não é de cessão.
        </p>
        <Link href="/solicitacoes">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar
          </Button>
        </Link>
      </div>
    )
  }

  const dataPrevista = dataExtenso(sol.criado_em)
  const eletronicos = sol.eletronicos ?? []

  return (
    <div className="mx-auto max-w-[800px] bg-white p-8 text-black print:p-0">
      <div className="mb-6 flex justify-between print:hidden">
        <Link href="/solicitacoes">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar
          </Button>
        </Link>
        <Button onClick={() => window.print()}>
          <Printer className="mr-2 h-4 w-4" />
          Imprimir / Salvar como PDF
        </Button>
      </div>

      <div className="mb-6 flex justify-end">
        <div className="text-right">
          <div className="text-2xl font-bold tracking-tight">UFC</div>
          <div className="text-xs tracking-widest text-gray-600">ENGENHARIA</div>
        </div>
      </div>

      <h1 className="mb-2 text-center text-lg font-bold underline">
        TERMO DE RESPONSABILIDADE
      </h1>
      <p className="mb-6 text-center text-xs uppercase tracking-widest text-gray-500">
        Proposta — Solicitação #{sol.id} · {sol.status}
      </p>

      <p className="mb-4">
        <strong>Responsável:</strong> {sol.responsavel}
      </p>

      <p className="mb-4 text-justify">
        Declaro para os devidos fins, que retirarei os equipamentos
        listados abaixo, que serão utilizados sob minha direta
        responsabilidade e coordenação. Responsabilizo-me, portanto, pelo
        uso adequado e pela devolução do referido equipamento em perfeitas
        condições de uso.
      </p>

      <p className="mb-2">
        <strong>Centro de Custo origem:</strong> {sol.centro_custo}
      </p>
      <p className="mb-2">
        <strong>Centro de Custo destino:</strong> {sol.centro_custo_destino}
      </p>

      <p className="mb-2">
        Equipamentos a ceder ({eletronicos.length}):
      </p>

      <table className="mb-8 w-full border-collapse border border-black text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="border border-black px-2 py-1 text-left">EQUIPAMENTO</th>
            <th className="border border-black px-2 py-1 text-left">Nº DE SÉRIE</th>
            <th className="border border-black px-2 py-1 text-left">PATRIMÔNIO</th>
          </tr>
        </thead>
        <tbody>
          {eletronicos.map((e) => (
            <tr key={e.id}>
              <td className="border border-black px-2 py-1">{e.nome}</td>
              <td className="border border-black px-2 py-1">{e.numero_serie}</td>
              <td className="border border-black px-2 py-1">{e.numero_patrimonio}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mb-16">Lauro de Freitas, {dataPrevista}</p>

      <div className="space-y-12 text-center">
        <div>
          <div className="mx-auto w-72 border-t border-black" />
          <p className="mt-1 text-sm">{sol.responsavel}</p>
        </div>

        <div>
          <div className="mx-auto w-72 border-t border-black" />
          <p className="mt-1 text-sm font-semibold">UFC ENGENHARIA LTDA.</p>
        </div>
      </div>

      <p className="mt-10 text-center text-xs text-gray-500 print:hidden">
        Este termo só terá validade após a aprovação da solicitação pelo
        Gestor do CC de origem.
      </p>
    </div>
  )
}
