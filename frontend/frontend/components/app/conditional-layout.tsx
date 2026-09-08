'use client'

import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { useAuth } from '@/context/auth-context'

/**
 * O ramo que centralizava as páginas `/login` e `/cadastro` foi removido junto
 * com elas: a tela de senha agora é do Keycloak, e o middleware garante que
 * nada aqui renderiza sem sessão. Toda rota que chega tem barra lateral.
 */
export function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const { isLoading } = useAuth()

  if (isLoading) return null

  return (
    <div className="flex h-screen overflow-hidden print:block print:h-auto print:overflow-visible">
      <div className="hidden md:flex print:hidden">
        <Sidebar />
      </div>
      <div className="flex flex-1 flex-col overflow-hidden print:block print:overflow-visible">
        <div className="print:hidden">
          <Topbar />
        </div>
        <main className="flex-1 overflow-y-auto p-4 md:p-6 print:overflow-visible print:p-0">
          {children}
        </main>
      </div>
    </div>
  )
}
