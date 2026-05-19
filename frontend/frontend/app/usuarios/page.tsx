'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getUsers,
  deleteUser,
  updateUser,
  createUserAdmin,
  type UserUpdate,
} from '@/lib/api/users'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato, deleteAssociacaoContrato } from '@/lib/api/associacoes'
import { createConviteCC } from '@/lib/api/solicitacoes'
import type { User, Contrato, AssociacaoUserContrato, Ocupacao } from '@/types/api'
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
  UserPlus,
  Trash2,
  Pencil,
  Plus,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { SearchableSelect } from '@/components/app/searchable-select'

const TIPOS = ['Funcionario', 'Subgestor', 'Gestor', 'Tecnico_TI', 'Admin']

const CAMPOS_BUSCA: Record<string, string> = {
  todos: 'Todos os campos',
  nome: 'Nome',
  email: 'Email',
  tipo: 'Tipo',
}

export default function UsuariosPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [assocs, setAssocs] = useState<AssociacaoUserContrato[]>([])
  const [search, setSearch] = useState('')
  const [campoBusca, setCampoBusca] = useState('todos')
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  const [openConvite, setOpenConvite] = useState(false)
  const [conviteCC, setConviteCC] = useState('')
  const [conviteUserId, setConviteUserId] = useState('')
  const [conviteOcupacao, setConviteOcupacao] = useState<Ocupacao>('Funcionario')

  const [editing, setEditing] = useState<User | null>(null)
  const [editForm, setEditForm] = useState<UserUpdate>({})

  const [openNovo, setOpenNovo] = useState(false)
  const [novo, setNovo] = useState({ nome: '', email: '', senha: '', tipo: 'Funcionario' })

  const load = () => {
    getUsers().then(setUsers).catch(() => {})
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesContrato().then(setAssocs).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const canInvite = user?.tipo === 'Admin' || user?.tipo === 'Gestor' || user?.tipo === 'Subgestor'
  const isAdmin = user?.tipo === 'Admin'

  const meusCCs = assocs.filter((a) => a.user_id === user?.id).map((a) => a.centro_custo)
  const ccsParaExibir = isAdmin || user?.tipo === 'Tecnico_TI'
    ? contratos.map((c) => c.centro_custo)
    : meusCCs

  function toggleCollapse(key: string) {
    setCollapsed((s) => {
      const n = new Set(s)
      if (n.has(key)) n.delete(key)
      else n.add(key)
      return n
    })
  }

  function matchUser(u: User): boolean {
    const term = search.toLowerCase()
    if (!term) return true
    if (campoBusca === 'todos') {
      return Object.keys(CAMPOS_BUSCA)
        .filter((k) => k !== 'todos')
        .some((k) => {
          const v = u[k as keyof User]
          return v != null && String(v).toLowerCase().includes(term)
        })
    }
    const v = u[campoBusca as keyof User]
    return v != null && String(v).toLowerCase().includes(term)
  }

  async function handleConvite(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createConviteCC({
        solicitante_id: parseInt(conviteUserId),
        centro_custo: conviteCC,
        ocupacao_solicitada: conviteOcupacao,
      })
      toast.success('Convite enviado!')
      setOpenConvite(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao enviar convite.')
    }
  }

  async function handleRemover(userId: number, cc: string) {
    try {
      await deleteAssociacaoContrato(userId, cc)
      toast.success('Removido do CC!')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao remover.')
    }
  }

  async function handleDeleteUser(id: number) {
    try {
      await deleteUser(id)
      toast.success('Usuário excluído!')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao excluir.')
    }
  }

  function abrirEdicao(u: User) {
    setEditing(u)
    setEditForm({ nome: u.nome, email: u.email, tipo: u.tipo, senha: '' })
  }

  async function handleEditSave(e: React.FormEvent) {
    e.preventDefault()
    if (!editing) return
    try {
      const payload: UserUpdate = {}
      if (editForm.nome !== editing.nome) payload.nome = editForm.nome
      if (editForm.email !== editing.email) payload.email = editForm.email
      if (editForm.tipo !== editing.tipo) payload.tipo = editForm.tipo
      if (editForm.senha) payload.senha = editForm.senha

      await updateUser(editing.id, payload)
      toast.success('Usuário atualizado!')
      setEditing(null)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao atualizar.')
    }
  }

  async function handleNovo(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createUserAdmin(novo)
      toast.success('Usuário criado!')
      setOpenNovo(false)
      setNovo({ nome: '', email: '', senha: '', tipo: 'Funcionario' })
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao criar.')
    }
  }

  const ocupacoesPermitidas: Ocupacao[] =
    user?.tipo === 'Subgestor' ? ['Funcionario'] : ['Gestor', 'Subgestor', 'Funcionario']

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Usuários</h1>
        <div className="flex gap-2">
          {isAdmin && (
            <Button size="sm" onClick={() => setOpenNovo(true)}>
              <Plus className="mr-1 h-4 w-4" /> Criar
            </Button>
          )}
          {canInvite && (
            <Button size="sm" variant="outline" onClick={() => setOpenConvite(true)}>
              <UserPlus className="mr-1 h-4 w-4" /> Convidar
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Input
          placeholder="Buscar…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={campoBusca} onValueChange={setCampoBusca}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(CAMPOS_BUSCA).map(([k, l]) => (
              <SelectItem key={k} value={k}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {ccsParaExibir.map((cc) => {
        const membros = assocs
          .filter((a) => a.centro_custo === cc)
          .filter((a) => {
            const u = users.find((x) => x.id === a.user_id)
            return u ? matchUser(u) : false
          })
        const isCollapsed = collapsed.has(`cc:${cc}`)
        return (
          <div key={cc} className="rounded-md border">
            <button
              type="button"
              onClick={() => toggleCollapse(`cc:${cc}`)}
              className="flex w-full items-center gap-2 border-b bg-muted/50 px-4 py-2 text-left font-medium hover:bg-muted"
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              <span>{cc}</span>
              <span className="ml-auto text-xs text-muted-foreground">{membros.length}</span>
            </button>
            {!isCollapsed && (
              <div className="divide-y">
                {membros.length === 0 && (
                  <p className="px-4 py-3 text-sm text-muted-foreground">Sem membros.</p>
                )}
                {membros.map((m) => {
                  const u = users.find((x) => x.id === m.user_id)
                  return (
                    <div key={m.user_id} className="flex items-center justify-between px-4 py-2">
                      <div>
                        <p className="text-sm font-medium">{u?.nome ?? `#${m.user_id}`}</p>
                        <p className="text-xs text-muted-foreground">{u?.email}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{m.ocupacao}</Badge>
                        {canInvite && m.user_id !== user?.id && (
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 text-destructive"
                            onClick={() => handleRemover(m.user_id, cc)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}

      {isAdmin && (() => {
        const filtered = users.filter(matchUser)
        const isCollapsed = collapsed.has('all-users')
        return (
          <div className="rounded-md border">
            <button
              type="button"
              onClick={() => toggleCollapse('all-users')}
              className="flex w-full items-center gap-2 border-b bg-muted/50 px-4 py-2 text-left font-medium hover:bg-muted"
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              <span>Todos os usuários</span>
              <span className="ml-auto text-xs text-muted-foreground">{filtered.length}</span>
            </button>
            {!isCollapsed && (
              <div className="divide-y">
                {filtered.map((u) => (
                  <div key={u.id} className="flex items-center justify-between px-4 py-2">
                    <div>
                      <p className="text-sm font-medium">{u.nome}</p>
                      <p className="text-xs text-muted-foreground">{u.email}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{u.tipo}</Badge>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={() => abrirEdicao(u)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      {u.id !== user.id && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-destructive"
                          onClick={() => handleDeleteUser(u.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })()}

      <Dialog open={openConvite} onOpenChange={setOpenConvite}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Convidar usuário para CC</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleConvite} className="space-y-3">
            <div className="space-y-1">
              <Label>Usuário</Label>
              <SearchableSelect
                value={conviteUserId}
                onChange={setConviteUserId}
                options={users
                  .filter((u) => u.id !== user?.id)
                  .map((u) => ({ value: String(u.id), label: `${u.nome} (${u.email})` }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Centro de Custo</Label>
              <SearchableSelect
                value={conviteCC}
                onChange={setConviteCC}
                options={(isAdmin ? contratos.map((c) => c.centro_custo) : meusCCs).map((cc) => ({
                  value: cc,
                  label: cc,
                }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Cargo no CC</Label>
              <Select value={conviteOcupacao} onValueChange={(v) => setConviteOcupacao(v as Ocupacao)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ocupacoesPermitidas.map((o) => (
                    <SelectItem key={o} value={o}>{o}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" className="w-full" disabled={!conviteUserId || !conviteCC}>
              Enviar convite
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={openNovo} onOpenChange={setOpenNovo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Criar novo usuário</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleNovo} className="space-y-3" autoComplete="off">
            <div className="space-y-1">
              <Label>Nome</Label>
              <Input
                value={novo.nome}
                onChange={(e) => setNovo((n) => ({ ...n, nome: e.target.value }))}
                required
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input
                type="email"
                value={novo.email}
                onChange={(e) => setNovo((n) => ({ ...n, email: e.target.value }))}
                required
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <Label>Senha</Label>
              <Input
                type="password"
                value={novo.senha}
                onChange={(e) => setNovo((n) => ({ ...n, senha: e.target.value }))}
                required
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-1">
              <Label>Tipo</Label>
              <Select value={novo.tipo} onValueChange={(v) => setNovo((n) => ({ ...n, tipo: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIPOS.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" className="w-full">Criar</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={editing !== null} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar usuário</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSave} className="space-y-3" autoComplete="off">
            <div className="space-y-1">
              <Label>Nome</Label>
              <Input
                value={editForm.nome ?? ''}
                onChange={(e) => setEditForm((f) => ({ ...f, nome: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input
                type="email"
                value={editForm.email ?? ''}
                onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <Label>Nova senha (opcional)</Label>
              <Input
                type="password"
                value={editForm.senha ?? ''}
                onChange={(e) => setEditForm((f) => ({ ...f, senha: e.target.value }))}
                placeholder="Deixe em branco para manter"
                autoComplete="new-password"
              />
            </div>
            {isAdmin && (
              <div className="space-y-1">
                <Label>Tipo</Label>
                <Select
                  value={editForm.tipo ?? ''}
                  onValueChange={(v) => setEditForm((f) => ({ ...f, tipo: v }))}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TIPOS.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button type="submit" className="w-full">Salvar</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
