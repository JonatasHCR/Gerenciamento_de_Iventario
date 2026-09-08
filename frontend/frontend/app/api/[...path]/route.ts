import { type NextRequest, NextResponse } from 'next/server'

import { lerSessao } from '@/lib/session'

/**
 * Proxy do navegador para o FastAPI.
 *
 * Já existia, mas apenas repassava adiante o `Authorization` que o navegador
 * mandava. Agora o header é montado AQUI, a partir do cookie de sessão cifrado:
 * o token nunca chega ao navegador, então um XSS não rouba credencial de API.
 */

const BACKEND = process.env.API_URL ?? 'http://localhost:8000'

async function proxy(req: NextRequest): Promise<NextResponse> {
  const sessao = await lerSessao(req.cookies)
  if (!sessao?.access_token) {
    return NextResponse.json({ detail: 'Sessão expirada' }, { status: 401 })
  }

  const backendPath = req.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${backendPath}${req.nextUrl.search}`

  const headers = new Headers(req.headers)
  headers.delete('host')
  headers.delete('connection')
  headers.delete('content-length')
  // O cookie de sessão é assunto deste servidor; mandá-lo adiante só vazaria a
  // sessão para dentro da rede.
  headers.delete('cookie')
  headers.set('Authorization', `Bearer ${sessao.access_token}`)

  const isBodyless = ['GET', 'HEAD', 'DELETE'].includes(req.method)

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    // arrayBuffer(), não text(): `text()` decodifica como UTF-8 e corrompe
    // qualquer upload binário (planilhas, anexos).
    body: isBodyless ? undefined : await req.arrayBuffer(),
    redirect: 'follow',
  })

  const resHeaders = new Headers(upstream.headers)
  resHeaders.delete('transfer-encoding')
  // fetch() já descomprime o body automaticamente, então o content-encoding
  // e o content-length originais (que refletiam o tamanho comprimido) viram
  // inválidos. Removendo ambos, o Next responde com chunked encoding e o
  // browser não trunca a resposta.
  resHeaders.delete('content-encoding')
  resHeaders.delete('content-length')

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  })
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
export const PATCH = proxy
