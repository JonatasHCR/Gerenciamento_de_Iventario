'use client'

import { useEffect, useRef, useState } from 'react'
import { Grid2x2, ExternalLink } from 'lucide-react'

import type { Sistema } from '@/lib/sistemas'

/**
 * Voltar ao portal e pular para outro sistema, sem passar pela barra de
 * endereços.
 *
 * Com SSO a pessoa entra uma vez e circula entre três aplicações — mas cada uma
 * é um deploy separado, com sua própria navegação. Sem isto, sair de uma para
 * outra exige lembrar a porta.
 *
 * A lista vem de `/api/sistemas`, que a filtra no servidor pelos grupos da
 * sessão: o navegador não recebe a URL de um sistema a que a pessoa não tem
 * acesso.
 */
export function TrocarSistema({ collapsed = false }: { collapsed?: boolean }) {
  const [portal, setPortal] = useState<string | null>(null)
  const [sistemas, setSistemas] = useState<Sistema[]>([])
  const [aberto, setAberto] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/sistemas', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return
        setPortal(d.portal)
        setSistemas(d.sistemas ?? [])
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!aberto) return
    function fora(e: MouseEvent) {
      if (!caixa.current?.contains(e.target as Node)) setAberto(false)
    }
    function esc(e: KeyboardEvent) {
      if (e.key === 'Escape') setAberto(false)
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  // Sem sessão ainda, ou a chamada falhou: não desenha um botão que não leva a
  // lugar nenhum.
  if (!portal) return null

  return (
    <div className="relative" ref={caixa}>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-haspopup="menu"
        title="Ir para outro sistema"
        className="flex w-full items-center rounded-md px-2 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <Grid2x2 className="h-4 w-4 shrink-0" />
        {!collapsed && <span className="ml-2">Sistemas</span>}
      </button>

      {aberto && (
        <div
          role="menu"
          className="absolute bottom-full left-0 z-50 mb-1 min-w-52 overflow-hidden rounded-md border bg-popover py-1 shadow-md"
        >
          <a
            role="menuitem"
            href={portal}
            className="flex items-center justify-between gap-3 px-3 py-2 text-sm hover:bg-accent"
          >
            Portal
            <ExternalLink className="h-3.5 w-3.5 opacity-50" />
          </a>

          {sistemas.length > 0 && <div className="my-1 border-t" />}

          {sistemas.map((s) => (
            <a
              key={s.grupo}
              role="menuitem"
              href={s.url}
              className="flex items-center justify-between gap-3 px-3 py-2 text-sm hover:bg-accent"
            >
              {s.nome}
              <ExternalLink className="h-3.5 w-3.5 opacity-50" />
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
