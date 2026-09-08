/**
 * Catalogo dos sistemas — o mesmo do portal (infra/portal/lib/sistemas.ts).
 *
 * Repetido aqui de proposito: sao quatro aplicacoes com deploy independente, e
 * um pacote compartilhado exigiria publicar e versionar. Sao doze linhas; a
 * duplicacao custa menos que o acoplamento.
 *
 * As portas vem do ambiente pelo mesmo motivo que o IP: elas entram nos
 * redirect URIs do realm, e os dois lados precisam concordar.
 */

export interface Sistema {
  grupo: string
  nome: string
  url: string
}

/** O grupo DESTE sistema — usado para nao se listar no proprio seletor. */
export const GRUPO_DESTE_SISTEMA = '/apps/inventario'

export function portalUrl(): string {
  const host = `http://${process.env.HOST_IP}`
  return `${host}:${process.env.PORTAL_PORT ?? '3080'}`
}

export function sistemas(): Sistema[] {
  const host = `http://${process.env.HOST_IP}`
  return [
    { grupo: '/apps/inventario', nome: 'Inventário', url: `${host}:${process.env.INVENTARIO_PORT ?? '3030'}` },
    { grupo: '/apps/receita', nome: 'Receita', url: `${host}:${process.env.RECEITA_PORT ?? '3040'}` },
    { grupo: '/apps/despesa', nome: 'Despesas', url: `${host}:${process.env.DESPESA_PORT ?? '3010'}` },
  ]
}

/** Os que a pessoa pode abrir, tirando o sistema em que ela ja esta. */
export function outrosSistemas(grupos: string[]): Sistema[] {
  return sistemas().filter(
    (s) => s.grupo !== GRUPO_DESTE_SISTEMA && grupos.includes(s.grupo),
  )
}
