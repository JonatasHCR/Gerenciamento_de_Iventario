import { randomBytes, createHash } from 'node:crypto'
import { type NextRequest, NextResponse } from 'next/server'

import { clientId, endpoints, redirectUri } from '@/lib/oidc'
import { COOKIE_DESTINO, gravarFluxo } from '@/lib/session'

function aleatorio(): string {
  return randomBytes(32).toString('base64url')
}

/**
 * Inicia o login: monta a URL de authorize e redireciona para o Keycloak.
 *
 * Sobre o PKCE: o design dispensava, porque com client confidencial o `state`
 * ja resolve CSRF. Mantemos assim mesmo — e justamente aqui que ele vale mais.
 * O authorization code volta na URL do navegador, que trafega EM TEXTO CLARO na
 * rede; quem estiver com sniffer consegue le-lo. O `code_verifier` nunca sai
 * deste servidor, entao o codigo sozinho nao serve para nada. Custa dez linhas
 * porque rodamos no servidor, onde `node:crypto` existe.
 */
export async function GET(req: NextRequest) {
  const state = aleatorio()
  const nonce = aleatorio()
  const codeVerifier = aleatorio()
  const codeChallenge = createHash('sha256').update(codeVerifier).digest('base64url')

  const params = new URLSearchParams({
    client_id: clientId(),
    redirect_uri: redirectUri(),
    response_type: 'code',
    scope: 'openid profile email',
    state,
    nonce,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  })

  // Para onde voltar depois do login, quando o middleware interceptou uma rota.
  const destino = req.nextUrl.searchParams.get('destino')

  const resposta = NextResponse.redirect(`${endpoints.authorize()}?${params}`)
  await gravarFluxo(resposta, { state, nonce, code_verifier: codeVerifier })
  if (destino?.startsWith('/')) {
    resposta.cookies.set(COOKIE_DESTINO, destino, {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      maxAge: 600,
    })
  }
  return resposta
}
