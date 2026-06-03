'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getCessao, type Cessao } from '@/lib/api/cessoes'
import { Button } from '@/components/ui/button'
import { Printer } from 'lucide-react'

const MESES_PT = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

function dataExtenso(iso: string): string {
  const d = new Date(iso)
  return `${d.getDate()} de ${MESES_PT[d.getMonth()]} de ${d.getFullYear()}`
}

export default function TermoPage() {
  const params = useParams<{ id: string }>()
  const [cessao, setCessao] = useState<Cessao | null>(null)

  useEffect(() => {
    const id = parseInt(params.id)
    if (Number.isNaN(id)) return
    getCessao(id).then(setCessao).catch(() => {})
  }, [params.id])

  if (!cessao) return null

  return (
    <div className="mx-auto max-w-[800px] bg-white p-8 text-black print:p-0">
      <div className="mb-6 flex justify-end print:hidden">
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

      <h1 className="mb-8 text-center text-lg font-bold underline">
        TERMO DE RESPONSABILIDADE
      </h1>

      <p className="mb-4">
        <strong>Responsável:</strong> {cessao.responsavel}
      </p>

      <p className="mb-4 text-justify">
        Declaro para os devidos fins, que retirei na data de{' '}
        <strong>{dataExtenso(cessao.cedido_em)}</strong> os equipamentos
        listados abaixo e que os mesmos serão utilizados sob minha direta
        responsabilidade e coordenação. Responsabilizo-me, portanto, pelo uso
        adequado e pela devolução do referido equipamento em perfeitas
        condições de uso.
      </p>

      <p className="mb-2">
        <strong>Centro de Custo destino:</strong> {cessao.centro_custo_destino}
      </p>

      <p className="mb-2">Equipamentos Retirados:</p>

      <table className="mb-8 w-full border-collapse border border-black text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="border border-black px-2 py-1 text-left">EQUIPAMENTO</th>
            <th className="border border-black px-2 py-1 text-left">Nº DE SÉRIE</th>
            <th className="border border-black px-2 py-1 text-left">PATRIMÔNIO</th>
          </tr>
        </thead>
        <tbody>
          {cessao.eletronicos.map((e) => (
            <tr key={e.id}>
              <td className="border border-black px-2 py-1">{e.nome}</td>
              <td className="border border-black px-2 py-1">{e.numero_serie}</td>
              <td className="border border-black px-2 py-1">{e.numero_patrimonio}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mb-16">Lauro de Freitas, {dataExtenso(cessao.cedido_em)}</p>

      <div className="space-y-12 text-center">
        <div>
          <div className="mx-auto w-72 border-t border-black" />
          <p className="mt-1 text-sm">{cessao.responsavel}</p>
        </div>

        <div>
          <div className="mx-auto w-72 border-t border-black" />
          <p className="mt-1 text-sm font-semibold">UFC ENGENHARIA SA</p>
        </div>
      </div>

      {cessao.devolvida_em && (
        <p className="mt-8 text-center text-sm text-gray-600 print:hidden">
          Devolvida em {dataExtenso(cessao.devolvida_em)}
        </p>
      )}
    </div>
  )
}
