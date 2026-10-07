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
import { getCessoes, type Cessao } from '@/lib/api/cessoes'
import { getTipos, type TipoEletronico } from '@/lib/api/tipos'
import type {
  Eletronico,
  EletronicoStatus,
  Contrato,
  User,
  AssociacaoUserContrato,
  AssociacaoUserEletronico,
} from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ROTULO_STATUS } from '@/components/app/status'
import { cn } from '@/lib/utils'
import { Download, FileText } from 'lucide-react'

type ColKey = keyof Eletronico | 'responsavel'
type AgrupamentoKey =
  | 'centro_custo'
  | 'tipo'
  | 'localizacao'
  | 'status'
  | 'responsavel'
  | 'marca'
  | ''

// Na ordem do protótipo; as três últimas só existem no sistema.
const COLUNAS: { key: ColKey; label: string; mono?: boolean }[] = [
  { key: 'numero_patrimonio', label: 'Patrimônio', mono: true },
  { key: 'nome', label: 'Equipamento' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'modelo', label: 'Modelo' },
  { key: 'numero_serie', label: 'Série', mono: true },
  { key: 'status', label: 'Situação' },
  { key: 'localizacao', label: 'Localização' },
  { key: 'responsavel', label: 'Responsável' },
  { key: 'ip', label: 'IP', mono: true },
  { key: 'marca', label: 'Marca' },
  { key: 'centro_custo', label: 'Centro de custo' },
  { key: 'descricao', label: 'Descrição' },
]
const COLUNAS_PADRAO: ColKey[] = ['numero_patrimonio', 'nome', 'tipo', 'status', 'localizacao', 'responsavel']

const STATUSES: EletronicoStatus[] = ['Interno', 'Externo', 'Em Manutenção']

const AGRUPAMENTOS: { key: AgrupamentoKey; label: string }[] = [
  { key: 'centro_custo', label: 'Centro de custo' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'localizacao', label: 'Localização' },
  { key: 'status', label: 'Situação' },
  { key: 'responsavel', label: 'Responsável' },
  { key: 'marca', label: 'Marca' },
  { key: '', label: 'Sem agrupar' },
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

/** Caixas de marcar no estilo do protótipo: legenda e uma opção por linha. */
function Grupo({
  titulo,
  acoes,
  children,
}: {
  titulo: string
  acoes?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-1.5">
      <legend className="mb-1 flex w-full items-center justify-between text-[12.5px] font-semibold">
        {titulo}
        {acoes && <span className="flex gap-2 text-xs font-normal">{acoes}</span>}
      </legend>
      {children}
    </fieldset>
  )
}

function Opcao({ checked, onChange, children }: { checked: boolean; onChange: () => void; children: React.ReactNode }) {
  return (
    <label className="flex min-w-0 cursor-pointer items-center gap-2 text-[13px]">
      <input type="checkbox" checked={checked} onChange={onChange} />
      {children}
    </label>
  )
}

function Lk({ onClick, children, apagado }: { onClick: () => void; children: React.ReactNode; apagado?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn('hover:underline', apagado ? 'text-muted-foreground' : 'text-primary')}
    >
      {children}
    </button>
  )
}

