'use client'

import { useEffect, useState } from 'react'
import { Bell, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/context/auth-context'
import { MobileSidebar } from './mobile-sidebar'
import { BuscaGlobal } from './busca-global'
import { getSolicitacoes, aprovarSolicitacao, rejeitarSolicitacao } from '@/lib/api/solicitacoes'
import { getRecebimentosPendentesGestor } from '@/lib/api/cessoes'
import Link from 'next/link'
import type { Solicitacao } from '@/types/api'
import { formatDate } from '@/lib/utils'
import { toast } from 'sonner'

export function Topbar() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [convites, setConvites] = useState<Solicitacao[]>([])
  const [pendentes, setPendentes] = useState(0)
  const [recebimentos, setRecebimentos] = useState(0)
  const [sinoAberto, setSinoAberto] = useState(false)

  useEffect(() => setMounted(true), [])

  const load = () => {
    if (!user) return
    getRecebimentosPendentesGestor()
      .then((r) => setRecebimentos(r.count))
      .catch(() => {})
    getSolicitacoes()
      .then((list) => {
        // Convites são respondidos aqui; os demais pedidos, na tela de solicitações.
        setPendentes(
          list.filter((s) => s.status === 'pendente' && s.solicitante_id !== user.id).length,
        )
        return setConvites(
          list.filter(
            (s) =>
              s.status === 'pendente' &&
              s.convidado_por_id != null &&
              s.solicitante_id === user.id,
          ),
        )
      })
      .catch(() => {})
  }

  useEffect(() => {
    load()
    if (!user) return
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [user])

  const responder = async (id: number, aceitar: boolean) => {
    try {
      if (aceitar) await aprovarSolicitacao(id)
      else await rejeitarSolicitacao(id)
      toast.success(aceitar ? 'Convite aceito!' : 'Convite recusado.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao responder convite.')
    }
  }

  return (
    <header className="flex h-14 items-center gap-1 border-b bg-card px-4 md:px-6">
      <MobileSidebar />
      <BuscaGlobal />
      <div className="flex-1" />
      {mounted && (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Alternar tema"
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      )}
      <Sheet open={sinoAberto} onOpenChange={setSinoAberto}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            {convites.length + pendentes + recebimentos > 0 && (
              <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] text-white">
                {convites.length + pendentes + recebimentos}
              </span>
            )}
          </Button>
        </SheetTrigger>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Notificações</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-4 px-4">
            {pendentes > 0 && (
              <Link
                href="/solicitacoes"
                onClick={() => setSinoAberto(false)}
                className="block rounded-md border bg-warn-bg p-3 text-sm text-warn hover:border-ring"
              >
                <b>{pendentes} solicitação(ões) pendente(s)</b>
                <span className="block text-xs opacity-80">entrada em CC, cargo ou cessão esperando resposta</span>
              </Link>
            )}
            {recebimentos > 0 && (
              <Link
                href="/cessoes?aba=recebimentos"
                onClick={() => setSinoAberto(false)}
                className="block rounded-md border bg-info-bg p-3 text-sm text-info hover:border-ring"
              >
                <b>{recebimentos} devolução(ões) para conferir</b>
                <span className="block text-xs opacity-80">equipamentos que voltaram para os seus CCs</span>
              </Link>
            )}
            {convites.length > 0 && <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Convites</p>}
            {convites.length + pendentes + recebimentos === 0 && (
              <p className="text-sm text-muted-foreground">Nada esperando por você.</p>
            )}
            {convites.map((c) => (
              <div key={c.id} className="rounded-md border p-3 text-sm">
                <p className="font-medium">
                  Convite para{' '}
                  <Badge variant="outline">{c.centro_custo}</Badge> como{' '}
                  <span className="font-semibold">{c.ocupacao_solicitada}</span>
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{formatDate(c.criado_em)}</p>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" onClick={() => responder(c.id, true)}>
                    Aceitar
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => responder(c.id, false)}>
                    Recusar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </header>
  )
}
