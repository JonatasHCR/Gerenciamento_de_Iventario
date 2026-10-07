'use client'

import Link from 'next/link'
import {
  BarChart3,
  Boxes,
  Building2,
  ClipboardList,
  Database,
  FileText,
  History,
  LayoutDashboard,
  MapPin,
  Monitor,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { User } from '@/types/api'

interface Item {
  href: string
  label: string
  icon: LucideIcon
  so?: 'admin' | 'relatorios'
}

/** O menu dos dois lados (barra lateral e menu do celular), agrupado por assunto. */
const GRUPOS: [string, Item[]][] = [
  [
    'Operação',
    [
      { href: '/', label: 'Painel', icon: LayoutDashboard },
      { href: '/equipamentos', label: 'Equipamentos', icon: Monitor },
      { href: '/cessoes', label: 'Cessões', icon: FileText },
      { href: '/solicitacoes', label: 'Solicitações', icon: ClipboardList },
    ],
  ],
  [
    'Análise',
    [
      { href: '/relatorios', label: 'Relatórios', icon: BarChart3, so: 'relatorios' },
      { href: '/centros-de-custo', label: 'Centros de custo', icon: Building2 },
    ],
  ],
  [
    'Cadastros',
    [
      { href: '/usuarios', label: 'Usuários', icon: Users },
      { href: '/catalogo', label: 'Tipos e modelos', icon: Boxes, so: 'admin' },
      { href: '/localizacoes', label: 'Localizações', icon: MapPin, so: 'admin' },
    ],
  ],
  [
    'Administração',
    [
      { href: '/administracao', label: 'Backup e manutenção', icon: Database, so: 'admin' },
      { href: '/auditoria', label: 'Auditoria', icon: History, so: 'admin' },
    ],
  ],
]

function ativo(pathname: string, href: string) {
  if (href === '/catalogo' && ['/tipos', '/marcas', '/modelos'].includes(pathname)) return true
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(href + '/')
}

export function ListaNavegacao({
  user,
  ehGestorOuSub,
  pathname,
  pendentes,
  recebimentos,
  recolhido = false,
  onNavegar,
}: {
  user: User | null | undefined
  ehGestorOuSub: boolean
  pathname: string
  pendentes: number
  recebimentos: number
  recolhido?: boolean
  onNavegar?: () => void
}) {
  const isAdmin = user?.tipo === 'Admin'
  const isAdminTI = isAdmin || user?.tipo === 'Tecnico_TI'
  const pode = (i: Item) =>
    !i.so || (i.so === 'admin' ? isAdmin : isAdminTI || ehGestorOuSub)
  const contador = (href: string) =>
    href === '/solicitacoes' ? pendentes : href === '/cessoes' ? recebimentos : 0

  return (
    <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
      {GRUPOS.map(([grupo, itens]) => {
        const visiveis = itens.filter(pode)
        if (!visiveis.length) return null
        return (
          <div key={grupo}>
            <p
              className={cn(
                'px-3 pt-3 pb-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground',
                recolhido && 'invisible h-3 pt-1 pb-0',
              )}
            >
              {grupo}
            </p>
            {visiveis.map(({ href, label, icon: Icon }) => {
              const n = contador(href)
              const marcado = ativo(pathname, href)
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onNavegar}
                  title={recolhido ? label : undefined}
                  className={cn(
                    'relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    marcado
                      ? 'bg-secondary text-secondary-foreground before:absolute before:inset-y-2 before:-left-2 before:w-[3px] before:rounded-r before:bg-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!recolhido && <span className="flex-1">{label}</span>}
                  {n > 0 &&
                    (recolhido ? (
                      <span className="absolute top-1.5 left-7 size-2 rounded-full bg-primary" />
                    ) : (
                      <span className="rounded-full bg-primary px-1.5 text-[11px] font-bold text-primary-foreground">
                        {n}
                      </span>
                    ))}
                </Link>
              )
            })}
          </div>
        )
      })}
    </nav>
  )
}
