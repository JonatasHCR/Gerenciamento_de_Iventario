'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  ArrowRight,
  BarChart3,
  Box,
  Check,
  ClipboardList,
  Undo2,
  Wrench,
} from 'lucide-react'
import { useAuth } from '@/context/auth-context'
import { getEletronicos } from '@/lib/api/eletronicos'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato, getAssociacoesEletronico } from '@/lib/api/associacoes'
import { getSolicitacoes } from '@/lib/api/solicitacoes'
import { getCessoes, getRecebimentosPendentesGestor, type Cessao } from '@/lib/api/cessoes'
import type { Eletronico, EletronicoStatus, Solicitacao } from '@/types/api'
import { Button } from '@/components/ui/button'
import { StatusCessao, ROTULO_STATUS } from '@/components/app/status'
import { formatDate } from '@/lib/utils'
import { SimboloTipo } from '@/components/app/icone-tipo'

const COR: Record<EletronicoStatus, string> = {
  Interno: 'bg-ok',
  Externo: 'bg-accent',
  'Em Manutenção': 'bg-primary',
}
const SITUACOES: EletronicoStatus[] = ['Interno', 'Externo', 'Em Manutenção']

const ROTULO_SOLICITACAO: Record<Solicitacao['tipo'], string> = {
  cessao: 'cessão',
  entrada_cc: 'entrada em CC',
  cargo_inicial: 'cargo',
}

