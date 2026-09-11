import { NextResponse } from 'next/server'

import { baseUrl, clientId, endpoints } from '@/lib/oidc'

// Rota de servidor porque a URL vem do HOST_IP em runtime; um NEXT_PUBLIC_
// seria assado na imagem.
export const dynamic = 'force-dynamic'

export function GET() {
  // referrer/referrer_uri: sem eles o Account Console nao oferece volta. O
  // referrer_uri precisa estar nos redirectUris do client, ou vem ignorado.
  const params = new URLSearchParams({
    referrer: clientId(),
    referrer_uri: `${baseUrl()}/`,
  })
  return NextResponse.redirect(`${endpoints.conta()}?${params}`)
}
