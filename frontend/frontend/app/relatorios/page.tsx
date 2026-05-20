'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import { getEletronicos } from '@/lib/api/eletronicos'
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
import { SearchableSelect } from '@/components/app/searchable-select'
import {
  FileSpreadsheet,
  Printer,
  Filter,
  Columns3,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'

type ColKey = keyof Eletronico | 'responsavel'

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
  const tiposNomes = useMemo(
    () => tiposCatalogo.map((t) => t.nome),
    [tiposCatalogo],
  )

  const [ccsSel, setCcsSel] = useState<Set<string>>(new Set())
  const [statusSel, setStatusSel] = useState<Set<string>>(new Set(STATUSES))
  const [tiposSel, setTiposSel] = useState<Set<string>>(new Set())
  const [gestorId, setGestorId] = useState<string>('')
  const [colunasSel, setColunasSel] = useState<Set<ColKey>>(
    new Set(COLUNAS.map((c) => c.key).filter((k) => k !== 'centro_custo')),
  )
  const [titulo, setTitulo] = useState('Relatório de Equipamentos')

  const isAdminOuTI = user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'

  // Autorização per-CC: Admin/TI sempre, ou usuário com pelo menos
  // uma associação Gestor/Subgestor em algum CC.
  useEffect(() => {
    if (!user) return
    const isAdminOuTIUser =
      user.tipo === 'Admin' || user.tipo === 'Tecnico_TI'

    if (isAdminOuTIUser) {
      setAuthorized(true)
      setAuthChecked(true)
      getEletronicos().then(setEletronicos).catch(() => {})
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

    // Para demais papéis: precisa ter Gestor/Subgestor em ao menos um CC
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
        getEletronicos().then(setEletronicos).catch(() => {})
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

  // Quando troca o gestor, auto-popula os CCs com os que ele gerencia
  useEffect(() => {
    if (!gestorId) return
    const id = parseInt(gestorId)
    const ccs = assocs
      .filter((a) => a.user_id === id && a.ocupacao === 'Gestor')
      .map((a) => a.centro_custo)
    setCcsSel(new Set(ccs))
  }, [gestorId, assocs])

  const filtrados = useMemo(
    () =>
      eletronicos.filter((e) => {
        if (ccsSel.size > 0 && !ccsSel.has(e.centro_custo)) return false
        if (statusSel.size > 0 && !statusSel.has(e.status)) return false
        if (tiposSel.size > 0 && !tiposSel.has(e.tipo)) return false
        return true
      }),
    [eletronicos, ccsSel, statusSel, tiposSel],
  )

  // Agrupa por CC
  const agrupado = useMemo(() => {
    const grupos = new Map<string, Eletronico[]>()
    for (const e of filtrados) {
      const arr = grupos.get(e.centro_custo) ?? []
      arr.push(e)
      grupos.set(e.centro_custo, arr)
    }
    return Array.from(grupos.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [filtrados])

  if (!user || !authChecked || !authorized) return null

  const colunasOrdenadas = COLUNAS.filter((c) => colunasSel.has(c.key))
  const contratoPorCc = new Map(contratos.map((c) => [c.centro_custo, c]))

  const responsavelPorEqId = new Map<number, string>()
  for (const a of assocsEl) {
    if (responsavelPorEqId.has(a.eletronico_id)) continue
    const u = users.find((x) => x.id === a.user_id)
    responsavelPorEqId.set(a.eletronico_id, u?.nome ?? `#${a.user_id}`)
  }

  function getCellValue(e: Eletronico, key: ColKey): string {
    if (key === 'responsavel') {
      return responsavelPorEqId.get(e.id) ?? '—'
    }
    const v = e[key]
    // IP é opcional — quando vazio/null, deixar explícito "Sem IP".
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
    const headers = ['Centro de Custo', ...colunasOrdenadas.map((c) => c.label)]
    const lines: string[] = [headers.join(';')]

    for (const [cc, equips] of agrupado) {
      const contrato = contratoPorCc.get(cc)
      const desc = contrato ? ` — ${contrato.descricao}` : ''
      lines.push(csvEscape(`▶ CC ${cc}${desc} (${equips.length})`))
      for (const e of equips) {
        const row = [
          csvEscape(cc),
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

  const gestor = gestorId ? users.find((u) => u.id === parseInt(gestorId)) : null
  const ccsDoGestor = gestorId
    ? assocs
        .filter(
          (a) => a.user_id === parseInt(gestorId) && a.ocupacao === 'Gestor',
        )
        .map((a) => a.centro_custo)
    : []

  const chips = [
    ccsSel.size > 0 && {
      label: `${ccsSel.size} CC(s)`,
      value: Array.from(ccsSel).join(', '),
    },
    statusSel.size < STATUSES.length && {
      label: 'Status',
      value: Array.from(statusSel).join(', '),
    },
    tiposSel.size < tiposNomes.length && {
      label: 'Tipos',
      value: Array.from(tiposSel).join(', '),
    },
    gestor && { label: 'Gestor', value: gestor.nome },
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
          <div className="flex gap-2">
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
          <header className="flex items-center gap-2 border-b px-4 py-2.5">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Filtros</h2>
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
              <div className="space-y-1 rounded-md border border-dashed bg-muted/30 p-3">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Atalho: filtrar por Gestor
                </Label>
                <SearchableSelect
                  value={gestorId}
                  onChange={setGestorId}
                  options={[
                    { value: '', label: 'Nenhum' },
                    ...gestoresOptions.map((u) => ({
                      value: String(u.id),
                      label: u.nome,
                      searchKey: `${u.nome} ${u.email}`,
                    })),
                  ]}
                  placeholder={
                    gestoresOptions.length === 0
                      ? 'Nenhum gestor cadastrado'
                      : 'Selecione um Gestor'
                  }
                />
                {gestor && (
                  <p className="text-xs text-muted-foreground">
                    {ccsDoGestor.length === 0
                      ? `${gestor.nome} não gerencia nenhum CC`
                      : `Auto-selecionados: ${ccsDoGestor.join(', ')}`}
                  </p>
                )}
              </div>
            )}

            <div className="grid gap-4 lg:grid-cols-3">
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
                <div className="max-h-44 space-y-1 overflow-auto rounded-md border p-2">
                  {contratos.length === 0 && (
                    <p className="px-1 py-2 text-xs text-muted-foreground">
                      Nenhum CC disponível
                    </p>
                  )}
                  {contratos.map((c) => (
                    <label
                      key={c.centro_custo}
                      className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
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

              {/* Status */}
              <div>
                <Label className="mb-2 block">Status</Label>
                <div className="space-y-1 rounded-md border p-2">
                  {STATUSES.map((s) => (
                    <label
                      key={s}
                      className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
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
                <div className="space-y-1 rounded-md border p-2">
                  {tiposNomes.map((t) => (
                    <label
                      key={t}
                      className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
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
                className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-muted/50"
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
            <strong>{agrupado.length}</strong> CC(s)
          </span>
          {chips.length > 0 && (
            <div className="ml-auto flex flex-wrap gap-1">
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
            {agrupado.map(([cc, equips]) => {
              const contrato = contratoPorCc.get(cc)
              return (
                <GrupoCC
                  key={cc}
                  cc={cc}
                  descricao={contrato?.descricao}
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
              Gerado em {new Date().toLocaleString('pt-BR')} · {filtrados.length}{' '}
              equipamento(s) · {agrupado.length} CC(s)
            </p>
            {chips.length > 0 && (
              <p className="mt-1 text-[10px]">
                <strong>Filtros:</strong> {chips.map((c) => `${c.label}: ${c.value}`).join(' · ')}
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

        {agrupado.map(([cc, equips]) => {
          const contrato = contratoPorCc.get(cc)
          return (
            <div key={cc} className="mb-5 break-inside-avoid">
              <h2 className="mb-1 border-b border-black pb-0.5 text-sm font-bold">
                CC {cc}
                {contrato && (
                  <span className="ml-2 font-normal">— {contrato.descricao}</span>
                )}
                <span className="float-right text-[10px] font-normal">
                  {equips.length} equipamento(s)
                </span>
              </h2>
              <table className="w-full border-collapse text-[10px]">
                <thead>
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
                    <tr key={e.id}>
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

function GrupoCC({
  cc,
  descricao,
  equips,
  colunas,
  getCellValue,
}: {
  cc: string
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
        <div className="flex items-center gap-2">
          {aberto ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <Badge variant="default">{cc}</Badge>
          {descricao && (
            <span className="text-sm text-muted-foreground">{descricao}</span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
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
