import { NextResponse } from 'next/server'

import { portalUrl } from '@/lib/sistemas'
import { limparSessao } from '@/lib/session'

// Delega ao portal: o realm so autoriza a URL dele em post.logout.redirect.uris
// (a propria devolve 400), e so ele guarda o id_token.
export const dynamic = 'force-dynamic'

export function GET() {
  const resposta = NextResponse.redirect(`${portalUrl()}/api/auth/logout`)
  limparSessao(resposta)
  return resposta
}
