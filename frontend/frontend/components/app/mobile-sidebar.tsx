'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { Menu, LogOut } from 'lucide-react'
import { useAuth } from '@/context/auth-context'
import { TrocarSistema } from './trocar-sistema'
import { ListaNavegacao } from './navegacao'
import { Iniciais, Marca } from './marca'
import { getSolicitacoes } from '@/lib/api/solicitacoes'
import { getRecebimentosPendentesGestor } from '@/lib/api/cessoes'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

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
          <SheetTitle>
            <Marca />
          </SheetTitle>
        </SheetHeader>
        <ListaNavegacao
          user={user}
          ehGestorOuSub={ehGestorOuSub}
          pathname={pathname}
          pendentes={pendentes}
          recebimentos={recebimentosPendentes}
          onNavegar={() => setOpen(false)}
        />
        {user && (
          <div className="border-t p-3">
            <div className="mb-2 flex items-center gap-2.5 px-1">
              <Iniciais nome={user.nome} className="bg-primary/10 text-primary" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user.nome}</p>
                <p className="text-xs text-muted-foreground">{user.tipo}</p>
              </div>
            </div>
            <TrocarSistema />
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
