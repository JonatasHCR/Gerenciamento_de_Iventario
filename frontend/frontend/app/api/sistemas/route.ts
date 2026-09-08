import { type NextRequest, NextResponse } from 'next/server'

import { lerSessao } from '@/lib/session'
import { outrosSistemas, portalUrl } from '@/lib/sistemas'

/**
 * Para onde mais esta pessoa pode ir.
 *
 * Rota de servidor, e nao `NEXT_PUBLIC_*`: uma variavel publica seria assada na
 * imagem em tempo de build e traria o IP de volta para dentro dos artefatos —
 * exatamente o que centralizar o HOST_IP evita.
 *
 * A filtragem acontece aqui: o navegador nao recebe a URL de um sistema a que a
 * pessoa nao tem acesso.
 */
export const dynamic = 'force-dynamic'

export async function GET(req: NextRequest) {
  const sessao = await lerSessao(req.cookies)
  if (!sessao) {
    return NextResponse.json({ detail: 'Sessão expirada' }, { status: 401 })
  }

  return NextResponse.json({
    portal: portalUrl(),
    sistemas: outrosSistemas(sessao.groups ?? []),
  })
}
