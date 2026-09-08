import { createRemoteJWKSet, jwtVerify, type JWTPayload } from 'jose'

/**
 * Cliente OIDC do lado do SERVIDOR (copia do portal, ver infra/portal/lib).
 *
 * Todo o fluxo roda aqui, nunca no navegador. Sem TLS o browser nao expoe
 * `crypto.subtle`, entao o PKCE do lado do cliente simplesmente nao funciona em
 * `http://<ip>` — e a biblioteca OIDC de browser quebra. Rodando no servidor
 * temos `node:crypto` e o problema desaparece.
 *
 * Nao e um remendo: o BFF e o desenho mais seguro dos dois, porque o token
 * nunca fica ao alcance de XSS. O trabalho nao se perde se um dia houver TLS.
 */

function obrigatoria(nome: string): string {
  const valor = process.env[nome]
  if (!valor) {
    throw new Error(
      `${nome} nao definida. O portal nao sobe sem ela — confira o infra/.env.`,
    )
  }
  return valor
}

/** `http://<HOST_IP>:8080/realms/ufc` — a MESMA string para navegador e containers. */
export function issuer(): string {
  return `http://${obrigatoria('HOST_IP')}:8080/realms/ufc`
}

export function clientId(): string {
  return process.env.OIDC_CLIENT_ID ?? 'inventario-web'
}

export function clientSecret(): string {
  return obrigatoria('OIDC_CLIENT_SECRET')
}

/**
 * URL publica DESTE app, montada do HOST_IP — NUNCA de `req.url`.
 *
 * O Next deriva `req.url` do hostname com que o servidor faz bind, nao do
 * header Host. Dentro do container esse hostname e `0.0.0.0`, entao um
 * `new URL('/', req.url)` produz `http://0.0.0.0:3080/` e o navegador nao
 * consegue seguir o redirect. So aparece rodando em container.
 */
export function baseUrl(): string {
  return `http://${obrigatoria('HOST_IP')}:${process.env.PORTA_PUBLICA ?? '3000'}`
}

export function redirectUri(): string {
  return `${baseUrl()}/api/auth/callback`
}

export const endpoints = {
  authorize: () => `${issuer()}/protocol/openid-connect/auth`,
  token: () => `${issuer()}/protocol/openid-connect/token`,
  logout: () => `${issuer()}/protocol/openid-connect/logout`,
  jwks: () => `${issuer()}/protocol/openid-connect/certs`,
  conta: () => `${issuer()}/account`,
}

// createRemoteJWKSet mantem cache das chaves; instanciar uma vez por processo.
let jwks: ReturnType<typeof createRemoteJWKSet> | null = null
function chaves() {
  if (!jwks) jwks = createRemoteJWKSet(new URL(endpoints.jwks()))
  return jwks
}

export interface Tokens {
  access_token: string
  refresh_token?: string
  id_token?: string
  expires_in: number
}

async function pedirToken(corpo: Record<string, string>): Promise<Tokens> {
  const resp = await fetch(endpoints.token(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: clientId(),
      client_secret: clientSecret(),
      ...corpo,
    }),
    cache: 'no-store',
  })

  if (!resp.ok) {
    throw new Error(`Keycloak recusou o token (${resp.status}): ${await resp.text()}`)
  }
  return resp.json()
}

export function trocarCodigo(code: string, codeVerifier: string): Promise<Tokens> {
  return pedirToken({
    grant_type: 'authorization_code',
    code,
    redirect_uri: redirectUri(),
    code_verifier: codeVerifier,
  })
}

export function renovar(refreshToken: string): Promise<Tokens> {
  return pedirToken({ grant_type: 'refresh_token', refresh_token: refreshToken })
}

/**
 * Valida assinatura, emissor e audiencia do token. `nonce` amarra o id_token a
 * ESTA tentativa de login.
 */
export async function verificar(token: string, nonce?: string): Promise<JWTPayload> {
  const { payload } = await jwtVerify(token, chaves(), {
    issuer: issuer(),
    audience: clientId(),
  })
  if (nonce && payload.nonce !== nonce) {
    throw new Error('nonce do id_token nao confere com o da requisicao')
  }
  return payload
}
