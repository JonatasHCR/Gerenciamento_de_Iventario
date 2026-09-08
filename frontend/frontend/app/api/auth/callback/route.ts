import { type NextRequest, NextResponse } from 'next/server'

import { baseUrl, trocarCodigo, verificar } from '@/lib/oidc'
import {
  COOKIE_DESTINO,
  COOKIE_FLUXO,
  gravarSessao,
  lerFluxo,
  limparSessao,
  sessaoDeClaims,
} from '@/lib/session'

/**
 * O Keycloak devolve o usuario aqui com um `code`. A troca por token acontece
 * NESTE servidor — o navegador nunca ve token nenhum, so recebe o cookie de
 * sessao cifrado.
 */
export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams
  const inicio = new URL('/', baseUrl())

  // O Keycloak sinaliza erro por query string, nao por status HTTP.
  const erro = params.get('error')
  if (erro) {
    inicio.searchParams.set('erro', params.get('error_description') ?? erro)
    return NextResponse.redirect(inicio)
  }

  const code = params.get('code')
  const state = params.get('state')
  const fluxo = await lerFluxo(req.cookies)

  if (!code || !state || !fluxo || state !== fluxo.state) {
    // State ausente ou diferente = requisicao forjada, ou o cookie de fluxo
    // expirou (o usuario deixou a tela de login aberta tempo demais).
    inicio.searchParams.set('erro', 'Sessao de login expirou. Tente de novo.')
    const recusa = NextResponse.redirect(inicio)
    limparSessao(recusa)
    return recusa
  }

  try {
    const tokens = await trocarCodigo(code, fluxo.code_verifier)
    if (!tokens.id_token) throw new Error('Keycloak nao devolveu id_token')

    // Assinatura, emissor, audiencia e nonce.
    const claims = await verificar(tokens.id_token, fluxo.nonce)

    const destino = req.cookies.get(COOKIE_DESTINO)?.value
    const alvo = destino?.startsWith('/') ? new URL(destino, baseUrl()) : inicio

    const resposta = NextResponse.redirect(alvo)
    await gravarSessao(
      resposta,
      sessaoDeClaims(claims as Record<string, unknown>, tokens),
    )
    resposta.cookies.delete(COOKIE_DESTINO)
    resposta.cookies.delete(COOKIE_FLUXO)
    return resposta
  } catch (e) {
    console.error('[auth/callback]', e)
    inicio.searchParams.set('erro', 'Nao foi possivel concluir o login.')
    const falha = NextResponse.redirect(inicio)
    limparSessao(falha)
    return falha
  }
}
