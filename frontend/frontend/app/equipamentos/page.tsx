'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getEletronicosPaginated,
  createEletronico,
  updateEletronico,
  deleteEletronico,
  type CampoBuscaEletronico,
} from '@/lib/api/eletronicos'
import { getContratos } from '@/lib/api/contratos'
import {
  getAssociacoesEletronico,
  createAssociacaoEletronico,
  deleteAssociacaoEletronico,
  getAssociacoesContrato,
} from '@/lib/api/associacoes'
import { getUsers } from '@/lib/api/users'
import type {
  Eletronico,
  Contrato,
  AssociacaoUserEletronico,
  AssociacaoUserContrato,
  User,
} from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
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
} from 'lucide-react'
import Link from 'next/link'
import { SearchableSelect } from '@/components/app/searchable-select'

const STATUS_COLORS: Record<string, string> = {
  Interno: 'default',
  Externo: 'secondary',
  'Em Manutenção': 'destructive',
}

const TIPOS_EQUIPAMENTO = [
  'Computador',
  'Notbook',
  'Monitor',
  'Impressora',
  'Scanner',
]

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

const PAGE_SIZE = 25

export default function EquipamentosPage() {
  const { user } = useAuth()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [search, setSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [campoBusca, setCampoBusca] =
    useState<CampoBuscaEletronico>('todos')
  const [filtroCC, setFiltroCC] = useState('todos')
  const [filtroStatus, setFiltroStatus] = useState('todos')
  const [filtroTipo, setFiltroTipo] = useState('todos')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<Eletronico | null>(null)
  const [form, setForm] = useState(EMPTY)
  const [novoResponsavelId, setNovoResponsavelId] = useState('')
  const [associarEq, setAssociarEq] = useState<Eletronico | null>(null)
  const [associarUserId, setAssociarUserId] = useState('')
  const [assocsEl, setAssocsEl] = useState<AssociacaoUserEletronico[]>([])
  const [assocsCC, setAssocsCC] = useState<AssociacaoUserContrato[]>([])
  const [allUsers, setAllUsers] = useState<User[]>([])

  // Debounce do search
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Reseta para página 1 quando filtros mudam
  useEffect(() => {
    setPage(1)
  }, [searchDebounced, campoBusca, filtroCC, filtroStatus, filtroTipo])

  // Carrega dados quando filtros ou página mudam
  useEffect(() => {
    setLoading(true)
    getEletronicosPaginated({
      q: searchDebounced || undefined,
      campo: campoBusca,
      centro_custo: filtroCC !== 'todos' ? [filtroCC] : undefined,
      status: filtroStatus !== 'todos' ? [filtroStatus] : undefined,
      tipo: filtroTipo !== 'todos' ? [filtroTipo] : undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => {
        setEletronicos(res.eletronicos)
        setTotal(res.total)
        setPages(res.pages)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchDebounced, campoBusca, filtroCC, filtroStatus, filtroTipo, page])

  useEffect(() => {
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesEletronico().then(setAssocsEl).catch(() => {})
    getAssociacoesContrato().then(setAssocsCC).catch(() => {})
    getUsers().then(setAllUsers).catch(() => {})
  }, [])

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
      centro_custo: filtroCC !== 'todos' ? [filtroCC] : undefined,
      status: filtroStatus !== 'todos' ? [filtroStatus] : undefined,
      tipo: filtroTipo !== 'todos' ? [filtroTipo] : undefined,
      page,
      page_size: PAGE_SIZE,
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
    setOpen(true)
  }

  async function handleSave(ev: React.FormEvent) {
    ev.preventDefault()
    try {
      if (editando) {
        await updateEletronico(editando.id, form as Parameters<typeof updateEletronico>[1])
        toast.success('Atualizado!')
      } else {
        const novo = await createEletronico(form as Parameters<typeof createEletronico>[0])

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Equipamentos</h1>
        <div className="flex gap-2">
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
          {canWrite && (
            <Button size="sm" onClick={abrirNovo}>
              <Plus className="mr-1 h-4 w-4" /> Novo
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <Input
          placeholder={
            campoBusca === 'sem_responsavel'
              ? 'Filtro ativo — busca desabilitada'
              : campoBusca === 'todos'
                ? 'Buscar (nome, série, patrimônio, marca, modelo, IP, localização)…'
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
          <SelectTrigger>
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
        <SearchableSelect
          value={filtroCC}
          onChange={setFiltroCC}
          options={[
            { value: 'todos', label: 'Todos os CCs' },
            ...contratos.map((c) => ({ value: c.centro_custo, label: c.centro_custo })),
          ]}
        />
        <Select value={filtroStatus} onValueChange={setFiltroStatus}>
          <SelectTrigger>
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            <SelectItem value="Interno">Interno</SelectItem>
            <SelectItem value="Externo">Cedidos</SelectItem>
            <SelectItem value="Em Manutenção">Em Manutenção</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filtroTipo} onValueChange={setFiltroTipo}>
          <SelectTrigger>
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os tipos</SelectItem>
            {TIPOS_EQUIPAMENTO.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[600px] text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-2 text-left font-medium">Nome</th>
              <th className="px-4 py-2 text-left font-medium">Tipo</th>
              <th className="px-4 py-2 text-left font-medium">CC</th>
              <th className="px-4 py-2 text-left font-medium">Status</th>
              <th className="px-4 py-2 text-left font-medium">Responsável</th>
              {canWrite && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {loading && eletronicos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : eletronicos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                  Nenhum equipamento encontrado.
                </td>
              </tr>
            ) : (
              eletronicos.map((e) => {
                const temResp = assocsEl.some((a) => a.eletronico_id === e.id)
                return (
                  <tr key={e.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-2">
                      <p className="font-medium">{e.nome}</p>
                      <p className="text-xs text-muted-foreground">{e.numero_serie}</p>
                    </td>
                    <td className="px-4 py-2">{e.tipo}</td>
                    <td className="px-4 py-2">{e.centro_custo}</td>
                    <td className="px-4 py-2">
                      <Badge variant={STATUS_COLORS[e.status] as 'default' | 'secondary' | 'destructive'}>
                        {e.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2">
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
                      <td className="px-4 py-2">
                        <div className="flex gap-1 justify-end">
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
                          <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => abrirEditar(e)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => handleDelete(e.id)}>
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

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/30 px-4 py-2 text-sm">
          <span className="text-muted-foreground">
            Mostrando{' '}
            <strong>
              {(page - 1) * PAGE_SIZE + 1}–
              {Math.min(page * PAGE_SIZE, total)}
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
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editando ? 'Editar equipamento' : 'Novo equipamento'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSave} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(
              [
                ['nome', 'Nome', true],
                ['numero_serie', 'Nº Série', true],
                ['numero_patrimonio', 'Nº Patrimônio', true],
                ['marca', 'Marca', false],
                ['modelo', 'Modelo', false],
                ['ip', 'IP', false],
                ['localizacao', 'Localização', false],
              ] as [keyof typeof EMPTY, string, boolean][]
            ).map(([field, label, required]) => (
              <div key={field} className="space-y-1">
                <Label>{label}</Label>
                <Input
                  value={form[field]}
                  onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                  required={required}
                />
              </div>
            ))}
            <div className="space-y-1">
              <Label>Tipo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v }))}>
                <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                <SelectContent>
                  {TIPOS_EQUIPAMENTO.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Status</Label>
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
              <Label>Centro de Custo</Label>
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
                      label: `${u.nome} (${u.email})`,
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
              <Label>Descrição</Label>
              <Input value={form.descricao} onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))} />
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
                    .map((u) => ({ value: String(u.id), label: `${u.nome} (${u.email})` }))
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
    </div>
  )
}
