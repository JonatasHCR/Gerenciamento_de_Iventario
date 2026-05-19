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
import type { Solicitacao } from '@/types/api'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'
import { Check, X, Trash2, FileText } from 'lucide-react'

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  pendente: 'secondary',
  aprovada: 'default',
  rejeitada: 'destructive',
}

export default function SolicitacoesPage() {
  const { user } = useAuth()
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([])

  const load = () => {
    getSolicitacoes().then(setSolicitacoes).catch(() => {})
  }

  useEffect(() => {
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

    return (
      <div key={s.id} className="flex items-start justify-between rounded-md border p-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Badge variant={STATUS_VARIANT[s.status]}>{s.status}</Badge>
            <span>{labelTipo(s.tipo)}</span>
          </div>
          {s.tipo === 'cessao' ? (
            <>
              <p className="text-sm text-muted-foreground">
                CC origem: <strong>{s.centro_custo}</strong>
                {' → CC destino: '}
                <strong>{s.centro_custo_destino}</strong>
              </p>
              <p className="text-sm">
                <strong>Responsável (recebe):</strong> {s.responsavel}
                {' · '}
                <span className="text-muted-foreground">
                  {s.eletronicos?.length ?? 0} equipamento(s)
                </span>
              </p>
              <Link href={`/solicitacoes/${s.id}/termo`}>
                <Button size="sm" variant="outline" className="mt-1">
                  <FileText className="mr-1 h-3 w-3" />
                  Ver termo
                </Button>
              </Link>
            </>
          ) : (
            <>
              {s.centro_custo && (
                <p className="text-sm text-muted-foreground">
                  CC: <strong>{s.centro_custo}</strong>
                  {s.ocupacao_solicitada && ` · ${s.ocupacao_solicitada}`}
                </p>
              )}
              {s.cargo_solicitado && (
                <p className="text-sm text-muted-foreground">
                  Cargo: <strong>{s.cargo_solicitado}</strong>
                </p>
              )}
            </>
          )}
          <p className="text-xs text-muted-foreground">
            Solicitante #{s.solicitante_id} · {formatDate(s.criado_em)}
            {isConvite && ' · convite'}
          </p>
        </div>
        <div className="flex gap-1 ml-4 shrink-0">
          {isPendente && canAprovar && (
            <>
              <Button size="icon" variant="ghost" className="h-7 w-7 text-green-600" onClick={() => aprovar(s.id)}>
                <Check className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => rejeitar(s.id)}>
                <X className="h-4 w-4" />
              </Button>
            </>
          )}
          {(isAdmin || (isPendente && isMinha)) && (
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7 text-destructive"
              onClick={() => cancelar(s.id)}
              title={isAdmin ? 'Excluir' : 'Cancelar'}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Solicitações</h1>

      <div>
        <h2 className="mb-3 font-semibold">Pendentes ({pendentes.length})</h2>
        {pendentes.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma solicitação pendente.</p>
        ) : (
          <div className="space-y-2">{pendentes.map(renderItem)}</div>
        )}
      </div>

      {historico.length > 0 && (
        <div>
          <h2 className="mb-3 font-semibold">Histórico</h2>
          <div className="space-y-2">{historico.map(renderItem)}</div>
        </div>
      )}
    </div>
  )
}
