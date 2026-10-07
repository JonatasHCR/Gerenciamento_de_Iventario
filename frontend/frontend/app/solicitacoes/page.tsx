'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getSolicitacoes,
  aprovarSolicitacao,
  rejeitarSolicitacao,
  cancelarSolicitacao,
} from '@/lib/api/solicitacoes'
import type { Solicitacao, User } from '@/types/api'
import { getUsers } from '@/lib/api/users'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'
import { Check, X, Trash2, FileText, ArrowRight, LogIn, UserCog } from 'lucide-react'
import { cn } from '@/lib/utils'

const SITUACAO: Record<Solicitacao['status'], [string, string]> = {
  pendente: ['Pendente', 'bg-warn-bg text-warn'],
  aprovada: ['Aprovada', 'bg-ok-bg text-ok'],
  rejeitada: ['Recusada', 'bg-muted text-muted-foreground'],
}

const ICONE = { cessao: ArrowRight, entrada_cc: LogIn, cargo_inicial: UserCog }

export default function SolicitacoesPage() {
  const { user } = useAuth()
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([])
  const [usuarios, setUsuarios] = useState<User[]>([])
  const nomeDe = (id: number) => usuarios.find((u) => u.id === id)?.nome ?? `#${id}`

  const load = () => {
    getSolicitacoes().then(setSolicitacoes).catch(() => {})
  }

  useEffect(() => {
    getUsers().then(setUsuarios).catch(() => {})
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  async function aprovar(id: number) {
    try {
      await aprovarSolicitacao(id)
      toast.success('Aprovado!')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao aprovar.')
    }
  }

  async function rejeitar(id: number) {
    try {
      await rejeitarSolicitacao(id)
      toast.success('Rejeitado.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao rejeitar.')
    }
  }

  async function cancelar(id: number) {
    try {
      await cancelarSolicitacao(id)
      toast.success('Cancelado.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao cancelar.')
    }
  }

  const pendentes = solicitacoes.filter((s) => s.status === 'pendente')
  const historico = solicitacoes.filter((s) => s.status !== 'pendente')

  const labelTipo = (t: Solicitacao['tipo']) => {
    if (t === 'entrada_cc') return 'Entrada em CC'
    if (t === 'cargo_inicial') return 'Cargo inicial'
    return 'Cessão de equipamentos'
  }

  const renderItem = (s: Solicitacao) => {
    const isPendente = s.status === 'pendente'
    const isMinha = s.solicitante_id === user?.id
    const isConvite = s.convidado_por_id != null
    const isAdmin = user?.tipo === 'Admin'
    const canAprovar =
      isPendente &&
      (
        isAdmin ||
        // convite: apenas o convidado aceita
        (s.tipo === 'entrada_cc' && isConvite && isMinha) ||
        // entrada_cc sem convite: Gestor/Subgestor do CC (backend valida)
        (s.tipo === 'entrada_cc' && !isConvite && !isMinha &&
          user?.tipo !== 'Funcionario' && user?.tipo !== 'Tecnico_TI') ||
        // cessao: Gestor do CC (backend revalida)
        (s.tipo === 'cessao' && !isMinha &&
          (user?.tipo === 'Gestor' || user?.tipo === 'Admin'))
      )

    const Icone = ICONE[s.tipo]
    const [rotulo, cor] = SITUACAO[s.status]
    return (
      <li key={s.id} className="flex flex-wrap items-start gap-3 px-4 py-3.5">
        <span
          className={cn(
            'grid size-9 shrink-0 place-items-center rounded-lg',
            isPendente ? 'bg-warn-bg text-warn' : 'bg-muted text-muted-foreground',
          )}
        >
          <Icone className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1 space-y-0.5">
          <p className="text-sm">
            <b className="font-semibold">{nomeDe(s.solicitante_id)}</b>
            <span className="text-muted-foreground"> · {labelTipo(s.tipo)}</span>
            {isConvite && <span className="text-muted-foreground"> · convite</span>}
            <span className={cn('ml-2 rounded-full px-2 py-0.5 text-xs font-medium', cor)}>{rotulo}</span>
          </p>
          {s.tipo === 'cessao' ? (
            <p className="text-sm text-muted-foreground">
              {s.eletronicos?.length ?? 0} equipamento(s) do CC {s.centro_custo} para o CC{' '}
              {s.centro_custo_destino} · recebe <strong className="text-foreground">{s.responsavel}</strong>
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              {s.centro_custo && <>CC {s.centro_custo}</>}
              {s.ocupacao_solicitada && <> como {s.ocupacao_solicitada}</>}
              {s.cargo_solicitado && <>cargo {s.cargo_solicitado}</>}
            </p>
          )}
          <p className="text-xs text-muted-foreground">{formatDate(s.criado_em)}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          {s.tipo === 'cessao' && (
            <Button size="sm" variant="ghost" asChild>
              <Link href={`/solicitacoes/${s.id}/termo`}>
                <FileText className="h-4 w-4" /> Termo
              </Link>
            </Button>
          )}
          {isPendente && canAprovar && (
            <>
              <Button size="sm" variant="outline" onClick={() => rejeitar(s.id)}>
                <X className="h-4 w-4" /> Recusar
              </Button>
              <Button size="sm" onClick={() => aprovar(s.id)}>
                <Check className="h-4 w-4" /> Aprovar
              </Button>
            </>
          )}
          {(isAdmin || (isPendente && isMinha)) && (
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-destructive"
              onClick={() => cancelar(s.id)}
              title={isAdmin ? 'Excluir' : 'Cancelar'}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </li>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Solicitações</h1>
        <p className="text-sm text-muted-foreground">
          Pedidos de entrada em CC, de cargo e de cessão que esperam resposta.
        </p>
      </div>

      <section className="rounded-xl border bg-card shadow-xs">
        <header className="flex items-center gap-2 border-b px-4 py-3">
          <h2 className="text-sm font-semibold">Pendentes</h2>
          {pendentes.length > 0 && (
            <span className="rounded-full bg-primary px-2 text-xs font-bold text-primary-foreground">
              {pendentes.length}
            </span>
          )}
        </header>
        {pendentes.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted-foreground">
            Nada pendente. Quando alguém pedir, aparece aqui.
          </p>
        ) : (
          <ul className="divide-y">{pendentes.map(renderItem)}</ul>
        )}
      </section>

      {historico.length > 0 && (
        <section className="rounded-xl border bg-card shadow-xs">
          <header className="border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Histórico</h2>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs text-muted-foreground">
                <tr className="border-b">
                  <th className="px-4 py-2 text-left font-medium">Pedido em</th>
                  <th className="px-4 py-2 text-left font-medium">Quem pediu</th>
                  <th className="px-4 py-2 text-left font-medium">Pedido</th>
                  <th className="px-4 py-2 text-left font-medium">Detalhe</th>
                  <th className="px-4 py-2 text-left font-medium">Situação</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {historico.map((s) => {
                  const [rotulo, cor] = SITUACAO[s.status]
                  return (
                    <tr key={s.id} className="border-b last:border-0">
                      <td className="whitespace-nowrap px-4 py-2 text-xs text-muted-foreground">
                        {formatDate(s.criado_em)}
                      </td>
                      <td className="px-4 py-2 font-medium">{nomeDe(s.solicitante_id)}</td>
                      <td className="px-4 py-2">
                        {labelTipo(s.tipo)}
                        {s.convidado_por_id != null && <span className="text-muted-foreground"> · convite</span>}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">
                        {s.tipo === 'cessao'
                          ? `${s.eletronicos?.length ?? 0} equip. · CC ${s.centro_custo} → ${s.centro_custo_destino} · ${s.responsavel}`
                          : [
                              s.centro_custo && `CC ${s.centro_custo}`,
                              s.ocupacao_solicitada && `como ${s.ocupacao_solicitada}`,
                              s.cargo_solicitado && `cargo ${s.cargo_solicitado}`,
                            ]
                              .filter(Boolean)
                              .join(' ')}
                      </td>
                      <td className="px-4 py-2">
                        <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', cor)}>{rotulo}</span>
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex justify-end gap-1">
                          {s.tipo === 'cessao' && (
                            <Button size="sm" variant="ghost" asChild>
                              <Link href={`/solicitacoes/${s.id}/termo`}>
                                <FileText className="h-4 w-4" /> Termo
                              </Link>
                            </Button>
                          )}
                          {user?.tipo === 'Admin' && (
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-8 w-8 text-destructive"
                              onClick={() => cancelar(s.id)}
                              title="Excluir"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
