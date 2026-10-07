'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getEletronicosPaginated,
  createEletronico,
  updateEletronico,
  deleteEletronico,
  getEletronicos,
  type CampoBuscaEletronico,
  type EletronicoPayload,
} from '@/lib/api/eletronicos'
import { getCessoes, type Cessao } from '@/lib/api/cessoes'
import { getContratos } from '@/lib/api/contratos'
import {
  getAssociacoesEletronico,
  createAssociacaoEletronico,
  deleteAssociacaoEletronico,
  getAssociacoesContrato,
} from '@/lib/api/associacoes'
import { getUsers } from '@/lib/api/users'
import { getTipos, type TipoEletronico } from '@/lib/api/tipos'
import {
  getLocalizacoes,
  createLocalizacao,
  type Localizacao,
} from '@/lib/api/localizacoes'
import { getMarcas, createMarca, type Marca } from '@/lib/api/marcas'
import { getModelos, createModelo, type Modelo } from '@/lib/api/modelos'
import type {
  Eletronico,
  Contrato,
  AssociacaoUserEletronico,
  AssociacaoUserContrato,
  User,
} from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Plus,
  Pencil,
  Trash2,
  FileText,
  ChevronLeft,
  ChevronRight,
  Users as UsersIcon,
  X,
  ArrowRight,
  LayoutGrid,
  List,
  MapPin,
  Wrench,
  Undo2,
  Download,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { FiltroMulti } from '@/components/app/filtro-multi'
import { StatusEquipamento, ROTULO_STATUS } from '@/components/app/status'
import { formatDate } from '@/lib/utils'
import { IconeTipo } from '@/components/app/icone-tipo'
import Link from 'next/link'
import { SearchableSelect } from '@/components/app/searchable-select'

function Ordenavel({
  col,
  ordem,
  onOrdenar,
  children,
}: {
  col: string
  ordem: { col: string; desc: boolean }
  onOrdenar: (col: string) => void
  children: React.ReactNode
}) {
  return (
    <th
      className="cursor-pointer select-none px-3 py-2 text-left font-medium hover:text-foreground"
      onClick={() => onOrdenar(col)}
      aria-sort={ordem.col === col ? (ordem.desc ? 'descending' : 'ascending') : undefined}
    >
      {children}
      {ordem.col === col && <span className="ml-1 text-primary">{ordem.desc ? '↓' : '↑'}</span>}
    </th>
  )
}

function payloadDe(e: Eletronico): EletronicoPayload {
  return {
    numero_serie: e.numero_serie,
    numero_patrimonio: e.numero_patrimonio,
    nome: e.nome,
    marca: e.marca ?? '',
    tipo: e.tipo,
    modelo: e.modelo ?? '',
    status: e.status,
    ip: e.ip ?? '',
    localizacao: e.localizacao ?? '',
    descricao: e.descricao ?? '',
    centro_custo: e.centro_custo,
  }
}

// TIPOS_EQUIPAMENTO agora vem do backend dinamicamente — ver useEffect.

const CAMPOS_BUSCA: Record<CampoBuscaEletronico, string> = {
  todos: 'Todos os campos',
  nome: 'Nome',
  numero_serie: 'Nº Série',
  numero_patrimonio: 'Nº Patrimônio',
  marca: 'Marca',
  modelo: 'Modelo',
  ip: 'IP',
  localizacao: 'Localização',
  responsavel: 'Responsável',
  sem_responsavel: 'Sem responsável',
}

const EMPTY = {
  numero_serie: '',
  numero_patrimonio: '',
  nome: '',
  marca: '',
  tipo: '',
  modelo: '',
  status: 'Interno',
  ip: '',
  localizacao: '',
  descricao: '',
  centro_custo: '',
}

