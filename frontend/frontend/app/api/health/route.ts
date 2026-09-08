import { NextResponse } from 'next/server'

/**
 * Alvo do HEALTHCHECK do container. Precisa ficar FORA do middleware: a raiz `/`
 * agora redireciona para o login, e o wget do healthcheck seguiria o redirect
 * ate o Keycloak — dando o container por saudavel ou nao conforme o estado de
 * outro servico.
 */
export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json({ status: 'ok' })
}
