'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import type { User } from '@/types/api'
import { apiLogin } from '@/lib/api/auth'
import { getUsers } from '@/lib/api/users'
import { getCookie, setCookie, deleteCookie, decodeJwt } from '@/lib/utils'
import { ApiError } from '@/lib/api/client'

export const TOKEN_COOKIE = 'invcontrol_token'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadUser = useCallback(async (isInitial: boolean) => {
    const token = getCookie(TOKEN_COOKIE)
    if (!token) {
      if (isInitial) setIsLoading(false)
      return
    }
    try {
      const payload = decodeJwt(token)
      const email = payload?.sub as string | undefined
      if (!email) throw new ApiError(401, 'Token inválido')
      const users = await getUsers()
      setUser(users.find((u) => u.email === email) ?? null)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        deleteCookie(TOKEN_COOKIE)
        setUser(null)
      }
    } finally {
      if (isInitial) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser(true)
    const id = setInterval(() => loadUser(false), 10000)
    return () => clearInterval(id)
  }, [loadUser])

  async function login(email: string, senha: string) {
    const data = await apiLogin(email, senha)
    setCookie(TOKEN_COOKIE, data.access_token, 7)
    const users = await getUsers()
    setUser(users.find((u) => u.email === email) ?? null)
  }

  function logout() {
    deleteCookie(TOKEN_COOKIE)
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