function EquipamentosConteudo() {
  const { user } = useAuth()
  const router = useRouter()
  const busca = useSearchParams()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [search, setSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [campoBusca, setCampoBusca] =
    useState<CampoBuscaEletronico>('todos')
  // Os links do painel chegam com o filtro na URL (?status=…&tipo=…&id=…).
  const [filtroCC, setFiltroCC] = useState<string[]>(() => busca.getAll('centro_custo'))
  const [filtroStatus, setFiltroStatus] = useState<string[]>(() => busca.getAll('status'))
  const [filtroTipo, setFiltroTipo] = useState<string[]>(() => busca.getAll('tipo'))
  const [filtroLocal, setFiltroLocal] = useState<string[]>(() => busca.getAll('localizacao'))
  const [ordem, setOrdem] = useState<{ col: string; desc: boolean }>({ col: 'recentes', desc: false })
  const [exportando, setExportando] = useState(false)
  const [modo, setModo] = useState<'tabela' | 'cartoes'>('tabela')
  const [marcados, setMarcados] = useState<Map<number, Eletronico>>(new Map())
  const [detalheId, setDetalheId] = useState<number | null>(() => Number(busca.get('id')) || null)
  const [detalheAvulso, setDetalheAvulso] = useState<Eletronico | null>(null)
  const [cessoes, setCessoes] = useState<Cessao[]>([])
  const [localLoteOpen, setLocalLoteOpen] = useState(false)
  const [localLote, setLocalLote] = useState('')
  const [emLote, setEmLote] = useState(false)
  const [excluir, setExcluir] = useState<Eletronico | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<Eletronico | null>(null)
  const [form, setForm] = useState(EMPTY)
  const [novoResponsavelId, setNovoResponsavelId] = useState('')
  const [semIp, setSemIp] = useState(false)
  const [associarEq, setAssociarEq] = useState<Eletronico | null>(null)
  const [associarUserId, setAssociarUserId] = useState('')
  const [assocsEl, setAssocsEl] = useState<AssociacaoUserEletronico[]>([])
  const [assocsCC, setAssocsCC] = useState<AssociacaoUserContrato[]>([])
  const [allUsers, setAllUsers] = useState<User[]>([])
  const [tiposCatalogo, setTiposCatalogo] = useState<TipoEletronico[]>([])
  const [localizacoes, setLocalizacoes] = useState<Localizacao[]>([])
  const [novaLocOpen, setNovaLocOpen] = useState(false)
  const [novaLocNome, setNovaLocNome] = useState('')
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [modelos, setModelos] = useState<Modelo[]>([])
  const [novaMarcaOpen, setNovaMarcaOpen] = useState(false)
  const [novaMarcaNome, setNovaMarcaNome] = useState('')
  const [novoModeloOpen, setNovoModeloOpen] = useState(false)
  const [novoModeloNome, setNovoModeloNome] = useState('')
  const [novoModeloDescricao, setNovoModeloDescricao] = useState('')

  // Debounce do search
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Reseta para página 1 quando filtros ou page size mudam
  useEffect(() => {
    setPage(1)
  }, [searchDebounced, campoBusca, filtroCC, filtroStatus, filtroTipo, filtroLocal, ordem, pageSize])

  // Carrega dados quando filtros ou página mudam
  useEffect(() => {
    setLoading(true)
    getEletronicosPaginated({
      q: searchDebounced || undefined,
      campo: campoBusca,
      centro_custo: filtroCC.length ? filtroCC : undefined,
      status: filtroStatus.length ? filtroStatus : undefined,
      tipo: filtroTipo.length ? filtroTipo : undefined,
      localizacao: filtroLocal.length ? filtroLocal : undefined,
      ordem: ordem.col,
      desc: ordem.desc,
      page,
      page_size: pageSize,
    })
      .then((res) => {
        setEletronicos(res.eletronicos)
        setTotal(res.total)
        setPages(res.pages)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchDebounced, campoBusca, filtroCC, filtroStatus, filtroTipo, filtroLocal, ordem, page, pageSize])

  useEffect(() => {
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
    getAssociacoesContrato().then(setAssocsCC).catch(() => {})
    getUsers().then(setAllUsers).catch(() => {})
    // Catálogo dinâmico — só os ativos pra alimentar o select
    getTipos(true).then(setTiposCatalogo).catch(() => {})
    getLocalizacoes().then(setLocalizacoes).catch(() => {})
    getMarcas().then(setMarcas).catch(() => {})
    getModelos().then(setModelos).catch(() => {})
    getCessoes().then(setCessoes).catch(() => {})
  }, [])

  // Aberto pela busca global ou por link: o equipamento pode não estar nesta página.
  useEffect(() => {
    if (!detalheId || eletronicos.some((e) => e.id === detalheId)) return
    getEletronicos()
      .then((todos) => setDetalheAvulso(todos.find((e) => e.id === detalheId) ?? null))
      .catch(() => {})
  }, [detalheId, eletronicos])

  const detalhe =
    eletronicos.find((e) => e.id === detalheId) ??
    (detalheAvulso?.id === detalheId ? detalheAvulso : null)

  const historico = useMemo(
    () =>
      detalhe
        ? cessoes
            .filter((c) => c.eletronicos.some((x) => x.id === detalhe.id))
            .sort((a, b) => b.cedido_em.localeCompare(a.cedido_em))
        : [],
    [cessoes, detalhe],
  )

  function abrirDetalhe(id: number | null) {
    setDetalheId(id)
    // A URL acompanha, para o link poder ser copiado; sem recarregar a página.
    const url = new URL(window.location.href)
    if (id) url.searchParams.set('id', String(id))
    else url.searchParams.delete('id')
    window.history.replaceState(null, '', url)
  }

  function alternarMarcado(e: Eletronico) {
    setMarcados((m) => {
      const n = new Map(m)
      if (n.has(e.id)) n.delete(e.id)
      else n.set(e.id, e)
      return n
    })
  }

  const paginaMarcada = eletronicos.length > 0 && eletronicos.every((e) => marcados.has(e.id))
  function marcarPagina() {
    setMarcados((m) => {
      const n = new Map(m)
      eletronicos.forEach((e) => (paginaMarcada ? n.delete(e.id) : n.set(e.id, e)))
      return n
    })
  }

  const listaMarcada = [...marcados.values()]
  const internosMarcados = listaMarcada.filter((e) => e.status === 'Interno')
  const emManutencaoMarcados = listaMarcada.filter((e) => e.status === 'Em Manutenção')

  /** Uma alteração aplicada a vários; a API só edita um por vez. */
  async function aplicarEmLote(
    alvos: Eletronico[],
    mudar: (p: EletronicoPayload) => EletronicoPayload,
    feito: string,
  ) {
    setEmLote(true)
    let falhas = 0
    for (const e of alvos) {
      try {
        await updateEletronico(e.id, mudar(payloadDe(e)))
      } catch {
        falhas += 1
      }
    }
    setEmLote(false)
    if (falhas) toast.error(`${alvos.length - falhas} ${feito}; ${falhas} não puderam ser alterados.`)
    else toast.success(`${alvos.length} ${feito}.`)
    setMarcados(new Map())
    reload()
  }

  function cederMarcados() {
    const ids = internosMarcados.map((e) => e.id).join(',')
    router.push(`/equipamentos/ceder?ids=${ids}`)
  }

  const podeCeder =
    user?.tipo === 'Admin' ||
    user?.tipo === 'Tecnico_TI' ||
    user?.tipo === 'Gestor' ||
    user?.tipo === 'Subgestor'

  const filtrosAtivos =
    filtroCC.length + filtroStatus.length + filtroTipo.length + filtroLocal.length > 0 || search !== ''

  function ordenarPor(col: string) {
    setOrdem((o) => (o.col === col ? { col, desc: !o.desc } : { col, desc: false }))
  }

  /** CSV com tudo o que o filtro pega (todas as páginas), aberto direto no Excel. */
  async function exportar() {
    setExportando(true)
    try {
      const todos: Eletronico[] = []
      for (let pg = 1; ; pg++) {
        const r = await getEletronicosPaginated({
          q: searchDebounced || undefined,
          campo: campoBusca,
          centro_custo: filtroCC.length ? filtroCC : undefined,
          status: filtroStatus.length ? filtroStatus : undefined,
          tipo: filtroTipo.length ? filtroTipo : undefined,
          localizacao: filtroLocal.length ? filtroLocal : undefined,
          ordem: ordem.col,
          desc: ordem.desc,
          page: pg,
          page_size: 1000,
        })
        todos.push(...r.eletronicos)
        if (pg >= r.pages) break
      }
      const cab = ['Patrimônio', 'Nome', 'Tipo', 'Marca', 'Modelo', 'Nº de série', 'Situação', 'CC', 'Localização', 'IP', 'Responsável']
      const cel = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
      const linhas = todos.map((e) =>
        [e.numero_patrimonio, e.nome, e.tipo, e.marca, e.modelo, e.numero_serie, ROTULO_STATUS[e.status],
          e.centro_custo, e.localizacao, e.ip, responsavelDe(e)].map(cel).join(';'),
      )
      const blob = new Blob(['\ufeff' + [cab.map(cel).join(';'), ...linhas].join('\r\n')], {
        type: 'text/csv;charset=utf-8',
      })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `equipamentos-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      setTimeout(() => URL.revokeObjectURL(a.href), 10000)
      toast.success(`${todos.length} equipamento(s) exportado(s).`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao exportar.')
    } finally {
      setExportando(false)
    }
  }

  async function handleCriarLocalizacao(e: React.FormEvent) {
    e.preventDefault()
    const nome = novaLocNome.trim()
    if (!nome) return
    try {
      const nova = await createLocalizacao({ nome })
      setLocalizacoes((prev) => [...prev, nova])
      setForm((f) => ({ ...f, localizacao: nova.nome }))
      setNovaLocNome('')
      setNovaLocOpen(false)
      toast.success(`Localização "${nova.nome}" criada.`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  async function handleCriarMarca(e: React.FormEvent) {
    e.preventDefault()
    const nome = novaMarcaNome.trim()
    if (!nome) return
    try {
      const nova = await createMarca({ nome })
      setMarcas((prev) => [...prev, nova])
      // seleciona a nova marca e limpa o modelo (muda de contexto)
      setForm((f) => ({ ...f, marca: nova.nome, modelo: '' }))
      setNovaMarcaNome('')
      setNovaMarcaOpen(false)
      toast.success(`Marca "${nova.nome}" criada.`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  async function handleCriarModelo(e: React.FormEvent) {
    e.preventDefault()
    const nome = novoModeloNome.trim()
    if (!nome) return
    const marcaSel = marcas.find((m) => m.nome === form.marca)
    if (!marcaSel) {
      toast.error('Selecione uma marca antes de criar o modelo.')
      return
    }
    try {
      const novo = await createModelo({
        nome,
        marca_id: marcaSel.id,
        descricao: novoModeloDescricao.trim() || null,
      })
      setModelos((prev) => [...prev, novo])
      // seleciona o modelo e traz a descrição cadastrada, só se o
      // campo ainda estiver vazio (não sobrescreve o que já foi digitado)
      setForm((f) => ({
        ...f,
        modelo: novo.nome,
        descricao:
          f.descricao.trim() === '' && novo.descricao
            ? novo.descricao
            : f.descricao,
      }))
      setNovoModeloNome('')
      setNovoModeloDescricao('')
      setNovoModeloOpen(false)
      toast.success(`Modelo "${novo.nome}" criado.`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  function reloadAssocs() {
    getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
  }

  const minhasOcupacoes = new Map(
    assocsCC.filter((a) => a.user_id === user?.id).map((a) => [a.centro_custo, a.ocupacao]),
  )

  function podeAssociar(eq: Eletronico): boolean {
    if (user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI') return true
    const o = minhasOcupacoes.get(eq.centro_custo)
    return o === 'Gestor' || o === 'Subgestor'
  }

  function responsavelDe(eq: Eletronico): string {
    const a = assocsEl.find((x) => x.eletronico_id === eq.id)
    if (!a) return '—'
    const u = allUsers.find((x) => x.id === a.user_id)
    return u?.nome ?? `#${a.user_id}`
  }

  async function abrirAssociar(eq: Eletronico) {
    setAssociarEq(eq)
    setAssociarUserId('')
  }

  async function confirmarAssociar(e: React.FormEvent) {
    e.preventDefault()
    if (!associarEq || !associarUserId) return
    try {
      // Remove associações anteriores deste eletrônico
      const existing = assocsEl.filter((a) => a.eletronico_id === associarEq.id)
      for (const a of existing) {
        await deleteAssociacaoEletronico(a.user_id, associarEq.id)
      }
      await createAssociacaoEletronico({
        user_id: parseInt(associarUserId),
        eletronico_id: associarEq.id,
      })
      toast.success('Responsável definido.')
      setAssociarEq(null)
      reloadAssocs()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao associar.')
    }
  }

  async function desassociar(eq: Eletronico) {
    const a = assocsEl.find((x) => x.eletronico_id === eq.id)
    if (!a) return
    if (!confirm(`Remover ${responsavelDe(eq)} como responsável de "${eq.nome}"?`)) return
    try {
      await deleteAssociacaoEletronico(a.user_id, eq.id)
      toast.success('Responsável removido.')
      reloadAssocs()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  const reload = () => {
    setPage((p) => p)
    // força refetch:
    getEletronicosPaginated({
      q: searchDebounced || undefined,
      campo: campoBusca,
      centro_custo: filtroCC.length ? filtroCC : undefined,
      status: filtroStatus.length ? filtroStatus : undefined,
      tipo: filtroTipo.length ? filtroTipo : undefined,
      localizacao: filtroLocal.length ? filtroLocal : undefined,
      ordem: ordem.col,
      desc: ordem.desc,
      page,
      page_size: pageSize,
    })
      .then((res) => {
        setEletronicos(res.eletronicos)
        setTotal(res.total)
        setPages(res.pages)
      })
      .catch(() => {})
  }

  const canWrite = user?.tipo !== undefined

  function abrirNovo() {
    setEditando(null)
    setForm(EMPTY)
    setSemIp(false)
    setNovoResponsavelId(user ? String(user.id) : '')
    setOpen(true)
  }

  function abrirEditar(e: Eletronico) {
    setEditando(e)
    setForm({
      numero_serie: e.numero_serie,
      numero_patrimonio: e.numero_patrimonio,
      nome: e.nome,
      marca: e.marca ?? '',
      tipo: e.tipo,
      modelo: e.modelo ?? '',
      status: e.status,
      ip: e.ip ?? '',
      localizacao: e.localizacao ?? '',
      descricao: e.descricao ?? '',
      centro_custo: e.centro_custo,
    })
    setSemIp(!e.ip)
    setOpen(true)
  }

  async function handleSave(ev: React.FormEvent) {
    ev.preventDefault()
    // Quando "Sem IP" está marcado, força ip vazio (backend trata como nulo)
    const payload = { ...form, ip: semIp ? '' : form.ip }
    try {
      if (editando) {
        await updateEletronico(editando.id, payload as Parameters<typeof updateEletronico>[1])
        toast.success('Atualizado!')
      } else {
        const novo = await createEletronico(payload as Parameters<typeof createEletronico>[0])

        // Define o responsável (se diferente do auto-associado pelo backend)
        const isFuncionario =
          !(user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI') &&
          minhasOcupacoes.get(form.centro_custo) === 'Funcionario'
        // Backend auto-associa o criador se Funcionario. Para os demais,
        // criamos a associação aqui se o usuário escolheu alguém.
        if (!isFuncionario && novoResponsavelId) {
          try {
            await createAssociacaoEletronico({
              user_id: parseInt(novoResponsavelId),
              eletronico_id: novo.id,
            })
          } catch {
            // não bloqueia a criação do eletrônico se associação falhar
          }
        }
        toast.success('Criado!')
        reloadAssocs()
      }
      setOpen(false)
      reload()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteEletronico(id)
      toast.success('Removido!')
      reload()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao remover.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Equipamentos</h1>
          <p className="text-sm text-muted-foreground">
            Tudo o que está no inventário: interno, cedido ou em manutenção.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(user?.tipo === 'Admin' ||
            user?.tipo === 'Tecnico_TI' ||
            user?.tipo === 'Gestor' ||
            user?.tipo === 'Subgestor') && (
            <Link href="/equipamentos/ceder">
              <Button size="sm" variant="outline">
                <FileText className="mr-1 h-4 w-4" /> Ceder
              </Button>
            </Link>
          )}
          <Button size="sm" variant="outline" onClick={exportar} disabled={exportando}>
            <Download className="mr-1 h-4 w-4" /> {exportando ? 'Exportando…' : 'Exportar'}
          </Button>
          {canWrite && (
            <Button size="sm" onClick={abrirNovo}>
              <Plus className="mr-1 h-4 w-4" /> Novo
            </Button>
          )}
        </div>
      </div>

      <div className="rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-2 border-b p-3">
        <Input
          className="h-9 min-w-56 flex-1 sm:max-w-sm"
          placeholder={
            campoBusca === 'sem_responsavel'
              ? 'Filtro ativo — busca desabilitada'
              : campoBusca === 'todos'
                ? 'Patrimônio, série, nome, modelo, IP, localização…'
                : `Buscar por ${CAMPOS_BUSCA[campoBusca].toLowerCase()}…`
          }
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={campoBusca === 'sem_responsavel'}
        />
        <Select
          value={campoBusca}
          onValueChange={(v) => setCampoBusca(v as CampoBuscaEletronico)}
        >
          <SelectTrigger className="h-9 w-auto min-w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(CAMPOS_BUSCA) as CampoBuscaEletronico[]).map(
              (k) => (
                <SelectItem key={k} value={k}>
                  {CAMPOS_BUSCA[k]}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>
        <FiltroMulti
          titulo="Tipo"
          opcoes={tiposCatalogo.map((t) => ({ value: t.nome, label: t.nome }))}
          valor={filtroTipo}
          onChange={setFiltroTipo}
        />
        <FiltroMulti
          titulo="Situação"
          opcoes={(['Interno', 'Externo', 'Em Manutenção'] as const).map((s) => ({
            value: s,
            label: ROTULO_STATUS[s],
          }))}
          valor={filtroStatus}
          onChange={setFiltroStatus}
        />
        <FiltroMulti
          titulo="Localização"
          opcoes={localizacoes.map((l) => ({ value: l.nome, label: l.nome }))}
          valor={filtroLocal}
          onChange={setFiltroLocal}
        />
        <FiltroMulti
          titulo="Centro de custo"
          opcoes={contratos.map((c) => ({
            value: c.centro_custo,
            label: `${c.centro_custo} · ${c.descricao}`,
          }))}
          valor={filtroCC}
          onChange={setFiltroCC}
        />
        {filtrosAtivos && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setSearch('')
              setFiltroCC([])
              setFiltroStatus([])
              setFiltroTipo([])
              setFiltroLocal([])
            }}
          >
            Limpar
          </Button>
        )}
        <div className="ml-auto flex rounded-lg bg-muted p-0.5" role="group" aria-label="Visualização">
          {(
            [
              ['tabela', List, 'Tabela'],
              ['cartoes', LayoutGrid, 'Cartões'],
            ] as const
          ).map(([m, Icone, rotulo]) => (
            <button
              key={m}
              type="button"
              title={rotulo}
              aria-pressed={modo === m}
              onClick={() => setModo(m)}
              className={
                'rounded-md px-2 py-1 text-muted-foreground aria-pressed:bg-card aria-pressed:text-foreground aria-pressed:shadow-xs'
              }
            >
              <Icone className="h-4 w-4" />
            </button>
          ))}
        </div>
      </div>

      {modo === 'cartoes' ? (
        <div className="grid gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {eletronicos.length === 0 && (
            <p className="col-span-full py-8 text-center text-sm text-muted-foreground">
              {loading ? 'Carregando…' : 'Nenhum equipamento com esses filtros.'}
            </p>
          )}
          {eletronicos.map((e) => (
            <div
              key={e.id}
              role="button"
              tabIndex={0}
              onClick={() => abrirDetalhe(e.id)}
              onKeyDown={(ev) => ev.key === 'Enter' && abrirDetalhe(e.id)}
              className={
                'flex cursor-pointer flex-col gap-2 rounded-xl border bg-card p-3 text-left transition-colors hover:border-ring ' +
                (marcados.has(e.id) ? 'border-primary bg-primary/5' : '')
              }
            >
              <div className="flex items-start justify-between gap-2">
                <IconeTipo tipo={e.tipo} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{e.nome}</p>
                  <p className="font-mono text-xs text-muted-foreground">{e.numero_patrimonio}</p>
                </div>
                <input
                  type="checkbox"
                  className="mt-1 accent-primary"
                  checked={marcados.has(e.id)}
                  onClick={(ev) => ev.stopPropagation()}
                  onChange={() => alternarMarcado(e)}
                  aria-label={`Marcar ${e.numero_patrimonio}`}
                />
              </div>
              <StatusEquipamento status={e.status} />
              <dl className="grid grid-cols-[auto_1fr] gap-x-2 text-xs">
                <dt className="text-muted-foreground">Modelo</dt>
                <dd className="truncate">{[e.marca, e.modelo].filter(Boolean).join(' ') || '—'}</dd>
                <dt className="text-muted-foreground">CC</dt>
                <dd>{e.centro_custo}</dd>
                <dt className="text-muted-foreground">Local</dt>
                <dd className="truncate">{e.localizacao || '—'}</dd>
                <dt className="text-muted-foreground">Com</dt>
                <dd className="truncate">{responsavelDe(e)}</dd>
              </dl>
              {e.descricao && <p className="truncate text-xs text-muted-foreground">{e.descricao}</p>}
            </div>
          ))}
        </div>
      ) : (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-xs text-muted-foreground">
              <th className="w-10 px-3 py-2">
                <input
                  type="checkbox"
                  className="accent-primary"
                  checked={paginaMarcada}
                  onChange={marcarPagina}
                  aria-label="Marcar a página"
                />
              </th>
              <Ordenavel col="numero_patrimonio" ordem={ordem} onOrdenar={ordenarPor}>Patrimônio</Ordenavel>
              <Ordenavel col="nome" ordem={ordem} onOrdenar={ordenarPor}>Equipamento</Ordenavel>
              <Ordenavel col="status" ordem={ordem} onOrdenar={ordenarPor}>Situação</Ordenavel>
              <Ordenavel col="centro_custo" ordem={ordem} onOrdenar={ordenarPor}>CC</Ordenavel>
              <Ordenavel col="localizacao" ordem={ordem} onOrdenar={ordenarPor}>Localização</Ordenavel>
              <th className="px-3 py-2 text-left font-medium">Responsável</th>
              {canWrite && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody>
            {loading && eletronicos.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : eletronicos.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                  Nenhum equipamento com esses filtros.
                </td>
              </tr>
            ) : (
              eletronicos.map((e) => {
                const temResp = assocsEl.some((a) => a.eletronico_id === e.id)
                return (
                  <tr
                    key={e.id}
                    onClick={() => abrirDetalhe(e.id)}
                    className={
                      'cursor-pointer border-b last:border-0 hover:bg-muted/40 ' +
                      (marcados.has(e.id) ? 'bg-primary/5' : '')
                    }
                  >
                    <td className="px-3 py-2" onClick={(ev) => ev.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="accent-primary"
                        checked={marcados.has(e.id)}
                        onChange={() => alternarMarcado(e)}
                        aria-label={`Marcar ${e.numero_patrimonio}`}
                      />
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums">{e.numero_patrimonio}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2.5">
                      <IconeTipo tipo={e.tipo} />
                      <div>
                      <p className="font-medium">{e.nome}</p>
                      <p className="text-xs text-muted-foreground">
                        {e.tipo}
                        {(e.marca || e.modelo) && ` · ${[e.marca, e.modelo].filter(Boolean).join(' ')}`}
                      </p>
                      </div>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <StatusEquipamento status={e.status} />
                    </td>
                    <td className="px-3 py-2 font-mono">{e.centro_custo}</td>
                    <td className="max-w-44 truncate px-3 py-2 text-muted-foreground">{e.localizacao || '—'}</td>
                    <td className="px-3 py-2" onClick={(ev) => ev.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        <span className="text-sm">{responsavelDe(e)}</span>
                        {temResp && podeAssociar(e) && (
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-6 w-6 text-muted-foreground"
                            onClick={() => desassociar(e)}
                            title="Remover responsável"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </td>
                    {canWrite && (
                      <td className="px-3 py-2" onClick={(ev) => ev.stopPropagation()}>
                        <div className="flex justify-end gap-1">
                          {podeAssociar(e) && (
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7"
                              onClick={() => abrirAssociar(e)}
                              title="Definir responsável"
                            >
                              <UsersIcon className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => abrirEditar(e)} title="Editar">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => setExcluir(e)} title="Excluir">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      )}

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-2 text-sm">
          <span className="text-muted-foreground">
            Mostrando{' '}
            <strong>
              {(page - 1) * pageSize + 1}–
              {Math.min(page * pageSize, total)}
            </strong>{' '}
            de <strong>{total}</strong>
          </span>
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-xs text-muted-foreground">
              Página {page} de {pages}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= pages || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Itens/pág.:</span>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="rounded border bg-background px-1.5 py-1 text-xs"
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      </div>

      {marcados.size > 0 && (
        <div className="sticky bottom-3 z-20 mx-auto flex w-fit max-w-full flex-wrap items-center gap-2 rounded-xl bg-foreground px-4 py-2 text-sm text-background shadow-lg">
          <b>{marcados.size} marcado(s)</b>
          <span className="opacity-70">{internosMarcados.length} disponível(is) para ceder</span>
          {podeCeder && (
            <Button size="sm" disabled={!internosMarcados.length || emLote} onClick={cederMarcados}>
              <ArrowRight className="h-4 w-4" /> Ceder ({internosMarcados.length})
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="text-background hover:bg-background/15 hover:text-background"
            disabled={emLote}
            onClick={() => {
              setLocalLote('')
              setLocalLoteOpen(true)
            }}
          >
            <MapPin className="h-4 w-4" /> Mudar localização
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-background hover:bg-background/15 hover:text-background"
            disabled={!internosMarcados.length || emLote}
            onClick={() =>
              aplicarEmLote(internosMarcados, (p) => ({ ...p, status: 'Em Manutenção' }), 'foram para manutenção')
            }
          >
            <Wrench className="h-4 w-4" /> Manutenção ({internosMarcados.length})
          </Button>
          {emManutencaoMarcados.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              className="text-background hover:bg-background/15 hover:text-background"
              disabled={emLote}
              onClick={() =>
                aplicarEmLote(emManutencaoMarcados, (p) => ({ ...p, status: 'Interno' }), 'voltaram da manutenção')
              }
            >
              <Undo2 className="h-4 w-4" /> Voltou da manutenção ({emManutencaoMarcados.length})
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="text-background hover:bg-background/15 hover:text-background"
            onClick={() => setMarcados(new Map())}
          >
            <X className="h-4 w-4" /> Limpar
          </Button>
        </div>
      )}

      <Dialog open={excluir !== null} onOpenChange={(o) => !o && setExcluir(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir {excluir?.nome}?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            O equipamento de patrimônio <strong className="text-foreground">{excluir?.numero_patrimonio}</strong> sai do
            inventário. A exclusão fica registrada na auditoria.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setExcluir(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (excluir) handleDelete(excluir.id)
                if (excluir && detalheId === excluir.id) abrirDetalhe(null)
                setExcluir(null)
              }}
            >
              <Trash2 className="h-4 w-4" /> Excluir
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={localLoteOpen} onOpenChange={setLocalLoteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mudar a localização de {marcados.size} equipamento(s)</DialogTitle>
          </DialogHeader>
          <div className="space-y-1">
            <Label>Nova localização</Label>
            <SearchableSelect
              value={localLote}
              onChange={setLocalLote}
              options={localizacoes.map((l) => ({ value: l.nome, label: l.nome }))}
              placeholder="Escolha…"
            />
          </div>
          <Button
            className="w-full"
            disabled={!localLote || emLote}
            onClick={() => {
              setLocalLoteOpen(false)
              aplicarEmLote(listaMarcada, (p) => ({ ...p, localizacao: localLote }), 'mudaram de localização')
            }}
          >
            Mover
          </Button>
        </DialogContent>
      </Dialog>

      <Sheet open={detalhe !== null} onOpenChange={(o) => !o && abrirDetalhe(null)}>
        <SheetContent className="w-full gap-0 sm:max-w-md">
          {detalhe && (
            <>
              <SheetHeader className="flex-row items-center gap-3 border-b">
                <IconeTipo tipo={detalhe.tipo} className="size-10" />
                <div className="space-y-0.5">
                <SheetTitle>{detalhe.nome}</SheetTitle>
                <SheetDescription className="font-mono">Patrimônio {detalhe.numero_patrimonio}</SheetDescription>
                </div>
              </SheetHeader>
              <div className="flex-1 space-y-5 overflow-y-auto p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusEquipamento status={detalhe.status} />
                  <span className="text-sm text-muted-foreground">com {responsavelDe(detalhe)}</span>
                </div>
                <dl className="grid grid-cols-[8.5rem_1fr] gap-x-3 gap-y-2 text-sm">
                  <dt className="text-muted-foreground">Tipo</dt>
                  <dd>{detalhe.tipo}</dd>
                  <dt className="text-muted-foreground">Marca e modelo</dt>
                  <dd>{[detalhe.marca, detalhe.modelo].filter(Boolean).join(' ') || '—'}</dd>
                  <dt className="text-muted-foreground">Nº de série</dt>
                  <dd className="font-mono">{detalhe.numero_serie}</dd>
                  <dt className="text-muted-foreground">Centro de custo</dt>
                  <dd>
                    {detalhe.centro_custo}
                    {contratos.find((c) => c.centro_custo === detalhe.centro_custo)?.descricao &&
                      ` · ${contratos.find((c) => c.centro_custo === detalhe.centro_custo)?.descricao}`}
                  </dd>
                  <dt className="text-muted-foreground">Gestor do CC</dt>
                  <dd>{contratos.find((c) => c.centro_custo === detalhe.centro_custo)?.gestor_nome || '—'}</dd>
                  <dt className="text-muted-foreground">Localização</dt>
                  <dd>{detalhe.localizacao || '—'}</dd>
                  {detalhe.ip && (
                    <>
                      <dt className="text-muted-foreground">IP</dt>
                      <dd className="font-mono">{detalhe.ip}</dd>
                    </>
                  )}
                  <dt className="text-muted-foreground">Descrição</dt>
                  <dd className="whitespace-pre-line">
                    {detalhe.descricao || <span className="text-muted-foreground">sem descrição</span>}
                  </dd>
                </dl>
                {detalhe.status === 'Externo' &&
                  !historico.some((c) => c.eletronicos.some((x) => x.id === detalhe.id && x.devolvido_em === null)) && (
                    <div className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm">
                      <p className="font-medium text-warn">Cedido sem cessão registrada</p>
                      <p className="mt-0.5 text-muted-foreground">
                        Está marcado como cedido, mas não há cessão aberta, por isso não tem termo. Registre a
                        cessão para gerar o documento.
                      </p>
                      <Button size="sm" className="mt-2" asChild>
                        <Link href={`/equipamentos/ceder?ids=${detalhe.id}`}>
                          <FileText className="h-4 w-4" /> Registrar cessão
                        </Link>
                      </Button>
                    </div>
                  )}
                <div>
                  <p className="mb-2 text-sm font-medium">Histórico de cessões</p>
                  {historico.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nunca foi cedido.</p>
                  ) : (
                    <ul className="space-y-3 border-l pl-4 text-sm">
                      {historico.map((c) => {
                        const item = c.eletronicos.find((x) => x.id === detalhe.id)
                        return (
                          <li key={c.id} className="relative before:absolute before:top-1.5 before:-left-[21px] before:size-2.5 before:rounded-full before:bg-primary">
                            <Link href={`/cessoes?id=${c.id}`} className="font-medium hover:underline">
                              Cessão #{c.id} · {c.responsavel}
                            </Link>
                            <p className="text-xs text-muted-foreground">
                              cedido em {formatDate(c.cedido_em).slice(0, 10)} · CC {c.centro_custo_destino}
                              {item?.devolvido_em
                                ? ` · devolvido em ${formatDate(item.devolvido_em).slice(0, 10)}`
                                : ' · ainda com o responsável'}
                            </p>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              <Link
                                href={`/cessoes/${c.id}/termo`}
                                className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs hover:bg-muted"
                              >
                                <FileText className="h-3 w-3" /> Termo de cessão
                              </Link>
                              {c.devolucoes
                                .filter((d) => d.eletronicos.some((x) => x.id === detalhe.id))
                                .map((d) => (
                                  <Link
                                    key={d.lote}
                                    href={`/cessoes/${c.id}/recebimento/${d.lote}`}
                                    className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs hover:bg-muted"
                                  >
                                    <FileText className="h-3 w-3" /> Recebimento #{d.lote}
                                  </Link>
                                ))}
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap justify-between gap-2 border-t p-4">
                {canWrite && (
                  <Button
                    variant="outline"
                    className="text-destructive"
                    onClick={() => setExcluir(detalhe)}
                  >
                    <Trash2 className="h-4 w-4" /> Excluir
                  </Button>
                )}
                <div className="ml-auto flex gap-2">
                  {podeCeder && detalhe.status === 'Interno' && (
                    <Button variant="outline" asChild>
                      <Link href={`/equipamentos/ceder?ids=${detalhe.id}`}>
                        <ArrowRight className="h-4 w-4" /> Ceder
                      </Link>
                    </Button>
                  )}
                  {canWrite && (
                    <Button
                      onClick={() => {
                        abrirEditar(detalhe)
                        abrirDetalhe(null)
                      }}
                    >
                      <Pencil className="h-4 w-4" /> Editar
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editando ? 'Editar equipamento' : 'Novo equipamento'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSave} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(
              [
                ['nome', 'Nome', true],
                ['numero_serie', 'Nº Série', true],
                ['numero_patrimonio', 'Nº Patrimônio', true],
              ] as [keyof typeof EMPTY, string, boolean][]
            ).map(([field, label, required]) => (
              <div key={field} className="space-y-1">
                <Label>
                  {label} {required && <RequiredMark />}
                </Label>
                <Input
                  value={form[field]}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      // Nº Série sempre em maiúsculas, independente do CapsLock
                      [field]:
                        field === 'numero_serie'
                          ? e.target.value.toUpperCase()
                          : e.target.value,
                    }))
                  }
                  required={required}
                />
              </div>
            ))}
            <div className="space-y-1">
              <Label>Marca</Label>
              <div className="flex gap-1">
                <div className="flex-1">
                  <SearchableSelect
                    value={form.marca}
                    onChange={(v) =>
                      // troca de marca: limpa o modelo (pertence à marca)
                      setForm((f) => ({ ...f, marca: v, modelo: '' }))
                    }
                    options={marcas.map((m) => ({
                      value: m.nome,
                      label: m.nome,
                    }))}
                    placeholder="Selecione…"
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => setNovaMarcaOpen(true)}
                  title="Criar nova marca"
                  className="shrink-0"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-1">
              <Label>Modelo</Label>
              <div className="flex gap-1">
                <div className="flex-1">
                  <SearchableSelect
                    value={form.modelo}
                    onChange={(v) => {
                      // Ao escolher o modelo, traz a descrição dele —
                      // mas só se o campo ainda estiver vazio (não
                      // sobrescreve peculiaridades já digitadas).
                      const mod = modelos.find(
                        (m) => m.nome === v && m.marca_nome === form.marca,
                      )
                      setForm((f) => ({
                        ...f,
                        modelo: v,
                        descricao:
                          f.descricao.trim() === '' && mod?.descricao
                            ? mod.descricao
                            : f.descricao,
                      }))
                    }}
                    options={modelos
                      .filter((m) => m.marca_nome === form.marca)
                      .map((m) => ({
                        value: m.nome,
                        label: m.nome,
                        searchKey: `${m.nome} ${m.descricao ?? ''}`,
                      }))}
                    placeholder={
                      form.marca
                        ? 'Selecione…'
                        : 'Escolha a marca primeiro'
                    }
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    if (!form.marca) {
                      toast.error('Escolha a marca primeiro.')
                      return
                    }
                    setNovoModeloNome('')
                    setNovoModeloDescricao('')
                    setNovoModeloOpen(true)
                  }}
                  title="Criar novo modelo"
                  className="shrink-0"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-1">
              <Label>IP</Label>
              <Input
                value={semIp ? '' : form.ip}
                onChange={(e) => setForm((f) => ({ ...f, ip: e.target.value }))}
                disabled={semIp}
                placeholder={semIp ? 'Sem IP' : 'ex.: 10.0.0.1'}
                className={semIp ? 'bg-muted' : ''}
              />
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={semIp}
                  onChange={(e) => setSemIp(e.target.checked)}
                />
                Equipamento sem IP
              </label>
            </div>
            <div className="space-y-1">
              <Label>Localização</Label>
              <div className="flex gap-1">
                <div className="flex-1">
                  <SearchableSelect
                    value={form.localizacao}
                    onChange={(v) => setForm((f) => ({ ...f, localizacao: v }))}
                    options={localizacoes.map((l) => ({
                      value: l.nome,
                      label: l.nome,
                      searchKey: `${l.nome} ${l.descricao ?? ''}`,
                    }))}
                    placeholder="Selecione…"
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => setNovaLocOpen(true)}
                  title="Criar nova localização"
                  className="shrink-0"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-1">
              <Label>Tipo <RequiredMark /></Label>
              <Select value={form.tipo} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v }))}>
                <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                <SelectContent>
                  {tiposCatalogo.map((t) => (
                    <SelectItem key={t.id} value={t.nome}>{t.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Status <RequiredMark /></Label>
              <Select value={form.status} onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Interno">Interno</SelectItem>
                  <SelectItem value="Externo">Externo</SelectItem>
                  <SelectItem value="Em Manutenção">Em Manutenção</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Centro de Custo <RequiredMark /></Label>
              <SearchableSelect
                value={form.centro_custo}
                onChange={(v) => {
                  setForm((f) => ({ ...f, centro_custo: v }))
                  // Se o usuário é Funcionario no novo CC, trava o responsável nele
                  const isAdminTI =
                    user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'
                  if (!isAdminTI && minhasOcupacoes.get(v) === 'Funcionario') {
                    setNovoResponsavelId(user ? String(user.id) : '')
                  }
                }}
                options={contratos.map((c) => ({ value: c.centro_custo, label: c.centro_custo }))}
              />
            </div>
            {!editando && (
              <div className="space-y-1">
                <Label>Responsável</Label>
                {(() => {
                  const isAdminTI =
                    user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'
                  const ehFuncNoCC =
                    !isAdminTI &&
                    minhasOcupacoes.get(form.centro_custo) === 'Funcionario'
                  if (ehFuncNoCC) {
                    return (
                      <Input
                        value={user?.nome ?? ''}
                        disabled
                        className="bg-muted"
                      />
                    )
                  }
                  const userIdsNoCC = assocsCC
                    .filter((a) => a.centro_custo === form.centro_custo)
                    .map((a) => a.user_id)
                  const opts = allUsers
                    .filter((u) => userIdsNoCC.includes(u.id))
                    .map((u) => ({
                      value: String(u.id),
                      label: u.nome,
                      searchKey: `${u.nome} ${u.email}`,
                    }))
                  return (
                    <SearchableSelect
                      value={novoResponsavelId}
                      onChange={setNovoResponsavelId}
                      options={opts}
                      placeholder={
                        form.centro_custo
                          ? 'Selecione um membro do CC'
                          : 'Escolha o CC primeiro'
                      }
                    />
                  )
                })()}
              </div>
            )}
            <div className="space-y-1 sm:col-span-2">
              <div className="flex items-center justify-between gap-2">
                <Label>Descrição</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    const mod = modelos.find(
                      (m) =>
                        m.nome === form.modelo &&
                        m.marca_nome === form.marca,
                    )
                    if (!form.modelo || !mod) {
                      toast.error('Selecione um modelo primeiro.')
                      return
                    }
                    if (!mod.descricao || !mod.descricao.trim()) {
                      toast.error(
                        `O modelo "${mod.nome}" não tem descrição cadastrada.`,
                      )
                      return
                    }
                    if (
                      form.descricao.trim() &&
                      !confirm(
                        'Isso vai SOBRESCREVER toda a descrição atual do ' +
                          'equipamento pela descrição do modelo. Continuar?',
                      )
                    ) {
                      return
                    }
                    setForm((f) => ({ ...f, descricao: mod.descricao ?? '' }))
                    toast.success('Descrição do modelo carregada.')
                  }}
                >
                  <FileText className="mr-1 h-3 w-3" />
                  Carregar descrição do modelo
                </Button>
              </div>
              <Textarea
                value={form.descricao}
                onChange={(e) =>
                  setForm((f) => ({ ...f, descricao: e.target.value }))
                }
                rows={3}
              />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" className="w-full">{editando ? 'Salvar' : 'Criar'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={associarEq !== null} onOpenChange={(o) => !o && setAssociarEq(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Definir responsável: {associarEq?.nome}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={confirmarAssociar} className="space-y-3">
            <div className="space-y-1">
              <Label>Usuário responsável</Label>
              <SearchableSelect
                value={associarUserId}
                onChange={setAssociarUserId}
                options={(() => {
                  if (!associarEq) return []
                  // Apenas usuários associados ao CC do eletrônico
                  const userIdsNoCC = assocsCC
                    .filter((a) => a.centro_custo === associarEq.centro_custo)
                    .map((a) => a.user_id)
                  return allUsers
                    .filter((u) => userIdsNoCC.includes(u.id))
                    .map((u) => ({
                      value: String(u.id),
                      label: u.nome,
                      searchKey: `${u.nome} ${u.email}`,
                    }))
                })()}
                placeholder="Selecione um usuário do CC"
              />
              <p className="text-xs text-muted-foreground">
                Apenas usuários membros do CC do equipamento.
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={!associarUserId}>
              Definir como responsável
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={novaLocOpen} onOpenChange={setNovaLocOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova localização</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCriarLocalizacao} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={novaLocNome}
                onChange={(e) => setNovaLocNome(e.target.value)}
                placeholder="Ex.: Sala TI, Almoxarifado, …"
                required
                autoFocus
              />
            </div>
            <Button type="submit" className="w-full">
              Criar e selecionar
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={novaMarcaOpen} onOpenChange={setNovaMarcaOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova marca</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCriarMarca} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={novaMarcaNome}
                onChange={(e) => setNovaMarcaNome(e.target.value)}
                placeholder="Ex.: Dell, HP, Samsung, …"
                required
                autoFocus
              />
            </div>
            <Button type="submit" className="w-full">
              Criar e selecionar
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={novoModeloOpen} onOpenChange={setNovoModeloOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Novo modelo {form.marca && `· ${form.marca}`}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCriarModelo} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={novoModeloNome}
                onChange={(e) => setNovoModeloNome(e.target.value)}
                placeholder="Ex.: Latitude 5420, EliteBook 840, …"
                required
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Será associado à marca <strong>{form.marca}</strong>.
              </p>
            </div>
            <div className="space-y-1">
              <Label>Descrição (opcional)</Label>
              <Textarea
                value={novoModeloDescricao}
                onChange={(e) => setNovoModeloDescricao(e.target.value)}
                rows={3}
                placeholder="Descrição do modelo (preenche a descrição do equipamento)"
              />
            </div>
            <Button type="submit" className="w-full">
              Criar e selecionar
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function EquipamentosPage() {
  return (
    <Suspense fallback={null}>
      <EquipamentosConteudo />
    </Suspense>
  )
}
