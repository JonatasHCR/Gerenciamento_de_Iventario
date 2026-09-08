import { EncryptJWT, jwtDecrypt } from 'jose'
import type { NextResponse } from 'next/server'

/**
 * Contrato de sessao do BFF. Este arquivo e identico nos tres sistemas.
 *
 * O navegador recebe so um cookie opaco (JWE, httpOnly): o access token nunca
 * chega ate ele. Sem a flag `Secure`, porque `Secure` exige HTTPS e aqui tudo
 * anda em http — e a primeira linha a mudar quando houver TLS.
 */

export const COOKIE_SESSAO = 'inventario_session'
export const COOKIE_FLUXO = 'inventario_oauth'
export const COOKIE_DESTINO = 'inventario_destino'

// A sessao cifrada passa de 4096 bytes, o limite por cookie, e o Chrome
// descarta o excedente sem erro — vira um laco de login inexplicavel. Dai o
// fatiamento em `.0`, `.1`, ... Clientes HTTP de script nao aplicam o limite,
// entao isso nao aparece em teste.
const LIMITE_VALOR = 3500
const MAX_PARTES = 8

// Cookie nao distingue porta: sem DNS os quatro apps compartilham o host, e o
// navegador manda os cookies de todos para cada um. Guardando os tres tokens em
// cada app o header passa de 18 KB e o Node responde 431. Dai cada app guardar
// so o que usa.
const GUARDAR = {
  access_token: true, // o proxy /api/[...path] precisa dele para chamar a API
  refresh_token: true, // renovação no middleware
  id_token: false, // só serviria ao logout limpo, e quem o faz é o portal
} as const

export interface Sessao {
  /** Ausente quando a app não chama API (ver GUARDAR). */
  access_token?: string
  refresh_token?: string
  /** guardado so para o id_token_hint do logout RP-initiated */
  id_token?: string
  /** epoch em segundos */
  expires_at: number
  sub: string
  email: string
  name: string
  groups: string[]
}

/** Vive entre /login e /callback. */
export interface Fluxo {
  state: string
  nonce: string
  code_verifier: string
}

/** O comum entre NextRequest.cookies e o cookies() de next/headers. */
interface LeitorDeCookies {
  get(nome: string): { value: string } | undefined
}

function chave(): Uint8Array {
  const bruto = process.env.SESSION_SECRET
  if (!bruto || bruto.length < 32) {
    throw new Error(
      'SESSION_SECRET ausente ou com menos de 32 caracteres. ' +
        'Gere com `openssl rand -hex 32`.',
    )
  }
  return new TextEncoder().encode(bruto).slice(0, 32)
}

async function cifrar(dados: object, segundos: number): Promise<string> {
  return new EncryptJWT({ ...dados })
    .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
    .setIssuedAt()
    .setExpirationTime(`${segundos}s`)
    .encrypt(chave())
}

async function decifrar<T>(token: string): Promise<T | null> {
  try {
    const { payload } = await jwtDecrypt(token, chave())
    return payload as T
  } catch {
    return null
  }
}

const BASE_COOKIE = {
  httpOnly: true,
  sameSite: 'lax',
  path: '/',
  secure: false, // ver o comentario no topo do arquivo
} as const

/** Junta as fatias; aceita tambem o cookie unico. */
function juntarFatias(cookies: LeitorDeCookies): string | undefined {
  const inteiro = cookies.get(COOKIE_SESSAO)?.value
  if (inteiro) return inteiro

  const partes: string[] = []
  for (let i = 0; i < MAX_PARTES; i++) {
    const parte = cookies.get(`${COOKIE_SESSAO}.${i}`)?.value
    if (!parte) break
    partes.push(parte)
  }
  return partes.length > 0 ? partes.join('') : undefined
}

export async function gravarSessao(
  resposta: NextResponse,
  sessao: Sessao,
): Promise<void> {
  const duracao = 60 * 60 * 8 // acompanha o ssoSessionIdleTimeout do realm
  const valor = await cifrar(sessao, duracao)
  const opcoes = { ...BASE_COOKIE, maxAge: duracao }

  if (valor.length <= LIMITE_VALOR) {
    resposta.cookies.set(COOKIE_SESSAO, valor, opcoes)
    for (let i = 0; i < MAX_PARTES; i++) {
      resposta.cookies.delete(`${COOKIE_SESSAO}.${i}`)
    }
    return
  }

  const fatias: string[] = []
  for (let i = 0; i < valor.length; i += LIMITE_VALOR) {
    fatias.push(valor.slice(i, i + LIMITE_VALOR))
  }
  if (fatias.length > MAX_PARTES) {
    throw new Error(
      `Sessao com ${valor.length} bytes nao cabe em ${MAX_PARTES} cookies. ` +
        'Reduza o que e guardado na sessao.',
    )
  }

  resposta.cookies.delete(COOKIE_SESSAO)
  fatias.forEach((fatia, i) => {
    resposta.cookies.set(`${COOKIE_SESSAO}.${i}`, fatia, opcoes)
  })
  for (let i = fatias.length; i < MAX_PARTES; i++) {
    resposta.cookies.delete(`${COOKIE_SESSAO}.${i}`)
  }
}

/** Serve a `req.cookies` e ao `cookies()` de next/headers. */
export async function lerSessao(cookies: LeitorDeCookies): Promise<Sessao | null> {
  const bruto = juntarFatias(cookies)
  return bruto ? decifrar<Sessao>(bruto) : null
}

export function limparSessao(resposta: NextResponse): void {
  resposta.cookies.delete(COOKIE_SESSAO)
  for (let i = 0; i < MAX_PARTES; i++) {
    resposta.cookies.delete(`${COOKIE_SESSAO}.${i}`)
  }
  resposta.cookies.delete(COOKIE_FLUXO)
  resposta.cookies.delete(COOKIE_DESTINO)
}

export async function gravarFluxo(resposta: NextResponse, fluxo: Fluxo): Promise<void> {
  const duracao = 60 * 10 // o usuario tem 10 min para concluir o login
  resposta.cookies.set(COOKIE_FLUXO, await cifrar(fluxo, duracao), {
    ...BASE_COOKIE,
    maxAge: duracao,
  })
}

export async function lerFluxo(cookies: LeitorDeCookies): Promise<Fluxo | null> {
  const bruto = cookies.get(COOKIE_FLUXO)?.value
  return bruto ? decifrar<Fluxo>(bruto) : null
}

export function sessaoDeClaims(
  claims: Record<string, unknown>,
  tokens: {
    access_token: string
    refresh_token?: string
    id_token?: string
    expires_in: number
  },
): Sessao {
  return {
    ...(GUARDAR.access_token ? { access_token: tokens.access_token } : {}),
    ...(GUARDAR.refresh_token ? { refresh_token: tokens.refresh_token } : {}),
    ...(GUARDAR.id_token ? { id_token: tokens.id_token } : {}),
    expires_at: Math.floor(Date.now() / 1000) + tokens.expires_in,
    sub: String(claims.sub ?? ''),
    email: String(claims.email ?? ''),
    name: String(claims.name ?? claims.preferred_username ?? ''),
    groups: Array.isArray(claims.groups) ? (claims.groups as string[]) : [],
  }
}