export default function RelatoriosPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [assocs, setAssocs] = useState<AssociacaoUserContrato[]>([])
  const [assocsEl, setAssocsEl] = useState<AssociacaoUserEletronico[]>([])
  const [cessoes, setCessoes] = useState<Cessao[]>([])
  const [authChecked, setAuthChecked] = useState(false)
  const [authorized, setAuthorized] = useState(false)
  const [tiposCatalogo, setTiposCatalogo] = useState<TipoEletronico[]>([])

  const tiposNomes = useMemo(() => tiposCatalogo.map((t) => t.nome), [tiposCatalogo])

  const [titulo, setTitulo] = useState('Inventário por centro de custo')
  const [agrupamento, setAgrupamento] = useState<AgrupamentoKey>('centro_custo')
  const [statusSel, setStatusSel] = useState<Set<string>>(new Set(STATUSES))
  const [tiposSel, setTiposSel] = useState<Set<string>>(new Set())
  const [colunasSel, setColunasSel] = useState<Set<ColKey>>(new Set(COLUNAS_PADRAO))
  const [ccsSel, setCcsSel] = useState<Set<string>>(new Set())
  const [ccSearch, setCcSearch] = useState('')
  const [localizacoesSel, setLocalizacoesSel] = useState<Set<string>>(new Set())
  const [locSearch, setLocSearch] = useState('')
  const [gestorIds, setGestorIds] = useState<Set<number>>(new Set())

  const isAdminOuTI = user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'

  useEffect(() => {
    if (!user) return
    const carregar = () => {
      fetchAll({}).then(setEletronicos).catch(() => {})
      getContratos().then(setContratos).catch(() => {})
      getUsers().then(setUsers).catch(() => {})
      getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
      getCessoes().then(setCessoes).catch(() => {})
      getTipos(true)
        .then((tipos) => {
          setTiposCatalogo(tipos)
          setTiposSel(new Set(tipos.map((t) => t.nome)))
        })
        .catch(() => {})
    }

    if (user.tipo === 'Admin' || user.tipo === 'Tecnico_TI') {
      setAuthorized(true)
      setAuthChecked(true)
      getAssociacoesContrato().then(setAssocs).catch(() => {})
      carregar()
      return
    }

    getAssociacoesContrato()
      .then((all) => {
        setAssocs(all)
        const ehGestorOuSub = all.some(
          (a) => a.user_id === user.id && (a.ocupacao === 'Gestor' || a.ocupacao === 'Subgestor'),
        )
        if (!ehGestorOuSub) {
          toast.error('Apenas Gestores/Subgestores de algum CC podem gerar relatórios.')
          router.replace('/')
          return
        }
        setAuthorized(true)
        carregar()
      })
      .catch(() => router.replace('/'))
      .finally(() => setAuthChecked(true))
  }, [user, router])

  const todasLocalizacoes = useMemo(() => {
    const set = new Set<string>()
    for (const e of eletronicos) set.add(e.localizacao ? e.localizacao : SEM_LOCALIZACAO)
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

  const responsavelCessaoPorEqId = useMemo(() => {
    const map = new Map<number, string>()
    for (const c of cessoes) for (const e of c.eletronicos) if (e.devolvido_em === null) map.set(e.id, c.responsavel)
    return map
  }, [cessoes])

  const filtrados = useMemo(
    () =>
      eletronicos.filter((e) => {
        if (ccsSel.size > 0 && !ccsSel.has(e.centro_custo)) return false
        if (!statusSel.has(e.status)) return false
        if (tiposNomes.length > 0 && !tiposSel.has(e.tipo)) return false
        if (localizacoesSel.size > 0 && !localizacoesSel.has(e.localizacao || SEM_LOCALIZACAO)) return false
        return true
      }),
    [eletronicos, ccsSel, statusSel, tiposSel, tiposNomes, localizacoesSel],
  )

  const contratoPorCc = useMemo(() => new Map(contratos.map((c) => [c.centro_custo, c])), [contratos])

  function responsavelDe(e: Eletronico): string {
    if (e.status === 'Externo') {
      const r = responsavelCessaoPorEqId.get(e.id)
      if (r) return r
    }
    return responsavelPorEqId.get(e.id) ?? ''
  }

  function rotuloGrupo(e: Eletronico): string {
    switch (agrupamento) {
      case 'centro_custo': {
        const d = contratoPorCc.get(e.centro_custo)?.descricao
        return `CR ${e.centro_custo}${d ? ` · ${d}` : ''}`
      }
      case 'status':
        return ROTULO_STATUS[e.status]
      case 'localizacao':
        return e.localizacao || SEM_LOCALIZACAO
      case 'responsavel':
        return responsavelDe(e) || '(Sem responsável)'
      case '':
        return ''
      default:
        return String(e[agrupamento] || '—')
    }
  }

  const grupos = useMemo(() => {
    const m = new Map<string, Eletronico[]>()
    for (const e of filtrados) {
      const k = rotuloGrupo(e)
      const arr = m.get(k) ?? []
      arr.push(e)
      m.set(k, arr)
    }
    return Array.from(m.entries()).sort(([a], [b]) => a.localeCompare(b))
    // rotuloGrupo depende só destes valores
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtrados, agrupamento, contratoPorCc, responsavelPorEqId, responsavelCessaoPorEqId])

  if (!user || !authChecked || !authorized) return null

  const colunas = COLUNAS.filter((c) => colunasSel.has(c.key))
  const nCols = colunas.length || 1

  function valor(e: Eletronico, key: ColKey): string {
    if (key === 'responsavel') return responsavelDe(e)
    if (key === 'status') return ROTULO_STATUS[e.status]
    const v = e[key]
    return v == null ? '' : String(v)
  }

  function alternar<T>(s: Set<T>, v: T, setter: (s: Set<T>) => void) {
    const n = new Set(s)
    if (n.has(v)) n.delete(v)
    else n.add(v)
    setter(n)
  }

  function escolherGestor(id: number) {
    const n = new Set(gestorIds)
    if (n.has(id)) n.delete(id)
    else n.add(id)
    setGestorIds(n)
    if (n.size > 0) {
      setCcsSel(
        new Set(assocs.filter((a) => n.has(a.user_id) && a.ocupacao === 'Gestor').map((a) => a.centro_custo)),
      )
    }
  }

  function csv(v: unknown): string {
    const s = v == null ? '' : String(v)
    return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }

  function baixarExcel() {
    if (filtrados.length === 0) {
      toast.error('Nenhum equipamento no recorte.')
      return
    }
    const linhas: string[] = [[...(agrupamento ? ['Grupo'] : []), ...colunas.map((c) => c.label)].join(';')]
    for (const [g, eqs] of grupos)
      for (const e of eqs) linhas.push([...(agrupamento ? [csv(g)] : []), ...colunas.map((c) => csv(valor(e, c.key)))].join(';'))
    const blob = new Blob(['﻿' + linhas.join('\r\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${titulo.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Planilha baixada — abre no Excel.')
  }

  function gerarPDF() {
    if (filtrados.length === 0) {
      toast.error('Nenhum equipamento no recorte.')
      return
    }
    window.print()
  }

  const gestores = users
    .filter((u) => assocs.some((a) => a.user_id === u.id && a.ocupacao === 'Gestor'))
    .sort((a, b) => a.nome.localeCompare(b.nome))
  const ccsVisiveis = contratos.filter((c) =>
    `${c.centro_custo} ${c.descricao}`.toLowerCase().includes(ccSearch.toLowerCase()),
  )
  const locsVisiveis = todasLocalizacoes.filter((l) => l.toLowerCase().includes(locSearch.toLowerCase()))
  const hoje = new Date().toLocaleDateString('pt-BR')

  // A mesma folha na prévia e na impressão.
  const folha = (
    <div className="text-[11.5px] text-[#1f1514]">
      <div className="mb-2.5 flex items-end justify-between gap-3 border-b-2 border-primary pb-2">
        <div>
          <div className="text-[10px] uppercase tracking-[.08em] text-[#8a7570]">UFC Engenharia · InvControl</div>
          <h3 className="text-base font-bold">{titulo}</h3>
        </div>
        <div className="text-right text-[10.5px] text-[#8a7570]">
          {filtrados.length} equipamentos · {hoje}
        </div>
      </div>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {colunas.map((c) => (
              <th
                key={c.key}
                className="border-b border-[#e6dcd8] bg-[#f6f1ef] px-2 py-[5px] text-left text-[10.5px] font-semibold text-[#5b4b47]"
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grupos.map(([g, eqs]) => [
            g ? (
              <tr key={`g-${g}`} className="break-inside-avoid">
                <td colSpan={nCols} className="border-b border-[#efe7e4] bg-[#fbf6f4] px-2 py-[5px] text-[11px] font-semibold">
                  {g} · {eqs.length}
                </td>
              </tr>
            ) : null,
            ...eqs.map((e) => (
              <tr key={e.id} className="break-inside-avoid">
                {colunas.map((c) => (
                  <td
                    key={c.key}
                    className={cn('border-b border-[#efe7e4] px-2 py-[5px] text-[11px]', c.mono && 'font-mono')}
                  >
                    {valor(e, c.key) || '—'}
                  </td>
                ))}
              </tr>
            )),
          ])}
        </tbody>
      </table>
    </div>
  )

  return (
    <>
      <div className="space-y-5 print:hidden">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Relatórios</h1>
            <p className="text-sm text-muted-foreground">
              Monte o recorte à esquerda; a prévia ao lado é exatamente o que sai no PDF.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={baixarExcel}>
              <Download className="h-4 w-4" /> Excel
            </Button>
            <Button onClick={gerarPDF}>
              <FileText className="h-4 w-4" /> Gerar PDF
            </Button>
          </div>
        </div>

        <div className="grid items-start gap-[18px] lg:grid-cols-[300px_minmax(0,1fr)]">
          <div className="flex flex-col gap-3.5 rounded-xl border bg-card p-4 shadow-xs">
            <div>
              <label htmlFor="r-t" className="mb-1.5 block text-[12.5px] font-medium">Título</label>
              <Input id="r-t" value={titulo} onChange={(e) => setTitulo(e.target.value)} />
            </div>
            <div>
              <label htmlFor="r-g" className="mb-1.5 block text-[12.5px] font-medium">Agrupar por</label>
              <select
                id="r-g"
                value={agrupamento}
                onChange={(e) => setAgrupamento(e.target.value as AgrupamentoKey)}
                className="h-9 w-full rounded-md border bg-background px-2.5 text-sm"
              >
                {AGRUPAMENTOS.map((a) => (
                  <option key={a.key || 'nenhum'} value={a.key}>{a.label}</option>
                ))}
              </select>
            </div>

            <Grupo titulo="Situação">
              {STATUSES.map((s) => (
                <Opcao key={s} checked={statusSel.has(s)} onChange={() => alternar(statusSel, s, setStatusSel)}>
                  {ROTULO_STATUS[s]}
                </Opcao>
              ))}
            </Grupo>

            <Grupo titulo="Tipos">
              {tiposNomes.map((t) => (
                <Opcao key={t} checked={tiposSel.has(t)} onChange={() => alternar(tiposSel, t, setTiposSel)}>
                  {t}
                </Opcao>
              ))}
            </Grupo>

            <Grupo
              titulo="Colunas"
              acoes={
                <>
                  <Lk onClick={() => setColunasSel(new Set(COLUNAS.map((c) => c.key)))}>todas</Lk>
                  <Lk apagado onClick={() => setColunasSel(new Set(COLUNAS_PADRAO))}>padrão</Lk>
                </>
              }
            >
              {COLUNAS.map((c) => (
                <Opcao key={c.key} checked={colunasSel.has(c.key)} onChange={() => alternar(colunasSel, c.key, setColunasSel)}>
                  {c.label}
                </Opcao>
              ))}
            </Grupo>

            <Grupo
              titulo="Centros de custo"
              acoes={ccsSel.size > 0 && <Lk apagado onClick={() => { setCcsSel(new Set()); setGestorIds(new Set()) }}>limpar</Lk>}
            >
              <Input
                placeholder="Buscar CR…"
                value={ccSearch}
                onChange={(e) => setCcSearch(e.target.value)}
                className="h-8 text-xs"
              />
              <div className="flex max-h-40 flex-col gap-1.5 overflow-auto">
                {ccsVisiveis.map((c) => (
                  <Opcao
                    key={c.centro_custo}
                    checked={ccsSel.has(c.centro_custo)}
                    onChange={() => alternar(ccsSel, c.centro_custo, setCcsSel)}
                  >
                    <span className="font-medium">{c.centro_custo}</span>
                    <span className="truncate text-xs text-muted-foreground">{c.descricao}</span>
                  </Opcao>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">Nenhum marcado = todos</p>
            </Grupo>

            {isAdminOuTI && gestores.length > 0 && (
              <Grupo titulo="Por gestor" acoes={gestorIds.size > 0 && <Lk apagado onClick={() => setGestorIds(new Set())}>limpar</Lk>}>
                <div className="flex max-h-32 flex-col gap-1.5 overflow-auto">
                  {gestores.map((u) => (
                    <Opcao key={u.id} checked={gestorIds.has(u.id)} onChange={() => escolherGestor(u.id)}>
                      {u.nome}
                    </Opcao>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">Marca os CRs do gestor</p>
              </Grupo>
            )}

            <Grupo
              titulo="Localização"
              acoes={localizacoesSel.size > 0 && <Lk apagado onClick={() => setLocalizacoesSel(new Set())}>limpar</Lk>}
            >
              <Input
                placeholder="Buscar local…"
                value={locSearch}
                onChange={(e) => setLocSearch(e.target.value)}
                className="h-8 text-xs"
              />
              <div className="flex max-h-36 flex-col gap-1.5 overflow-auto">
                {locsVisiveis.map((l) => (
                  <Opcao key={l} checked={localizacoesSel.has(l)} onChange={() => alternar(localizacoesSel, l, setLocalizacoesSel)}>
                    <span className={cn(l === SEM_LOCALIZACAO && 'italic text-muted-foreground')}>{l}</span>
                  </Opcao>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">Nenhum marcado = todos</p>
            </Grupo>
          </div>

          <div className="lg:sticky lg:top-4">
            {filtrados.length === 0 ? (
              <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
                Nenhum equipamento nesse recorte.
              </div>
            ) : (
              <div className="max-h-[calc(100vh-9rem)] overflow-auto rounded-lg border bg-white px-6 py-[22px] shadow-sm">
                {folha}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="hidden bg-white print:block">{folha}</div>
    </>
  )
}
