'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Building2,
  Monitor,
  Users,
  ClipboardList,
  Menu,
  LogOut,
  FileText,
  BarChart3,
  Tags,
  MapPin,
  History,
} from 'lucide-react'
import { useAuth } from '@/context/auth-context'
import { getSolicitacoes } from '@/lib/api/solicitacoes'
import { getRecebimentosPendentesGestor } from '@/lib/api/cessoes'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

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
  { href: '/tipos', label: 'Tipos', icon: Tags, roles: ['Admin'] },
  { href: '/localizacoes', label: 'Localizações', icon: MapPin, roles: ['Admin'] },
  { href: '/auditoria', label: 'Auditoria', icon: History, roles: ['Admin'] },
] as const

export function MobileSidebar() {
  const [open, setOpen] = useState(false)
  const [pendentes, setPendentes] = useState(0)
  const [recebimentosPendentes, setRecebimentosPendentes] = useState(0)
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
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [user])

  useEffect(() => {
    if (!user) return
    getAssociacoesContrato()
      .then((all) => {
        setEhGestorOuSub(
          all.some(
            (a) =>
              a.user_id === user.id &&
              (a.ocupacao === 'Gestor' || a.ocupacao === 'Subgestor'),
          ),
        )
      })
      .catch(() => {})
  }, [user])

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="border-b px-4 py-3">
          <SheetTitle>InvControl</SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-1 p-2">
          {NAV.map((item) => {
            const { href, label, icon: Icon } = item
            if (href === '/relatorios') {
              const isAdminTI =
                user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'
              if (!isAdminTI && !ehGestorOuSub) return null
            }
            if (
              href === '/tipos' ||
              href === '/localizacoes' ||
              href === '/auditoria'
            ) {
              if (user?.tipo !== 'Admin') return null
            }
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
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
              </Link>
            )
          })}
        </nav>
        {user && (
          <div className="border-t p-3">
            <div className="mb-2 px-1">
              <p className="truncate text-sm font-medium">{user.nome}</p>
              <p className="text-xs text-muted-foreground">{user.tipo}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-muted-foreground hover:text-foreground"
              onClick={() => {
                setOpen(false)
                logout()
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="ml-2">Sair</span>
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
