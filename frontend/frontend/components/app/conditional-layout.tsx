'use client'

import { usePathname } from 'next/navigation'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { useAuth } from '@/context/auth-context'

const AUTH_PATHS = ['/login', '/cadastro']

export function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { isLoading } = useAuth()
  const isAuth = AUTH_PATHS.some((p) => pathname.startsWith(p))

  if (isAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
        {children}
      </div>
    )
  }

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
