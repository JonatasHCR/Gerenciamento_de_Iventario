import { getCookie, setCookie, deleteCookie } from '@/lib/utils'

const BASE_URL = '/api'
export const TOKEN_COOKIE = 'invcontrol_token'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

async function tryRefresh(): Promise<string | null> {
  const token = getCookie(TOKEN_COOKIE)
  if (!token) return null
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return null
    const data = (await res.json()) as { access_token: string }
    setCookie(TOKEN_COOKIE, data.access_token, 7)
    return data.access_token
  } catch {
    return null
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = getCookie(TOKEN_COOKIE)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401 && retry) {
    const newToken = await tryRefresh()
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`
      res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
    } else {
      deleteCookie(TOKEN_COOKIE)
      if (typeof window !== 'undefined') window.location.href = '/login'
      throw new ApiError(401, 'Sessão expirada')
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractError(res))
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

async function extractError(res: Response): Promise<string> {
  try {
    const err = (await res.json()) as { detail?: unknown }
    const d = err.detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) {
      return d
        .map((e: { loc?: string[]; msg?: string }) =>
          `${(e.loc ?? []).slice(1).join('.')}: ${e.msg ?? ''}`.trim(),
        )
        .join('; ')
    }
    return res.statusText || 'Erro desconhecido'
  } catch {
    return res.statusText || 'Erro desconhecido'
  }
}

export async function apiFormFetch<T>(
  path: string,
  body: URLSearchParams,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string
    }
    throw new ApiError(res.status, err.detail ?? 'Credenciais inválidas')
  }
  return res.json() as Promise<T>
}
