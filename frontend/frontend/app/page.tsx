'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/context/auth-context'
import { getEletronicos } from '@/lib/api/eletronicos'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato, getAssociacoesEletronico } from '@/lib/api/associacoes'
import type { Eletronico, Contrato } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Monitor, Building2, ArrowRight, AlertTriangle, Home } from 'lucide-react'

const TIPOS = ['Computador', 'Notbook', 'Monitor', 'Impressora', 'Scanner']

export default function DashboardPage() {
  const { user } = useAuth()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [meusEletronicosIds, setMeusEletronicosIds] = useState<number[]>([])
  const [meusCCs, setMeusCCs] = useState<string[]>([])

  useEffect(() => {
    if (!user) return
    getEletronicos().then(setEletronicos).catch(() => {})
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesContrato()
      .then((list) =>
        setMeusCCs(list.filter((a) => a.user_id === user.id).map((a) => a.centro_custo)),
      )
      .catch(() => {})
    getAssociacoesEletronico()
      .then((list) =>
        setMeusEletronicosIds(list.filter((a) => a.user_id === user.id).map((a) => a.eletronico_id)),
      )
      .catch(() => {})
  }, [user])

  const isFuncionario = user?.tipo === 'Funcionario'
  const isSubGestor = user?.tipo === 'Subgestor' || user?.tipo === 'Gestor'

  const eletronicosFiltrados = isFuncionario
    ? eletronicos.filter((e) => meusEletronicosIds.includes(e.id))
    : isSubGestor
      ? eletronicos.filter((e) => meusCCs.includes(e.centro_custo))
      : eletronicos

  const interno = eletronicosFiltrados.filter((e) => e.status === 'Interno').length
  const cedido = eletronicosFiltrados.filter((e) => e.status === 'Externo').length
  const manutencao = eletronicosFiltrados.filter((e) => e.status === 'Em Manutenção').length
  const ccsExibidos = isFuncionario || isSubGestor ? meusCCs.length : contratos.length

  const porTipo = TIPOS.map((tipo) => ({
    tipo,
    count: eletronicosFiltrados.filter((e) => e.tipo === tipo).length,
  }))
  const maxCount = Math.max(...porTipo.map((p) => p.count), 1)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Equipamentos</CardTitle>
            <Monitor className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{eletronicosFiltrados.length}</div>
            <p className="text-xs text-muted-foreground">total visível</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Centros de Custo</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{ccsExibidos}</div>
            <p className="text-xs text-muted-foreground">associados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Internos</CardTitle>
            <Home className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{interno}</div>
            <p className="text-xs text-muted-foreground">no patrimônio</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Cedidos</CardTitle>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cedido}</div>
            <p className="text-xs text-muted-foreground">externos</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Em Manutenção</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{manutencao}</div>
            <p className="text-xs text-muted-foreground">equipamentos</p>
          </CardContent>
        </Card>
      </div>

      <div className="rounded-md border">
        <div className="border-b px-4 py-3 text-sm font-medium">Equipamentos por tipo</div>
        <div className="space-y-2 p-4">
          {eletronicosFiltrados.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum equipamento encontrado.</p>
          ) : (
            porTipo.map(({ tipo, count }) => (
              <div key={tipo}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{tipo}</span>
                  <span>{count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(count / maxCount) * 100}%` }}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
