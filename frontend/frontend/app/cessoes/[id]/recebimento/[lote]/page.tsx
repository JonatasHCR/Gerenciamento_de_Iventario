'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getCessao, type Cessao, type Devolucao } from '@/lib/api/cessoes'
import { getUsers } from '@/lib/api/users'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import type { User, AssociacaoUserContrato } from '@/types/api'
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

export default function RecebimentoLotePage() {
  const params = useParams<{ id: string; lote: string }>()
  const [cessao, setCessao] = useState<Cessao | null>(null)
  const [devolucao, setDevolucao] = useState<Devolucao | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [assocsCC, setAssocsCC] = useState<AssociacaoUserContrato[]>([])

  useEffect(() => {
    const id = parseInt(params.id)
    const lote = parseInt(params.lote)
    if (Number.isNaN(id) || Number.isNaN(lote)) return
    getCessao(id)
      .then((c) => {
        setCessao(c)
        setDevolucao(c.devolucoes.find((d) => d.lote === lote) ?? null)
      })
      .catch(() => {})
    getUsers().then(setUsers).catch(() => {})
    getAssociacoesContrato().then(setAssocsCC).catch(() => {})
  }, [params.id, params.lote])

  if (!cessao) return null

  if (!devolucao) {
    return (
      <div className="mx-auto max-w-[800px] p-8 text-center">
        <p className="text-muted-foreground">
          Recebimento #{params.lote} não encontrado para esta cessão.
        </p>
      </div>
    )
  }

  const dataDevolucao = dataExtenso(devolucao.devolvida_em)
  const totalLotes = cessao.devolucoes.length
  const parcial = cessao.status === 'parcial' ||
    devolucao.eletronicos.length < cessao.total_eletronicos

  const recebedor = users.find((u) => u.id === devolucao.devolvida_por_id)
  const ccsOrigem = Array.from(
    new Set(cessao.eletronicos.map((e) => e.centro_custo)),
  )
  const ccOrigem = ccsOrigem[0]
  const gestorAssoc = assocsCC.find(
    (a) => a.centro_custo === ccOrigem && a.ocupacao === 'Gestor',
  )
  const gestor = gestorAssoc
    ? users.find((u) => u.id === gestorAssoc.user_id)
    : undefined

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

      <h1 className="mb-2 text-center text-lg font-bold underline">
        TERMO DE RECEBIMENTO{parcial ? ' PARCIAL' : ''}
      </h1>
      {totalLotes > 1 && (
        <p className="mb-6 text-center text-sm text-gray-600">
          Recebimento #{devolucao.lote} de {totalLotes}
        </p>
      )}
      {totalLotes <= 1 && <div className="mb-6" />}

      <p className="mb-2">
        <strong>Responsável que devolve:</strong> {cessao.responsavel}
      </p>
      <p className="mb-4">
        <strong>Recebido por:</strong>{' '}
        {recebedor ? recebedor.nome : '—'}
        {ccOrigem && (
          <span className="text-gray-700"> (CC {ccOrigem})</span>
        )}
      </p>

      <p className="mb-4 text-justify">
        Declaro para os devidos fins, que devolvi na data de{' '}
        <strong>{dataDevolucao}</strong>{' '}
        {parcial ? 'parcialmente ' : ''}
        os equipamentos listados abaixo, anteriormente retirados em{' '}
        <strong>{dataExtenso(cessao.cedido_em)}</strong>, em perfeitas
        condições de uso. A UFC Engenharia Ltda., através do membro{' '}
        <strong>{recebedor?.nome ?? '—'}</strong> do CC{' '}
        <strong>{ccOrigem ?? '—'}</strong>, atesta o recebimento dos
        referidos equipamentos
        {parcial
          ? '. Os demais equipamentos da cessão permanecem sob responsabilidade do declarante.'
          : ' e dá quitação da cessão.'}
      </p>

      <p className="mb-2">
        <strong>Centro de Custo de origem:</strong> {ccOrigem ?? '—'}
      </p>
      <p className="mb-2">
        <strong>Centro de Custo destino da cessão:</strong>{' '}
        {cessao.centro_custo_destino}
      </p>

      <p className="mb-2">
        Equipamentos Devolvidos ({devolucao.eletronicos.length} de{' '}
        {cessao.total_eletronicos} da cessão):
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
          {devolucao.eletronicos.map((e) => (
            <tr key={e.id}>
              <td className="border border-black px-2 py-1">{e.nome}</td>
              <td className="border border-black px-2 py-1">{e.numero_serie}</td>
              <td className="border border-black px-2 py-1">{e.numero_patrimonio}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {parcial && cessao.total_pendentes > 0 && (
        <p className="mb-6 text-sm italic text-gray-700">
          Pendentes de devolução nesta cessão: {cessao.total_pendentes}{' '}
          equipamento(s).
        </p>
      )}

      <p className="mb-16">Lauro de Freitas, {dataDevolucao}</p>

      <div className="grid grid-cols-1 gap-12 text-center sm:grid-cols-3">
        <div>
          <div className="mx-auto w-full border-t border-black" />
          <p className="mt-1 text-sm">{cessao.responsavel}</p>
          <p className="text-xs text-gray-600">Devolve</p>
        </div>

        <div>
          <div className="mx-auto w-full border-t border-black" />
          <p className="mt-1 text-sm">{recebedor?.nome ?? '—'}</p>
          <p className="text-xs text-gray-600">
            Recebe (CC {ccOrigem ?? '—'})
          </p>
        </div>

        <div>
          <div className="mx-auto w-full border-t border-black" />
          <p className="mt-1 text-sm">{gestor?.nome ?? '—'}</p>
          <p className="text-xs text-gray-600">
            Gestor do CC {ccOrigem ?? '—'} (Visto)
          </p>
        </div>
      </div>

      <p className="mt-10 text-center text-xs text-gray-500 print:hidden">
        Cessão #{cessao.id} · Cedida em {dataExtenso(cessao.cedido_em)} ·
        Recebimento #{devolucao.lote} em {dataDevolucao}
      </p>
    </div>
  )
}
