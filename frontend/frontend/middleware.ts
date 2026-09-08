import { NextResponse, type NextRequest } from 'next/server'

import { renovar, verificar } from '@/lib/oidc'
import {
  gravarSessao,
  lerSessao,
  limparSessao,
  sessaoDeClaims,
  type Sessao,
} from '@/lib/session'

/**
 * Protege as rotas e RENOVA o token quando ele está perto de vencer.
 *
 * O refresh precisa acontecer aqui, e não na página: um Server Component não
 * pode gravar cookie, então conseguiria renovar o token mas não guardar o
 * resultado — e renovaria de novo a cada request. O middleware é o único ponto
 * do Next que lê a sessão e escreve na resposta.
 *
 * Substitui a checagem de `localStorage.getItem('authToken')` que ficava num
 * `useEffect` do PageWrapper: aquilo rodava depois de a página já ter sido
 * montada, então a tela piscava antes de redirecionar.
 */

const MARGEM_SEGUNDOS = 60

/**
 * Chamadas de dados vêm de `fetch`, não de navegação: responder com um redirect
 * faria o fetch segui-lo e devolver o HTML da tela de login com status 200, e o
 * `apiFetch` interpretaria isso como sucesso. Precisa ser 401 para o cliente
 * mandar a pessoa logar de novo.
 */
function ehChamadaDeApi(req: NextRequest): boolean {
  return req.nextUrl.pathname.startsWith('/api/')
}

function semSessao(req: NextRequest): NextResponse {
  if (ehChamadaDeApi(req)) {
    const resposta = NextResponse.json(
      { detail: 'Sessão expirada' },
      { status: 401 },
    )
    limparSessao(resposta)
    return resposta
  }

  const login = new URL('/api/auth/login', req.url)
  const destino = req.nextUrl.pathname + req.nextUrl.search
  if (destino !== '/') login.searchParams.set('destino', destino)

  const resposta = NextResponse.redirect(login)
  limparSessao(resposta)
  return resposta
}

export async function middleware(req: NextRequest) {
  const sessao = await lerSessao(req.cookies)
  if (!sessao) return semSessao(req)

  const agora = Math.floor(Date.now() / 1000)
  if (sessao.expires_at - MARGEM_SEGUNDOS > agora) {
    return NextResponse.next()
  }

  if (!sessao.refresh_token) return semSessao(req)

  try {
    const tokens = await renovar(sessao.refresh_token)
    if (!tokens.id_token) throw new Error('refresh sem id_token')

    const claims = await verificar(tokens.id_token)
    // Os grupos vêm do token novo: tirar alguém do grupo `/apps/despesa` no
    // Keycloak passa a valer na renovação seguinte, sem precisar deslogar.
    const renovada: Sessao = sessaoDeClaims(claims as Record<string, unknown>, tokens)

    const resposta = NextResponse.next()
    await gravarSessao(resposta, renovada)
    return resposta
  } catch (e) {
    // Refresh token expirado ou sessão encerrada no Keycloak (logout feito em
    // outro sistema). Não é erro: é hora de logar de novo.
    console.error('[middleware] refresh falhou:', e)
    return semSessao(req)
  }
}

export const config = {
  // Fora: as rotas de auth (senão o redirect para /api/auth/login entra em
  // laço), o healthcheck do container, os estáticos e arquivos com extensão.
  //
  // O proxy /api/[...path] fica DENTRO: ele precisa da sessão para anexar o
  // Authorization, e é aqui que o token é renovado antes de vencer.
  matcher: [
    '/((?!api/auth|api/health|_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
}
