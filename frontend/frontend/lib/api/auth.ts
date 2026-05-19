import { apiFormFetch } from './client'
import type { TokenResponse } from '@/types/api'

export async function apiLogin(
  email: string,
  senha: string,
): Promise<TokenResponse> {
  return apiFormFetch<TokenResponse>(
    '/auth/login',
    new URLSearchParams({ username: email, password: senha }),
  )
}