export default function PainelPage() {
  const { user } = useAuth()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [ccsTotais, setCcsTotais] = useState(0)
  const [meusEletronicosIds, setMeusEletronicosIds] = useState<number[]>([])
  const [meusCCs, setMeusCCs] = useState<string[]>([])
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([])
  const [recebimentos, setRecebimentos] = useState(0)
  const [cessoes, setCessoes] = useState<Cessao[]>([])
  const [nomeCC, setNomeCC] = useState<Record<string, string>>({})
  const [cessoesCarregadas, setCessoesCarregadas] = useState(false)
  const router = useRouter()

  useEffect(() => {
    if (!user) return
    getEletronicos().then(setEletronicos).catch(() => {})
    getContratos()
      .then((l) => {
        setCcsTotais(l.length)
        setNomeCC(Object.fromEntries(l.map((c) => [c.centro_custo, c.descricao])))
      })
      .catch(() => {})
    getAssociacoesContrato()
      .then((list) => setMeusCCs(list.filter((a) => a.user_id === user.id).map((a) => a.centro_custo)))
      .catch(() => {})
    getAssociacoesEletronico()
      .then((list) =>
        setMeusEletronicosIds(list.filter((a) => a.user_id === user.id).map((a) => a.eletronico_id)),
      )
      .catch(() => {})
    getSolicitacoes().then(setSolicitacoes).catch(() => {})
    getRecebimentosPendentesGestor().then((r) => setRecebimentos(r.count)).catch(() => {})
    getCessoes()
      .then(setCessoes)
      .catch(() => {})
      .finally(() => setCessoesCarregadas(true))
  }, [user])

  const isFuncionario = user?.tipo === 'Funcionario'
  const isGestor = user?.tipo === 'Subgestor' || user?.tipo === 'Gestor'

  // Mesma regra de antes: funcionário vê os seus; gestor, os dos seus CCs.
  const visiveis = useMemo(
    () =>
      isFuncionario
        ? eletronicos.filter((e) => meusEletronicosIds.includes(e.id))
        : isGestor
          ? eletronicos.filter((e) => meusCCs.includes(e.centro_custo))
          : eletronicos,
    [eletronicos, isFuncionario, isGestor, meusEletronicosIds, meusCCs],
  )

  const contagem = useMemo(() => {
    const c: Record<EletronicoStatus, number> = { Interno: 0, Externo: 0, 'Em Manutenção': 0 }
    visiveis.forEach((e) => (c[e.status] = (c[e.status] ?? 0) + 1))
    return c
  }, [visiveis])

  const porTipo = useMemo(() => {
    const m = new Map<string, Record<EletronicoStatus, number>>()
    visiveis.forEach((e) => {
      const t = m.get(e.tipo) ?? { Interno: 0, Externo: 0, 'Em Manutenção': 0 }
      t[e.status] += 1
      m.set(e.tipo, t)
    })
    return [...m.entries()]
      .map(([tipo, c]) => ({ tipo, c, total: c.Interno + c.Externo + c['Em Manutenção'] }))
      .sort((a, b) => b.total - a.total)
  }, [visiveis])

  const total = visiveis.length
  const maiorTipo = Math.max(1, ...porTipo.map((t) => t.total))
  const pendentes = solicitacoes.filter((s) => s.status === 'pendente')
  const emManutencao = visiveis.filter((e) => e.status === 'Em Manutenção')
  const abertas = cessoes.filter((c) => c.status !== 'devolvida')
  const recentes = [...cessoes].sort((a, b) => b.cedido_em.localeCompare(a.cedido_em)).slice(0, 6)
  const emCessaoAberta = new Set(
    abertas.flatMap((c) => c.eletronicos.filter((e) => e.devolvido_em === null).map((e) => e.id)),
  )
  const semTermo = cessoesCarregadas ? visiveis.filter((e) => e.status === 'Externo' && !emCessaoAberta.has(e.id)) : []
  const atencao = pendentes.length + recebimentos
  const ccs = isFuncionario || isGestor ? meusCCs.length : ccsTotais

  const kpis: { titulo: string; valor: number; sub: string; href: string; Icone: typeof Box }[] = [
    { titulo: 'Equipamentos', valor: total, sub: `em ${ccs} centro(s) de custo`, href: '/equipamentos', Icone: Box },
    { titulo: 'Internos', valor: contagem.Interno, sub: 'no patrimônio, prontos para uso', href: '/equipamentos?status=Interno', Icone: Check },
    { titulo: 'Cedidos', valor: contagem.Externo, sub: `em ${abertas.length} cessão(ões) aberta(s)`, href: '/equipamentos?status=Externo', Icone: ArrowRight },
    { titulo: 'Em manutenção', valor: contagem['Em Manutenção'], sub: 'fora de uso', href: '/equipamentos?status=Em%20Manuten%C3%A7%C3%A3o', Icone: Wrench },
  ]

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Painel</h1>
          <p className="text-sm text-muted-foreground">
            {user ? `Olá, ${user.nome.split(' ')[0]}. ` : ''}
            {atencao ? `${atencao} coisa(s) pedem sua atenção.` : 'Nada esperando por você agora.'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/relatorios">
              <BarChart3 className="h-4 w-4" /> Relatório
            </Link>
          </Button>
          {!isFuncionario && (
            <Button asChild>
              <Link href="/equipamentos/ceder">
                <ArrowRight className="h-4 w-4" /> Ceder equipamentos
              </Link>
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {kpis.map(({ titulo, valor, sub, href, Icone }) => (
          <Link
            key={titulo}
            href={href}
            className="group rounded-xl border bg-card p-4 shadow-xs transition-colors hover:border-ring"
          >
            <div className="flex items-center justify-between text-sm font-medium text-muted-foreground">
              {titulo}
              <Icone className="h-4 w-4" />
            </div>
            <div className="mt-1 text-3xl font-bold tabular-nums tracking-tight">{valor}</div>
            <p className="text-xs text-muted-foreground">{sub}</p>
          </Link>
        ))}
      </div>

      {total > 0 && (
        <div className="space-y-2.5 rounded-xl border bg-card p-4 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold">Situação do inventário</p>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              {SITUACOES.map((s) => (
                <span key={s} className="inline-flex items-center gap-1.5">
                  <i className={`size-2.5 rounded-sm ${COR[s]}`} />
                  {ROTULO_STATUS[s]} · {Math.round((contagem[s] / total) * 100)}%
                </span>
              ))}
            </div>
          </div>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
            {SITUACOES.map((s) => (
              <div
                key={s}
                className={COR[s]}
                style={{ width: `${(contagem[s] / total) * 100}%` }}
                title={`${ROTULO_STATUS[s]}: ${contagem[s]}`}
              />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <section className="rounded-xl border bg-card shadow-xs">
          <header className="flex items-baseline gap-2 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Pede atenção</h2>
            <span className="text-xs text-muted-foreground">o que está esperando alguém</span>
          </header>
          <ul className="divide-y">
            {pendentes.length > 0 && (
              <ItemAtencao
                Icone={ClipboardList}
                cor="bg-warn-bg text-warn"
                titulo={`${pendentes.length} solicitação(ões) pendente(s)`}
                sub={[...new Set(pendentes.map((s) => ROTULO_SOLICITACAO[s.tipo]))].join(', ')}
                href="/solicitacoes"
                acao="Responder"
              />
            )}
            {recebimentos > 0 && (
              <ItemAtencao
                Icone={Undo2}
                cor="bg-info-bg text-info"
                titulo={`${recebimentos} recebimento(s) de devolução para conferir`}
                sub="equipamentos que voltaram para os seus CCs"
                href="/cessoes?aba=recebimentos"
                acao="Conferir"
              />
            )}
            {emManutencao.length > 0 && (
              <ItemAtencao
                Icone={Wrench}
                cor="bg-crit-bg text-destructive"
                titulo={`${emManutencao.length} em manutenção`}
                sub={emManutencao.slice(0, 3).map((e) => e.nome).join(', ') + (emManutencao.length > 3 ? '…' : '')}
                href="/equipamentos?status=Em%20Manuten%C3%A7%C3%A3o"
                acao="Ver"
              />
            )}
            {!pendentes.length && !recebimentos && !emManutencao.length && (
              <li className="px-4 py-8 text-center text-sm text-muted-foreground">Tudo em dia.</li>
            )}
          </ul>
        </section>

        <section className="rounded-xl border bg-card shadow-xs">
          <header className="flex items-baseline gap-2 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">Por tipo</h2>
            <span className="text-xs text-muted-foreground">clique para ver a lista</span>
          </header>
          <div className="space-y-0.5 p-2">
            {porTipo.length === 0 && (
              <p className="px-2 py-6 text-center text-sm text-muted-foreground">Nenhum equipamento encontrado.</p>
            )}
            {porTipo.map(({ tipo, c, total: n }) => (
              <Link
                key={tipo}
                href={`/equipamentos?tipo=${encodeURIComponent(tipo)}`}
                className="grid grid-cols-[8.5rem_1fr_2.5rem] items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <SimboloTipo tipo={tipo} className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate">{tipo}</span>
                </span>
                <span className="flex h-2 overflow-hidden rounded-full bg-muted">
                  {SITUACOES.map((s) => (
                    <i key={s} className={COR[s]} style={{ width: `${(c[s] / maiorTipo) * 100}%` }} />
                  ))}
                </span>
                <span className="text-right font-semibold tabular-nums">{n}</span>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border bg-card shadow-xs">
          <header className="flex items-center justify-between border-b px-4 py-3">
            <div className="flex items-baseline gap-2">
              <h2 className="text-sm font-semibold">Cessões recentes</h2>
              <span className="text-xs text-muted-foreground">
                {abertas.length} aberta(s) · {cessoes.length - abertas.length} devolvida(s)
              </span>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/cessoes">
                Ver todas <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </header>
          {semTermo.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-warn-bg px-4 py-2.5 text-sm">
              <span>
                <strong className="text-warn">{semTermo.length} cedido(s) sem cessão registrada</strong>
                <span className="text-muted-foreground"> · sem termo nem recebimento</span>
              </span>
              <Button size="sm" variant="outline" asChild>
                <Link href="/cessoes">Regularizar</Link>
              </Button>
            </div>
          )}
          {recentes.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-muted-foreground">
              Nenhuma cessão registrada ainda. Quando equipamentos forem cedidos, aparecem aqui com o termo.
            </p>
          ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-xs text-muted-foreground">
                  <th className="px-4 py-2 text-left font-medium">Cessão</th>
                  <th className="px-4 py-2 text-left font-medium">Responsável</th>
                  <th className="px-4 py-2 text-left font-medium">Destino</th>
                  <th className="px-4 py-2 text-left font-medium">Cedida em</th>
                  <th className="px-4 py-2 text-left font-medium">Itens</th>
                  <th className="px-4 py-2 text-left font-medium">Situação</th>
                </tr>
              </thead>
              <tbody>
                {recentes.map((c) => (
                  <tr
                    key={c.id}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/40"
                    onClick={() => router.push(`/cessoes?id=${c.id}`)}
                  >
                    <td className="px-4 py-2 font-mono">
                      <Link href={`/cessoes?id=${c.id}`} className="hover:underline">#{c.id}</Link>
                    </td>
                    <td className="px-4 py-2">{c.responsavel}</td>
                    <td className="px-4 py-2">
                      CC {c.centro_custo_destino}
                      {nomeCC[c.centro_custo_destino] && (
                        <span className="text-muted-foreground"> · {nomeCC[c.centro_custo_destino]}</span>
                      )}
                    </td>
                    <td className="px-4 py-2 tabular-nums">{formatDate(c.cedido_em).slice(0, 10)}</td>
                    <td className="px-4 py-2 tabular-nums">{c.total_eletronicos}</td>
                    <td className="px-4 py-2">
                      <StatusCessao
                        status={c.status}
                        detalhe={c.status === 'parcial' ? `${c.total_devolvidos}/${c.total_eletronicos}` : undefined}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </section>
    </div>
  )
}

function ItemAtencao({
  Icone,
  cor,
  titulo,
  sub,
  href,
  acao,
}: {
  Icone: typeof Box
  cor: string
  titulo: string
  sub: string
  href: string
  acao: string
}) {
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${cor}`}>
        <Icone className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <b className="block text-sm font-semibold">{titulo}</b>
        <span className="block truncate text-xs text-muted-foreground">{sub}</span>
      </span>
      <Button size="sm" variant="outline" asChild>
        <Link href={href}>{acao}</Link>
      </Button>
    </li>
  )
}
