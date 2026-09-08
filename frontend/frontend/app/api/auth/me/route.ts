import { type NextRequest, NextResponse } from 'next/server'

import { lerSessao } from '@/lib/session'

/**
 * Quem esta logado.
 *
 * Substitui o que o `auth-context` fazia: decodificar o token no navegador,
 * ler o `sub` esperando um email, e procurar esse email na LISTA COMPLETA de
 * usuarios — repetindo a cada 10 segundos. Com o token fora do navegador aquilo
 * deixou de ser possivel, e era caro de qualquer forma.
 */
export const dynamic = 'force-dynamic'

const BACKEND = process.env.API_URL ?? 'http://backend:8000'

export async function GET(req: NextRequest) {
  const sessao = await lerSessao(req.cookies)
  if (!sessao?.access_token) {
    return NextResponse.json({ detail: 'Sessão expirada' }, { status: 401 })
  }

  const resposta = await fetch(`${BACKEND}/users/me`, {
    headers: { Authorization: `Bearer ${sessao.access_token}` },
    cache: 'no-store',
  })

  if (!resposta.ok) {
    return NextResponse.json(
      { detail: 'Não foi possível carregar o usuário' },
      { status: resposta.status },
    )
  }

  return NextResponse.json(await resposta.json())
}
