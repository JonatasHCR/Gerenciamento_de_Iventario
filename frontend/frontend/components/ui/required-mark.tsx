/**
 * Asterisco padrão pra indicar campos obrigatórios em formulários.
 *
 * Uso: <Label>Nome <RequiredMark /></Label>
 *
 * O `aria-label` cobre leitores de tela; o `*` em si é vermelho do tema
 * destructive, alinhado pelo gap-2 já presente no <Label>.
 */
export function RequiredMark() {
  return (
    <span
      className="text-destructive leading-none"
      aria-label="obrigatório"
    >
      *
    </span>
  )
}
