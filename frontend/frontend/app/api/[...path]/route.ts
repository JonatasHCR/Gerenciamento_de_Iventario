import { type NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.API_URL ?? 'http://localhost:8000'

async function proxy(req: NextRequest): Promise<NextResponse> {
  const backendPath = req.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${backendPath}${req.nextUrl.search}`

  const headers = new Headers(req.headers)
  headers.delete('host')
  headers.delete('connection')
  headers.delete('content-length')

  const isBodyless = ['GET', 'HEAD', 'DELETE'].includes(req.method)

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body: isBodyless ? undefined : await req.text(),
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
