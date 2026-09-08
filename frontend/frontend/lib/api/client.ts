const BASE_URL = '/api'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/**
 * Chama a API pelo proxy deste mesmo servidor Next, que anexa o
 * `Authorization` a partir do cookie de sessão.
 *
 * O `tryRefresh()` que existia aqui foi removido — e com ele um bug antigo:
 * ele chamava `/auth/refresh`, mas a rota do backend era `/auth/refresh_token`.
 * O refresh dava 404 sempre, então todo 401 acabava em logout forçado, e
 * ninguém notou porque o token durava bastante. A renovação agora acontece no
 * middleware, no servidor, antes de o token vencer.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401) {
    // A sessão morreu (ou o refresh falhou). Quem monta a URL do Keycloak é o
    // servidor.
    if (typeof window !== 'undefined') {
      window.location.href = '/api/auth/login'
    }
    throw new ApiError(401, 'Sessão expirada')
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

// apiFormFetch existia só para o POST /auth/login (form-urlencoded). A rota
// não existe mais.
