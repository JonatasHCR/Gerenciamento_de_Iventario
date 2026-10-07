'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronLeft, ChevronRight, LogOut, Settings } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { useAuth } from '@/context/auth-context'
import { TrocarSistema } from './trocar-sistema'
import { ListaNavegacao } from './navegacao'
import { Iniciais, Marca } from './marca'
import { getSolicitacoes, createCargoInicial } from '@/lib/api/solicitacoes'
import { getRecebimentosPendentesGestor } from '@/lib/api/cessoes'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import { updateUser } from '@/lib/api/users'
import { Button } from '@/components/ui/button'
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

const POLL_MS = 5000

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [pendentes, setPendentes] = useState(0)
  const [recebimentosPendentes, setRecebimentosPendentes] = useState(0)
  const [profileOpen, setProfileOpen] = useState(false)
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
    setCargoSolicitado('')
    setProfileOpen(true)
  }

  async function salvarPerfil(e: React.FormEvent) {
    e.preventDefault()
    if (!user) return
    try {
      // Só o cargo: nome, e-mail e senha são do Keycloak.
      if (cargoSolicitado && cargoSolicitado !== user.tipo) {
        if (user.tipo === 'Admin') {
          await updateUser(user.id, { tipo: cargoSolicitado })
          toast.success('Cargo alterado!')
        } else {
          await createCargoInicial({ cargo_solicitado: cargoSolicitado })
          toast.success(`Solicitação de cargo "${cargoSolicitado}" enviada ao Admin.`)
        }
      }

      setProfileOpen(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r bg-sidebar transition-all duration-200',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <Link href="/" className={cn('flex items-center border-b py-4', collapsed ? 'justify-center px-2' : 'px-4')}>
        <Marca recolhida={collapsed} />
      </Link>

      <ListaNavegacao
        user={user}
        ehGestorOuSub={ehGestorOuSub}
        pathname={pathname}
        pendentes={pendentes}
        recebimentos={recebimentosPendentes}
        recolhido={collapsed}
      />

      <div className="border-t p-3">
        {user && (
          <button
            type="button"
            onClick={abrirPerfil}
            title={collapsed ? `${user.nome} · ${user.tipo}` : 'Meu perfil'}
            className={cn(
              'mb-2 flex w-full items-center gap-2.5 rounded-md p-1 text-left hover:bg-muted',
              collapsed && 'justify-center',
            )}
          >
            <Iniciais nome={user.nome} className="bg-primary/10 text-primary" />
            {!collapsed && (
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{user.nome}</span>
                <span className="block text-xs text-muted-foreground">{user.tipo}</span>
              </span>
            )}
          </button>
        )}
        {user?.tipo === 'Admin' && (
          <Button
            variant="ghost"
            size={collapsed ? 'icon' : 'sm'}
            className="w-full text-muted-foreground hover:text-foreground"
            asChild
          >
            <Link href="/administracao">
              <Settings className="h-4 w-4" />
              {!collapsed && <span className="ml-2">Administração</span>}
            </Link>
          </Button>
        )}
        <TrocarSistema collapsed={collapsed} />
        <Button
          variant="ghost"
          size={collapsed ? 'icon' : 'sm'}
          className="w-full text-muted-foreground hover:text-foreground"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && <span className="ml-2">Sair</span>}
        </Button>
        <Button
          variant="ghost"
          size={collapsed ? 'icon' : 'sm'}
          className="w-full text-muted-foreground hover:text-foreground"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          {!collapsed && <span className="ml-2">Recolher menu</span>}
        </Button>
      </div>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Meu perfil</DialogTitle>
          </DialogHeader>
          <form onSubmit={salvarPerfil} className="space-y-3" autoComplete="off">
            <div className="rounded-md border bg-muted/40 p-3">
              <p className="text-sm font-medium">{user?.nome}</p>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                Nome, e-mail e senha são os mesmos em todos os sistemas.
              </p>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages --
                  rota de servidor que redireciona para fora; Link navegaria no cliente */}
              <a
                href="/api/auth/conta"
                className="mt-2 inline-block text-sm font-medium underline underline-offset-4"
              >
                Alterar meus dados
              </a>
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
