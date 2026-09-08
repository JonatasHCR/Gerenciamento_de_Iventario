'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import type { User } from '@/types/api'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

/**
 * Quem está logado, vindo do servidor.
 *
 * Antes isto decodificava o JWT no navegador, lia o `sub` esperando um email e
 * procurava esse email na LISTA COMPLETA de usuários — a cada 10 segundos, para
 * sempre. Com o padrão BFF o token não chega ao navegador, e `/api/auth/me`
 * responde a mesma pergunta com uma requisição só.
 *
 * Não há mais `login()`: quem pede a senha é o Keycloak. Quem não tem sessão
 * nem chega aqui, porque o middleware barra antes no servidor.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelado = false
    fetch('/api/auth/me', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelado) setUser(data)
      })
      .catch(() => {
        if (!cancelado) setUser(null)
      })
      .finally(() => {
        if (!cancelado) setIsLoading(false)
      })
    return () => {
      cancelado = true
    }
  }, [])

  function logout() {
    // Logout RP-initiated: encerra a sessão no Keycloak também, deslogando dos
    // três sistemas. Apagar só o cookie daqui deixaria o próximo acesso entrar
    // direto, sem pedir senha.
    window.location.href = '/api/auth/logout'
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
