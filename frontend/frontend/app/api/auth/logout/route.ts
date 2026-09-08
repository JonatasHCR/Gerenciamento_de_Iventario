import { type NextRequest, NextResponse } from 'next/server'

import { baseUrl, clientId, endpoints } from '@/lib/oidc'
import { lerSessao, limparSessao } from '@/lib/session'

/**
 * Logout RP-initiated: alem de apagar o cookie daqui, encerra a sessao NO
 * KEYCLOAK — o que desloga a pessoa dos tres sistemas de uma vez. Apagar so o
 * cookie local deixaria o proximo /api/auth/login entrar direto, sem pedir
 * senha, e daria a impressao falsa de que o logout nao funcionou.
 */
export async function GET(req: NextRequest) {
  const sessao = await lerSessao(req.cookies)
  const inicio = new URL('/', baseUrl())

  const params = new URLSearchParams({
    client_id: clientId(),
    post_logout_redirect_uri: inicio.toString(),
  })
  // Sem o id_token_hint o Keycloak abre uma tela de confirmacao antes de
  // deslogar. E o unico motivo de a sessao guardar o id_token.
  if (sessao?.id_token) {
    params.set('id_token_hint', sessao.id_token)
  }

  const resposta = NextResponse.redirect(`${endpoints.logout()}?${params}`)
  limparSessao(resposta)
  return resposta
}
