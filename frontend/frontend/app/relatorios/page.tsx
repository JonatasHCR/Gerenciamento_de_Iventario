'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getEletronicosPaginated,
  type EletronicoQuery,
} from '@/lib/api/eletronicos'
import { getContratos } from '@/lib/api/contratos'
import { getUsers } from '@/lib/api/users'
import {
  getAssociacoesContrato,
  getAssociacoesEletronico,
} from '@/lib/api/associacoes'
import { getTipos, type TipoEletronico } from '@/lib/api/tipos'
import type {
  Eletronico,
  Contrato,
  User,
  AssociacaoUserContrato,
  AssociacaoUserEletronico,
} from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  Printer,
  Filter,
  Columns3,
  ChevronDown,
  ChevronRight,
  Layers,
  Search,
} from 'lucide-react'

type ColKey = keyof Eletronico | 'responsavel'
type AgrupamentoKey =
  | 'centro_custo'
  | 'localizacao'
  | 'responsavel'
  | 'status'
  | 'tipo'
  | 'marca'

const COLUNAS: { key: ColKey; label: string }[] = [
  { key: 'nome', label: 'Nome' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'marca', label: 'Marca' },
  { key: 'modelo', label: 'Modelo' },
  { key: 'numero_serie', label: 'Nº Série' },
  { key: 'numero_patrimonio', label: 'Patrimônio' },
  { key: 'status', label: 'Status' },
  { key: 'centro_custo', label: 'Centro de Custo' },
  { key: 'responsavel', label: 'Responsável' },
  { key: 'ip', label: 'IP' },
  { key: 'localizacao', label: 'Localização' },
  { key: 'descricao', label: 'Descrição' },
]

const STATUSES = ['Interno', 'Externo', 'Em Manutenção']

const AGRUPAMENTOS: { key: AgrupamentoKey; label: string }[] = [
  { key: 'centro_custo', label: 'Centro de Custo' },
  { key: 'localizacao', label: 'Localização' },
  { key: 'responsavel', label: 'Responsável' },
  { key: 'status', label: 'Status' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'marca', label: 'Marca' },
]

const SEM_LOCALIZACAO = '(Sem localização)'

async function fetchAll(query: EletronicoQuery): Promise<Eletronico[]> {
  const ps = 500
  const first = await getEletronicosPaginated({ ...query, page: 1, page_size: ps })
  if (first.pages <= 1) return first.eletronicos
  const rest = await Promise.all(
    Array.from({ length: first.pages - 1 }, (_, i) =>
      getEletronicosPaginated({ ...query, page: i + 2, page_size: ps }),
    ),
  )
  return [first.eletronicos, ...rest.map((r) => r.eletronicos)].flat()
}

