'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import { getEletronicos, cederEletronicos } from '@/lib/api/eletronicos'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import type { Eletronico, Contrato } from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SearchableSelect } from '@/components/app/searchable-select'
import { FileDown, AlertTriangle } from 'lucide-react'

export default function CessaoPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [meusCCsGestor, setMeusCCsGestor] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [filtroCC, setFiltroCC] = useState('todos')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [responsavel, setResponsavel] = useState('')
  const [ccDestino, setCcDestino] = useState('')
  const [loading, setLoading] = useState(false)

  const isAdmin = user?.tipo === 'Admin'
  const isTecnicoTi = user?.tipo === 'Tecnico_TI'
  const semAcesso =
    !isLoading && user && !isAdmin && !isTecnicoTi && meusCCsGestor.length === 0

  useEffect(() => {
    if (!user) return
    getEletronicos().then(setEletronicos).catch(() => {})
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesContrato()
      .then((list) =>
        setMeusCCsGestor(
          list
            .filter((a) => a.user_id === user.id && a.ocupacao === 'Gestor')
            .map((a) => a.centro_custo),
        ),
      )
      .catch(() => {})
  }, [user])

  const ccsPermitidos = useMemo(() => {
    if (isAdmin || isTecnicoTi) return contratos.map((c) => c.centro_custo)
    return meusCCsGestor
  }, [isAdmin, isTecnicoTi, contratos, meusCCsGestor])

  const cederItens = useMemo(() => {
    return eletronicos.filter((e) => {
      if (!ccsPermitidos.includes(e.centro_custo)) return false
      if (e.status !== 'Interno') return false
      const matchCC = filtroCC === 'todos' || e.centro_custo === filtroCC
      const term = search.toLowerCase()
      const matchSearch =
        !term ||
        e.nome.toLowerCase().includes(term) ||
        e.numero_serie.toLowerCase().includes(term) ||
        e.numero_patrimonio.toLowerCase().includes(term)
      return matchCC && matchSearch
    })
  }, [eletronicos, ccsPermitidos, filtroCC, search])

  function toggle(id: number) {
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  function toggleAll() {
    if (selected.size === cederItens.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(cederItens.map((e) => e.id)))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (selected.size === 0) {
      toast.error('Selecione pelo menos um equipamento.')
      return
    }
    setLoading(true)
    try {
      await cederEletronicos({
        eletronico_ids: Array.from(selected),
        responsavel,
        centro_custo_destino: ccDestino,
      })
      const ids = Array.from(selected).join(',')
      const params = new URLSearchParams({
        ids,
        responsavel,
        cc: ccDestino,
      })
      router.push(`/cessao/termo?${params.toString()}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao ceder.')
    } finally {
      setLoading(false)
    }
  }

  if (semAcesso) {
    return (
      <div className="flex items-start gap-3 rounded-md border bg-card p-6">
        <AlertTriangle className="mt-1 h-5 w-5 text-destructive" />
        <div>
          <p className="font-medium">Sem permissão</p>
          <p className="text-sm text-muted-foreground">
            Apenas Gestor, Admin ou Tecnico_TI pode ceder equipamentos.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Cessão de Equipamentos</h1>
        <p className="text-sm text-muted-foreground">
          Selecione os equipamentos a ceder, informe o responsável e o CC
          destino — o termo é gerado em seguida.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Input
          placeholder="Buscar nome, série, patrimônio…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={filtroCC} onValueChange={setFiltroCC}>
          <SelectTrigger>
            <SelectValue placeholder="Filtrar por CC" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os CCs disponíveis</SelectItem>
            {ccsPermitidos.map((cc) => (
              <SelectItem key={cc} value={cc}>{cc}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center justify-between rounded-md border bg-muted/30 px-3 text-sm">
          <span className="text-muted-foreground">Selecionados</span>
          <Badge variant="secondary">{selected.size}</Badge>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[700px] text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="w-10 px-3 py-2 text-left">
                <input
                  type="checkbox"
                  checked={
                    cederItens.length > 0 && selected.size === cederItens.length
                  }
                  onChange={toggleAll}
                />
              </th>
              <th className="px-3 py-2 text-left font-medium">Nome</th>
              <th className="px-3 py-2 text-left font-medium">Tipo</th>
              <th className="px-3 py-2 text-left font-medium">Nº Série</th>
              <th className="px-3 py-2 text-left font-medium">Patrimônio</th>
              <th className="px-3 py-2 text-left font-medium">CC</th>
            </tr>
          </thead>
          <tbody>
            {cederItens.map((e) => (
              <tr
                key={e.id}
                className="border-b last:border-0 cursor-pointer hover:bg-muted/30"
                onClick={() => toggle(e.id)}
              >
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.has(e.id)}
                    onChange={() => toggle(e.id)}
                    onClick={(ev) => ev.stopPropagation()}
                  />
                </td>
                <td className="px-3 py-2">{e.nome}</td>
                <td className="px-3 py-2">{e.tipo}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.numero_serie}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.numero_patrimonio}</td>
                <td className="px-3 py-2">{e.centro_custo}</td>
              </tr>
            ))}
            {cederItens.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  Nenhum equipamento elegível.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 rounded-md border p-4 sm:grid-cols-3">
        <div className="space-y-1">
          <Label>Responsável (recebe)</Label>
          <Input
            value={responsavel}
            onChange={(e) => setResponsavel(e.target.value)}
            placeholder="Nome completo"
            required
          />
        </div>
        <div className="space-y-1">
          <Label>CC destino</Label>
          <SearchableSelect
            value={ccDestino}
            onChange={setCcDestino}
            options={contratos.map((c) => ({
              value: c.centro_custo,
              label: `${c.centro_custo} — ${c.descricao}`,
            }))}
          />
        </div>
        <div className="flex items-end">
          <Button
            type="submit"
            className="w-full"
            disabled={
              loading || selected.size === 0 || !responsavel || !ccDestino
            }
          >
            <FileDown className="mr-2 h-4 w-4" />
            {loading ? 'Processando…' : 'Ceder e gerar termo'}
          </Button>
        </div>
      </form>
    </div>
  )
}
