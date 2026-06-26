'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Building2,
  Monitor,
  Users,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  LogOut,
  FileText,
  BarChart3,
  Tags,
  MapPin,
  Factory,
  Boxes,
  History,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { useAuth } from '@/context/auth-context'
import { getSolicitacoes, createCargoInicial } from '@/lib/api/solicitacoes'
import { getRecebimentosPendentesGestor } from '@/lib/api/cessoes'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import { updateUser, type UserUpdate } from '@/lib/api/users'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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

const CARGOS_SOLICITAVEIS = ['Gestor', 'Subgestor', 'Tecnico_TI']

const NAV = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/centros-de-custo', label: 'Centros de Custo', icon: Building2 },
  { href: '/equipamentos', label: 'Equipamentos', icon: Monitor },
  { href: '/cessoes', label: 'Cessões', icon: FileText },
  {
    href: '/relatorios',
    label: 'Relatórios',
    icon: BarChart3,
    roles: ['Admin', 'Tecnico_TI', 'Gestor', 'Subgestor'],
  },
  { href: '/usuarios', label: 'Usuários', icon: Users },
  { href: '/solicitacoes', label: 'Solicitações', icon: ClipboardList },
  {
    href: '/tipos',
    label: 'Tipos',
    icon: Tags,
    roles: ['Admin'],
  },
  {
    href: '/localizacoes',
    label: 'Localizações',
    icon: MapPin,
    roles: ['Admin'],
  },
  {
    href: '/marcas',
    label: 'Marcas',
    icon: Factory,
    roles: ['Admin'],
  },
  {
    href: '/modelos',
    label: 'Modelos',
    icon: Boxes,
    roles: ['Admin'],
  },
  {
    href: '/auditoria',
    label: 'Auditoria',
    icon: History,
    roles: ['Admin'],
  },
] as const

const POLL_MS = 5000

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [pendentes, setPendentes] = useState(0)
  const [recebimentosPendentes, setRecebimentosPendentes] = useState(0)
  const [profileOpen, setProfileOpen] = useState(false)
  const [form, setForm] = useState<UserUpdate>({})
  const [cargoSolicitado, setCargoSolicitado] = useState('')
  const [ehGestorOuSub, setEhGestorOuSub] = useState(false)
  const pathname = usePathname()
  const { user, logout } = useAuth()

  useEffect(() => {
    if (!user) return
    const load = () => {
      getSolicitacoes()
        .then((list) => setPendentes(list.filter((s) => s.status === 'pendente').length))
        .catch(() => {})
      getRecebimentosPendentesGestor()
        .then((r) => setRecebimentosPendentes(r.count))
        .catch(() => {})
    }
    load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [user])

  useEffect(() => {
    if (!user) return
    getAssociacoesContrato()
      .then((all) => {
        const tem = all.some(
          (a) =>
            a.user_id === user.id &&
            (a.ocupacao === 'Gestor' || a.ocupacao === 'Subgestor'),
        )
        setEhGestorOuSub(tem)
      })
      .catch(() => {})
  }, [user])

  function abrirPerfil() {
    if (!user) return
    setForm({ nome: user.nome, email: user.email, senha: '' })
    setCargoSolicitado('')
    setProfileOpen(true)
  }

  async function salvarPerfil(e: React.FormEvent) {
    e.preventDefault()
    if (!user) return
    try {
      const payload: UserUpdate = {}
      if (form.nome !== user.nome) payload.nome = form.nome
      if (form.email !== user.email) payload.email = form.email
      if (form.senha) payload.senha = form.senha

      const algoMudou = Object.keys(payload).length > 0
      if (algoMudou) {
        await updateUser(user.id, payload)
      }

      if (cargoSolicitado && cargoSolicitado !== user.tipo) {
        if (user.tipo === 'Admin') {
          await updateUser(user.id, { tipo: cargoSolicitado })
          toast.success('Cargo alterado!')
        } else {
          await createCargoInicial({ cargo_solicitado: cargoSolicitado })
          toast.success(`Solicitação de cargo "${cargoSolicitado}" enviada ao Admin.`)
        }
      } else if (algoMudou) {
        toast.success('Perfil atualizado!')
      }

      setProfileOpen(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r bg-card transition-all duration-200',
        collapsed ? 'w-16' : 'w-56',
      )}
    >
      <div className="flex items-center justify-between border-b px-3 py-4">
        {!collapsed && (
          <span className="text-sm font-semibold tracking-tight">InvControl</span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-7 w-7"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {NAV.map((item) => {
          const { href, label, icon: Icon } = item
          // Regra especial: /relatorios precisa Admin/TI OU ter Gestor/Subgestor em algum CC
          if (href === '/relatorios') {
            const isAdminTI =
              user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'
            if (!isAdminTI && !ehGestorOuSub) return null
          }
          // /tipos, /localizacoes, /auditoria: restritos pelo array roles
          if (
            href === '/tipos' ||
            href === '/localizacoes' ||
            href === '/marcas' ||
            href === '/modelos' ||
            href === '/auditoria'
          ) {
            if (user?.tipo !== 'Admin') return null
          }
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && (
                <span className="flex flex-1 items-center justify-between">
                  {label}
                  {href === '/solicitacoes' && pendentes > 0 && (
                    <Badge variant="destructive" className="ml-2 h-5 px-1.5 text-xs">
                      {pendentes}
                    </Badge>
                  )}
                  {href === '/cessoes' && recebimentosPendentes > 0 && (
                    <Badge
                      variant="destructive"
                      className="ml-2 h-5 px-1.5 text-xs"
                      title="Equipamento(s) recebido(s)"
                    >
                      {recebimentosPendentes}
                    </Badge>
                  )}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      <div className="border-t p-3">
        {!collapsed && user && (
          <button
            type="button"
            onClick={abrirPerfil}
            className="mb-2 w-full rounded-md px-1 py-1 text-left hover:bg-muted"
          >
            <p className="truncate text-sm font-medium">{user.nome}</p>
            <p className="text-xs text-muted-foreground">{user.tipo}</p>
          </button>
        )}
        <Button
          variant="ghost"
          size={collapsed ? 'icon' : 'sm'}
          className="w-full text-muted-foreground hover:text-foreground"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && <span className="ml-2">Sair</span>}
        </Button>
      </div>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Meu perfil</DialogTitle>
          </DialogHeader>
          <form onSubmit={salvarPerfil} className="space-y-3" autoComplete="off">
            <div className="space-y-1">
              <Label>Nome</Label>
              <Input
                value={form.nome ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                autoComplete="name"
              />
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input
                type="email"
                value={form.email ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                autoComplete="email"
              />
            </div>
            <div className="space-y-1">
              <Label>Nova senha (opcional)</Label>
              <Input
                type="password"
                value={form.senha ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, senha: e.target.value }))}
                placeholder="Deixe em branco para manter"
                autoComplete="new-password"
              />
            </div>
            {user && (
              <div className="space-y-1">
                <Label>
                  Cargo
                  {user.tipo !== 'Admin' && (
                    <span className="ml-1 text-xs text-muted-foreground">
                      (envia solicitação ao Admin)
                    </span>
                  )}
                </Label>
                <Select value={cargoSolicitado} onValueChange={setCargoSolicitado}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Atual: ${user.tipo}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {(user.tipo === 'Admin'
                      ? ['Funcionario', 'Subgestor', 'Gestor', 'Tecnico_TI', 'Admin']
                      : CARGOS_SOLICITAVEIS
                    ).map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button type="submit" className="w-full">Salvar</Button>
          </form>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