export default function RelatoriosPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [assocs, setAssocs] = useState<AssociacaoUserContrato[]>([])
  const [assocsEl, setAssocsEl] = useState<AssociacaoUserEletronico[]>([])
  const [authChecked, setAuthChecked] = useState(false)
  const [authorized, setAuthorized] = useState(false)
  const [tiposCatalogo, setTiposCatalogo] = useState<TipoEletronico[]>([])
  const [loadingData, setLoadingData] = useState(false)

  const tiposNomes = useMemo(
    () => tiposCatalogo.map((t) => t.nome),
    [tiposCatalogo],
  )

  // Filtros
  const [ccsSel, setCcsSel] = useState<Set<string>>(new Set())
  const [statusSel, setStatusSel] = useState<Set<string>>(new Set(STATUSES))
  const [tiposSel, setTiposSel] = useState<Set<string>>(new Set())
  const [localizacoesSel, setLocalizacoesSel] = useState<Set<string>>(new Set())
  const [locSearch, setLocSearch] = useState('')

  // Gestor multi-select
  const [gestorIds, setGestorIds] = useState<Set<number>>(new Set())
  const [gestorSearch, setGestorSearch] = useState('')

  // Agrupamento
  const [agrupamento, setAgrupamento] = useState<AgrupamentoKey>('centro_custo')

  const [colunasSel, setColunasSel] = useState<Set<ColKey>>(
    new Set(COLUNAS.map((c) => c.key).filter((k) => k !== 'centro_custo')),
  )
  const [titulo, setTitulo] = useState('Relatório de Equipamentos')

  const isAdminOuTI = user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'

  async function buscarComFiltros() {
    setLoadingData(true)
    try {
      const query: EletronicoQuery = {
        centro_custo: ccsSel.size > 0 ? Array.from(ccsSel) : undefined,
        status:
          statusSel.size > 0 && statusSel.size < STATUSES.length
            ? Array.from(statusSel)
            : undefined,
        tipo:
          tiposSel.size > 0 && tiposSel.size < tiposNomes.length
            ? Array.from(tiposSel)
            : undefined,
      }
      const items = await fetchAll(query)
      setEletronicos(items)
      setLocalizacoesSel(new Set())
    } catch {
      toast.error('Erro ao buscar equipamentos.')
    } finally {
      setLoadingData(false)
    }
  }

  useEffect(() => {
    if (!user) return
    const isAdminOuTIUser = user.tipo === 'Admin' || user.tipo === 'Tecnico_TI'

    if (isAdminOuTIUser) {
      setAuthorized(true)
      setAuthChecked(true)
      fetchAll({}).then(setEletronicos).catch(() => {})
      getContratos().then(setContratos).catch(() => {})
      getUsers().then(setUsers).catch(() => {})
      getAssociacoesContrato().then(setAssocs).catch(() => {})
      getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
      getTipos(true)
        .then((tipos) => {
          setTiposCatalogo(tipos)
          setTiposSel(new Set(tipos.map((t) => t.nome)))
        })
        .catch(() => {})
      return
    }

    getAssociacoesContrato()
      .then((all) => {
        setAssocs(all)
        const ehGestorOuSub = all.some(
          (a) =>
            a.user_id === user.id &&
            (a.ocupacao === 'Gestor' || a.ocupacao === 'Subgestor'),
        )
        if (!ehGestorOuSub) {
          toast.error(
            'Apenas Gestores/Subgestores de algum CC podem gerar relatórios.',
          )
          router.replace('/')
          return
        }
        setAuthorized(true)
        fetchAll({}).then(setEletronicos).catch(() => {})
        getContratos().then(setContratos).catch(() => {})
        getUsers().then(setUsers).catch(() => {})
        getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
        getTipos(true)
          .then((tipos) => {
            setTiposCatalogo(tipos)
            setTiposSel(new Set(tipos.map((t) => t.nome)))
          })
          .catch(() => {})
      })
      .catch(() => router.replace('/'))
      .finally(() => setAuthChecked(true))
  }, [user, router])

  // Quando muda seleção de gestores, auto-popula CCs com a união dos CCs deles
  useEffect(() => {
    if (gestorIds.size === 0) return
    const ccs = assocs
      .filter((a) => gestorIds.has(a.user_id) && a.ocupacao === 'Gestor')
      .map((a) => a.centro_custo)
    setCcsSel(new Set(ccs))
  }, [gestorIds, assocs])

  // Localizações únicas derivadas dos equipamentos (empty set = todos visíveis)
  const todasLocalizacoes = useMemo(() => {
    const set = new Set<string>()
    for (const e of eletronicos) {
      set.add(e.localizacao ? e.localizacao : SEM_LOCALIZACAO)
    }
    return Array.from(set).sort((a, b) => {
      if (a === SEM_LOCALIZACAO) return 1
      if (b === SEM_LOCALIZACAO) return -1
      return a.localeCompare(b)
    })
  }, [eletronicos])

  const responsavelPorEqId = useMemo(() => {
    const map = new Map<number, string>()
    for (const a of assocsEl) {
      if (map.has(a.eletronico_id)) continue
      const u = users.find((x) => x.id === a.user_id)
      map.set(a.eletronico_id, u?.nome ?? `#${a.user_id}`)
    }
    return map
  }, [assocsEl, users])

  const filtrados = useMemo(
    () =>
      eletronicos.filter((e) => {
        if (ccsSel.size > 0 && !ccsSel.has(e.centro_custo)) return false
        if (statusSel.size > 0 && !statusSel.has(e.status)) return false
        if (tiposSel.size > 0 && !tiposSel.has(e.tipo)) return false
        if (localizacoesSel.size > 0) {
          const loc = e.localizacao ? e.localizacao : SEM_LOCALIZACAO
          if (!localizacoesSel.has(loc)) return false
        }
        return true
      }),
    [eletronicos, ccsSel, statusSel, tiposSel, localizacoesSel],
  )

  const agrupado = useMemo(() => {
    const grupos = new Map<string, Eletronico[]>()
    for (const e of filtrados) {
      let key: string
      if (agrupamento === 'responsavel') {
        key = responsavelPorEqId.get(e.id) ?? '(Sem responsável)'
      } else if (agrupamento === 'localizacao') {
        key = e.localizacao ? e.localizacao : SEM_LOCALIZACAO
      } else {
        const v = e[agrupamento as keyof Eletronico]
        key = v == null || v === '' ? '—' : String(v)
      }
      const arr = grupos.get(key) ?? []
      arr.push(e)
      grupos.set(key, arr)
    }
    return Array.from(grupos.entries()).sort(([a], [b]) =>
      a.localeCompare(b),
    )
  }, [filtrados, agrupamento, responsavelPorEqId])

  if (!user || !authChecked || !authorized) return null

  const colunasOrdenadas = COLUNAS.filter((c) => colunasSel.has(c.key))
  const contratoPorCc = new Map(contratos.map((c) => [c.centro_custo, c]))
  const agrupLabel =
    AGRUPAMENTOS.find((a) => a.key === agrupamento)?.label ?? agrupamento

  function getCellValue(e: Eletronico, key: ColKey): string {
    if (key === 'responsavel') {
      return responsavelPorEqId.get(e.id) ?? '—'
    }
    const v = e[key]
    if (key === 'ip') {
      const s = v == null ? '' : String(v).trim()
      return s || 'Sem IP'
    }
    return v == null ? '' : String(v)
  }

  function toggleSet<T>(s: Set<T>, v: T, setter: (s: Set<T>) => void) {
    const n = new Set(s)
    if (n.has(v)) n.delete(v)
    else n.add(v)
    setter(n)
  }

  function selectAll<T>(values: T[], setter: (s: Set<T>) => void) {
    setter(new Set(values))
  }

  function clearAll<T>(setter: (s: Set<T>) => void) {
    setter(new Set())
  }

  function csvEscape(v: unknown): string {
    const s = v == null ? '' : String(v)
    if (s.includes(';') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`
    }
    return s
  }

  function baixarCSV() {
    if (filtrados.length === 0) {
      toast.error('Nenhum equipamento no filtro.')
      return
    }
    const headers = [agrupLabel, ...colunasOrdenadas.map((c) => c.label)]
    const lines: string[] = [headers.join(';')]

    for (const [grupo, equips] of agrupado) {
      const contrato =
        agrupamento === 'centro_custo' ? contratoPorCc.get(grupo) : null
      const desc = contrato ? ` — ${contrato.descricao}` : ''
      lines.push(csvEscape(`▶ ${grupo}${desc} (${equips.length})`))
      for (const e of equips) {
        const row = [
          csvEscape(grupo),
          ...colunasOrdenadas.map((c) => csvEscape(getCellValue(e, c.key))),
        ]
        lines.push(row.join(';'))
      }
      lines.push('')
    }

    const csv = '﻿' + lines.join('\r\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${titulo.replace(/\s+/g, '_')}_${new Date()
      .toISOString()
      .slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV baixado — abra no Excel.')
  }

  function imprimirPDF() {
    if (filtrados.length === 0) {
      toast.error('Nenhum equipamento no filtro.')
      return
    }
    window.print()
  }

  const userIdsGestores = new Set(
    assocs.filter((a) => a.ocupacao === 'Gestor').map((a) => a.user_id),
  )
  const gestoresOptions = users.filter((u) => userIdsGestores.has(u.id))
  const gestoresFiltrados = gestoresOptions.filter((u) =>
    u.nome.toLowerCase().includes(gestorSearch.toLowerCase()),
  )
  const gestoresSelecionados = gestoresOptions.filter((u) =>
    gestorIds.has(u.id),
  )
  const ccsDoGestores = [
    ...new Set(
      assocs
        .filter((a) => gestorIds.has(a.user_id) && a.ocupacao === 'Gestor')
        .map((a) => a.centro_custo),
    ),
  ]

  const locsFiltradas = todasLocalizacoes.filter((l) =>
    l.toLowerCase().includes(locSearch.toLowerCase()),
  )

  const chips = [
    ccsSel.size > 0 && {
      label: `${ccsSel.size} CC(s)`,
      value: Array.from(ccsSel).join(', '),
    },
    localizacoesSel.size > 0 && {
      label: `${localizacoesSel.size} local(is)`,
      value: Array.from(localizacoesSel).join(', '),
    },
    statusSel.size < STATUSES.length && {
      label: 'Status',
      value: Array.from(statusSel).join(', '),
    },
    tiposSel.size < tiposNomes.length && {
      label: 'Tipos',
      value: Array.from(tiposSel).join(', '),
    },
    gestoresSelecionados.length > 0 && {
      label: `${gestoresSelecionados.length} gestor(es)`,
      value: gestoresSelecionados.map((g) => g.nome).join(', '),
    },
  ].filter(Boolean) as { label: string; value: string }[]

  return (
    <>
      <div className="space-y-6 print:hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Relatórios</h1>
            <p className="text-sm text-muted-foreground">
              Configure os filtros, escolha as colunas e exporte
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={baixarCSV}>
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Excel (CSV)
            </Button>
            <Button onClick={imprimirPDF}>
              <Printer className="mr-2 h-4 w-4" />
              PDF
            </Button>
          </div>
        </div>

        {/* Filtros */}
        <section className="rounded-lg border bg-card">
          <header className="flex items-center justify-between gap-2 border-b px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Filtros</h2>
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={buscarComFiltros}
              disabled={loadingData}
            >
              <Search className="mr-1.5 h-3.5 w-3.5" />
              {loadingData ? 'Buscando…' : 'Buscar no servidor'}
            </Button>
          </header>
          <div className="space-y-4 p-4">
            <div className="space-y-1">
              <Label>Título do relatório</Label>
              <Input
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
              />
            </div>

            {isAdminOuTI && (
              <div className="rounded-md border border-dashed bg-muted/30 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                    Atalho: filtrar por Gestor
                  </Label>
                  {gestorIds.size > 0 && (
                    <button
                      type="button"
                      onClick={() => setGestorIds(new Set())}
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      limpar seleção
                    </button>
                  )}
                </div>
                <Input
                  placeholder="Buscar gestor…"
                  value={gestorSearch}
                  onChange={(e) => setGestorSearch(e.target.value)}
                  className="mb-2 h-7 text-xs"
                />
                <div className="max-h-36 space-y-0.5 overflow-auto rounded-md border bg-background p-1">
                  {gestoresFiltrados.length === 0 && (
                    <p className="px-2 py-2 text-xs text-muted-foreground">
                      {gestoresOptions.length === 0
                        ? 'Nenhum gestor cadastrado'
                        : 'Nenhum resultado'}
                    </p>
                  )}
                  {gestoresFiltrados.map((u) => (
                    <label
                      key={u.id}
                      className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={gestorIds.has(u.id)}
                        onChange={() =>
                          toggleSet(gestorIds, u.id, setGestorIds)
                        }
                      />
                      {u.nome}
                    </label>
                  ))}
                </div>
                {gestoresSelecionados.length > 0 && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    {ccsDoGestores.length === 0
                      ? 'Gestores selecionados não gerenciam nenhum CC'
                      : `Auto-selecionados: ${ccsDoGestores.join(', ')}`}
                  </p>
                )}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {/* CCs */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <Label>Centros de Custo</Label>
                  <div className="flex gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() =>
                        selectAll(
                          contratos.map((c) => c.centro_custo),
                          setCcsSel,
                        )
                      }
                      className="text-primary hover:underline"
                    >
                      todos
                    </button>
                    <button
                      type="button"
                      onClick={() => clearAll(setCcsSel)}
                      className="text-muted-foreground hover:underline"
                    >
                      limpar
                    </button>
                  </div>
                </div>
                <div className="max-h-44 space-y-0.5 overflow-auto rounded-md border p-2">
                  {contratos.length === 0 && (
                    <p className="px-1 py-2 text-xs text-muted-foreground">
                      Nenhum CC disponível
                    </p>
                  )}
                  {contratos.map((c) => (
                    <label
                      key={c.centro_custo}
                      className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={ccsSel.has(c.centro_custo)}
                        onChange={() =>
                          toggleSet(ccsSel, c.centro_custo, setCcsSel)
                        }
                      />
                      <span className="font-medium">{c.centro_custo}</span>
                      <span className="truncate text-xs text-muted-foreground">
                        {c.descricao}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Vazio = todos visíveis
                </p>
              </div>

              {/* Localização */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <Label>Localização</Label>
                  <div className="flex gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => {
                        clearAll(setLocalizacoesSel)
                        setLocSearch('')
                      }}
                      className="text-primary hover:underline"
                    >
                      todas
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        selectAll(todasLocalizacoes, setLocalizacoesSel)
                      }
                      className="text-muted-foreground hover:underline"
                    >
                      limpar
                    </button>
                  </div>
                </div>
                <Input
                  placeholder="Pesquisar…"
                  value={locSearch}
                  onChange={(e) => setLocSearch(e.target.value)}
                  className="mb-1 h-7 text-xs"
                />
                <div className="max-h-36 space-y-0.5 overflow-auto rounded-md border p-2">
                  {todasLocalizacoes.length === 0 && (
                    <p className="px-1 py-2 text-xs text-muted-foreground">
                      Nenhuma localização cadastrada
                    </p>
                  )}
                  {locsFiltradas.map((loc) => (
                    <label
                      key={loc}
                      className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={
                          localizacoesSel.size === 0 ||
                          localizacoesSel.has(loc)
                        }
                        onChange={() => {
                          if (localizacoesSel.size === 0) {
                            // Sair do modo "todas" excluindo apenas esta
                            const todas = new Set(todasLocalizacoes)
                            todas.delete(loc)
                            setLocalizacoesSel(todas)
                          } else {
                            toggleSet(localizacoesSel, loc, setLocalizacoesSel)
                          }
                        }}
                      />
                      <span
                        className={
                          loc === SEM_LOCALIZACAO
                            ? 'italic text-muted-foreground'
                            : ''
                        }
                      >
                        {loc}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Vazio = todas visíveis
                </p>
              </div>

              {/* Status */}
              <div>
                <Label className="mb-2 block">Status</Label>
                <div className="space-y-0.5 rounded-md border p-2">
                  {STATUSES.map((s) => (
                    <label
                      key={s}
                      className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={statusSel.has(s)}
                        onChange={() => toggleSet(statusSel, s, setStatusSel)}
                      />
                      {s}
                    </label>
                  ))}
                </div>
              </div>

              {/* Tipos */}
              <div>
                <Label className="mb-2 block">Tipos</Label>
                <div className="space-y-0.5 rounded-md border p-2">
                  {tiposNomes.map((t) => (
                    <label
                      key={t}
                      className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
                    >
                      <input
                        type="checkbox"
                        checked={tiposSel.has(t)}
                        onChange={() => toggleSet(tiposSel, t, setTiposSel)}
                      />
                      {t}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Agrupamento */}
        <section className="rounded-lg border bg-card">
          <header className="flex items-center gap-2 border-b px-4 py-2.5">
            <Layers className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Agrupar por</h2>
          </header>
          <div className="flex flex-wrap gap-2 p-4">
            {AGRUPAMENTOS.map((a) => (
              <button
                key={a.key}
                type="button"
                onClick={() => setAgrupamento(a.key)}
                className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                  agrupamento === a.key
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background hover:bg-muted'
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </section>

        {/* Colunas */}
        <section className="rounded-lg border bg-card">
          <header className="flex items-center justify-between border-b px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Columns3 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Colunas</h2>
            </div>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={() =>
                  selectAll(
                    COLUNAS.map((c) => c.key),
                    setColunasSel,
                  )
                }
                className="text-primary hover:underline"
              >
                todas
              </button>
              <button
                type="button"
                onClick={() => clearAll(setColunasSel)}
                className="text-muted-foreground hover:underline"
              >
                limpar
              </button>
            </div>
          </header>
          <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-3 lg:grid-cols-4">
            {COLUNAS.map((c) => (
              <label
                key={c.key}
                className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
              >
                <input
                  type="checkbox"
                  checked={colunasSel.has(c.key)}
                  onChange={() => toggleSet(colunasSel, c.key, setColunasSel)}
                />
                {c.label}
              </label>
            ))}
          </div>
        </section>

        {/* Resumo */}
        <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 px-4 py-3 text-sm">
          <span>
            <strong>{filtrados.length}</strong> equipamento(s) ·{' '}
            <strong>{agrupado.length}</strong> grupo(s) · por{' '}
            <strong>{agrupLabel}</strong>
          </span>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1 sm:ml-auto">
              {chips.map((c, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  {c.label}: {c.value}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Preview agrupado */}
        {agrupado.length === 0 ? (
          <div className="rounded-md border bg-card p-8 text-center text-sm text-muted-foreground">
            Ajuste os filtros para ver resultados.
          </div>
        ) : (
          <div className="space-y-3">
            {agrupado.map(([grupo, equips]) => {
              const descricao =
                agrupamento === 'centro_custo'
                  ? contratoPorCc.get(grupo)?.descricao
                  : undefined
              return (
                <GrupoRelatorio
                  key={grupo}
                  titulo={grupo}
                  descricao={descricao}
                  equips={equips}
                  colunas={colunasOrdenadas}
                  getCellValue={getCellValue}
                />
              )
            })}
          </div>
        )}
      </div>

      {/* PDF (somente impressão) */}
      <div className="hidden bg-white p-6 text-black print:block">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold">{titulo}</h1>
            <p className="text-xs">
              Gerado em {new Date().toLocaleString('pt-BR')} ·{' '}
              {filtrados.length} equipamento(s) · {agrupado.length} grupo(s) ·
              por {agrupLabel}
            </p>
            {chips.length > 0 && (
              <p className="mt-1 text-[10px]">
                <strong>Filtros:</strong>{' '}
                {chips.map((c) => `${c.label}: ${c.value}`).join(' · ')}
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-lg font-bold tracking-tight">UFC</div>
            <div className="text-[10px] tracking-widest text-gray-600">
              ENGENHARIA
            </div>
          </div>
        </div>

        {agrupado.map(([grupo, equips]) => {
          const contrato =
            agrupamento === 'centro_custo' ? contratoPorCc.get(grupo) : null
          const nCols = colunasOrdenadas.length || 1
          return (
            <div key={grupo} className="mb-6">
              <table className="w-full border-collapse text-[10px]">
                <thead>
                  <tr>
                    <td
                      colSpan={nCols}
                      className="border border-black bg-gray-800 px-1.5 py-0.5 text-left font-bold text-white"
                    >
                      {agrupamento === 'centro_custo' ? 'CC ' : ''}
                      {grupo}
                      {contrato && (
                        <span className="ml-1 font-normal text-gray-300">
                          — {contrato.descricao}
                        </span>
                      )}
                      <span className="float-right font-normal text-gray-300">
                        {equips.length} equipamento(s)
                      </span>
                    </td>
                  </tr>
                  <tr>
                    {colunasOrdenadas.map((c) => (
                      <th
                        key={c.key}
                        className="border border-black bg-gray-200 px-1 py-0.5 text-left"
                      >
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {equips.map((e) => (
                    <tr key={e.id} className="break-inside-avoid">
                      {colunasOrdenadas.map((c) => (
                        <td
                          key={c.key}
                          className="border border-black px-1 py-0.5"
                        >
                          {getCellValue(e, c.key) || '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        })}
      </div>
    </>
  )
}

function GrupoRelatorio({
  titulo,
  descricao,
  equips,
  colunas,
  getCellValue,
}: {
  titulo: string
  descricao?: string
  equips: Eletronico[]
  colunas: { key: ColKey; label: string }[]
  getCellValue: (e: Eletronico, key: ColKey) => string
}) {
  const [aberto, setAberto] = useState(true)
  return (
    <div className="rounded-md border bg-card">
      <button
        type="button"
        onClick={() => setAberto(!aberto)}
        className="flex w-full items-center justify-between border-b px-4 py-2.5 text-left hover:bg-muted/50"
      >
        <div className="flex flex-wrap items-center gap-2">
          {aberto ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <Badge variant="default">{titulo}</Badge>
          {descricao && (
            <span className="text-sm text-muted-foreground">{descricao}</span>
          )}
        </div>
        <span className="ml-2 shrink-0 text-xs text-muted-foreground">
          {equips.length} equipamento(s)
        </span>
      </button>
      {aberto && colunas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                {colunas.map((c) => (
                  <th
                    key={c.key}
                    className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                  >
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {equips.map((e) => (
                <tr key={e.id} className="border-b last:border-0">
                  {colunas.map((c) => (
                    <td key={c.key} className="px-3 py-2">
                      {getCellValue(e, c.key) || '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
