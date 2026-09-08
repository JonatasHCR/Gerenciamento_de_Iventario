import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// getCookie/setCookie/deleteCookie/decodeJwt foram removidos com o SSO.
//
// O cookie de sessão agora é `httpOnly` e cifrado: o JavaScript não o enxerga,
// e não há mais token no navegador para decodificar. Quem lê a sessão é o
// servidor (middleware, route handlers) via `lib/session.ts`.

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
