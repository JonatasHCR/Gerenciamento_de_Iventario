import { NextResponse } from 'next/server'

import { endpoints } from '@/lib/oidc'

/**
 * Leva ao Account Console do Keycloak, onde a pessoa troca a senha.
 *
 * E uma rota de servidor de proposito: a URL vem do HOST_IP em runtime. Um
 * `NEXT_PUBLIC_...` seria assado na imagem em tempo de build e traria o IP de
 * volta para dentro dos artefatos — exatamente o que centralizar a variavel
 * evita.
 */
export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.redirect(endpoints.conta())
}
