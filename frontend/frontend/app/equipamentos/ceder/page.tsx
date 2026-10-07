'use client'

import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import { getEletronicos, getEletronicosPaginated } from '@/lib/api/eletronicos'
import { createCessao, type Periferico } from '@/lib/api/cessoes'
import { createSolicitacaoCessao } from '@/lib/api/solicitacoes'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import type { Eletronico, Contrato } from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import { Badge } from '@/components/ui/badge'
import { SearchableSelect } from '@/components/app/searchable-select'
import { ArrowLeft, ArrowRight, Check, FileText, Send, Plus, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import Link from 'next/link'

function CederConteudo() {
  const { user } = useAuth()
  const router = useRouter()
  const busca = useSearchParams()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loadingTable, setLoadingTable] = useState(false)
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [meusCCsGestor, setMeusCCsGestor] = useState<string[]>([])
  const [meusCCsSubgestor, setMeusCCsSubgestor] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [filtroCC, setFiltroCC] = useState('todos')
  // Vindo da lista de equipamentos (?ids=1,2,3), a seleção já chega marcada.
  const [selecionados, setSelecionados] = useState<Set<number>>(
    () =>
      new Set(
        (busca.get('ids') ?? '')
          .split(',')
          .map(Number)
          .filter((n) => n > 0),
      ),
  )
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [responsavel, setResponsavel] = useState('')
  const [ccDestino, setCcDestino] = useState('')
  const [dataCessao, setDataCessao] = useState('')
  const [perifericos, setPerifericos] = useState<Periferico[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [passo, setPasso] = useState(() => (busca.get('ids') ? 1 : 0))
  const [revisao, setRevisao] = useState<Eletronico[]>([])
  const [ready, setReady] = useState(false)

  const isAdmin = user?.tipo === 'Admin'
  const isTI = user?.tipo === 'Tecnico_TI'
  const hasFullAccess = isAdmin || isTI
  const isSubgestorOnly =
    !hasFullAccess &&
    meusCCsGestor.length === 0 &&
    meusCCsSubgestor.length > 0

  // Carrega associações e contratos uma única vez
  useEffect(() => {
    if (!user) return
    getAssociacoesContrato()
      .then((list) => {
        const mine = list.filter((a) => a.user_id === user.id)
        const gestor = mine
          .filter((a) => a.ocupacao === 'Gestor')
          .map((a) => a.centro_custo)
        const sub = mine
          .filter((a) => a.ocupacao === 'Subgestor')
          .map((a) => a.centro_custo)
        setMeusCCsGestor(gestor)
        setMeusCCsSubgestor(sub)
        if (!hasFullAccess && gestor.length === 0 && sub.length === 0) {
          router.replace('/equipamentos')
          return
        }
        setReady(true)
      })
      .catch(() => {})
    getContratos().then(setContratos).catch(() => {})
    if (hasFullAccess) setReady(true)
  }, [user, hasFullAccess, router])

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function handleSearch(value: string) {
    setSearch(value)
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setPage(1)
      fetchPage(1, pageSize, value, filtroCC)
    }, 300)
  }

  function handleFiltroCC(value: string) {
    setFiltroCC(value)
    setPage(1)
    fetchPage(1, pageSize, search, value)
  }

  function handlePageSize(value: number) {
    setPageSize(value)
    setPage(1)
    fetchPage(1, value, search, filtroCC)
  }

  function handlePage(next: number) {
    setPage(next)
    fetchPage(next, pageSize, search, filtroCC)
  }

  async function fetchPage(
    p: number,
    ps: number,
    q: string,
    cc: string,
  ) {
    setLoadingTable(true)
    try {
      const res = await getEletronicosPaginated({
        status: ['Interno'],
        q: q.trim() || undefined,
        centro_custo: cc !== 'todos' ? [cc] : undefined,
        page: p,
        page_size: ps,
      })
      setEletronicos(res.eletronicos)
      setTotal(res.total)
      setTotalPages(res.pages)
    } catch {
      toast.error('Erro ao carregar equipamentos.')
    } finally {
      setLoadingTable(false)
    }
  }

  // Busca inicial quando o usuário está pronto
  useEffect(() => {
    if (!ready) return
    fetchPage(page, pageSize, search, filtroCC)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  const meusCCsOperaveis = useMemo(
    () => [...meusCCsGestor, ...meusCCsSubgestor],
    [meusCCsGestor, meusCCsSubgestor],
  )

  const ccsDisponiveis = useMemo(() => {
    return hasFullAccess
      ? contratos.map((c) => c.centro_custo)
      : meusCCsOperaveis
  }, [hasFullAccess, contratos, meusCCsOperaveis])

  function addPeriferico() {
    setPerifericos((p) => [...p, { nome: '', quantidade: 1 }])
  }

  function updatePeriferico(
    idx: number,
    patch: Partial<Periferico>,
  ) {
    setPerifericos((p) =>
      p.map((item, i) => (i === idx ? { ...item, ...patch } : item)),
    )
  }

  function removePeriferico(idx: number) {
    setPerifericos((p) => p.filter((_, i) => i !== idx))
  }

  function toggle(id: number) {
    setSelecionados((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  function toggleAll() {
    if (eletronicos.every((e) => selecionados.has(e.id))) {
      setSelecionados((s) => {
        const n = new Set(s)
        eletronicos.forEach((e) => n.delete(e.id))
        return n
      })
    } else {
      setSelecionados((s) => {
        const n = new Set(s)
        eletronicos.forEach((e) => n.add(e.id))
        return n
      })
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (selecionados.size === 0) {
      toast.error('Selecione ao menos um equipamento.')
      return
    }
    const ids = Array.from(selecionados)
    const perifericosLimpos = perifericos
      .map((p) => ({ nome: p.nome.trim(), quantidade: p.quantidade }))
      .filter((p) => p.nome !== '')
    setSubmitting(true)
    try {
      if (isSubgestorOnly) {
        await createSolicitacaoCessao({
          eletronico_ids: ids,
          responsavel,
          centro_custo_destino: ccDestino,
          perifericos: perifericosLimpos,
        })
        toast.success('Solicitação enviada ao Gestor.')
        router.push('/solicitacoes')
        return
      }

      const cessao = await createCessao({
        eletronico_ids: ids,
        responsavel,
        centro_custo_destino: ccDestino,
        cedido_em: dataCessao
          ? new Date(dataCessao + 'T12:00:00').toISOString()
          : null,
        perifericos: perifericosLimpos,
      })
      toast.success('Cessão registrada! Abrindo termo…')
      router.push(`/cessoes/${cessao.id}/termo`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao ceder.')
    } finally {
      setSubmitting(false)
    }
  }

  const PASSOS = ['Equipamentos', 'Destino', 'Periféricos', 'Revisão']
  const gestorDestino = contratos.find((c) => c.centro_custo === ccDestino)?.gestor_nome
  const podeAvancar =
    passo === 0 ? selecionados.size > 0 : passo === 1 ? !!responsavel.trim() && !!ccDestino : true

  function avancar() {
    const proximo = passo + 1
    setPasso(proximo)
    // Os marcados podem ser de outras páginas: a revisão busca todos de uma vez.
    if (proximo === 3) {
      setRevisao([])
      getEletronicos()
        .then((todos) => setRevisao(todos.filter((e) => selecionados.has(e.id))))
        .catch(() => {})
    }
  }

  const todosMarcados =
    eletronicos.length > 0 && eletronicos.every((e) => selecionados.has(e.id))

  const inicioItem = total === 0 ? 0 : (page - 1) * pageSize + 1
  const fimItem = Math.min(page * pageSize, total)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Link href="/equipamentos">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">
          {isSubgestorOnly ? 'Solicitar cessão de equipamentos' : 'Ceder equipamentos'}
        </h1>
      </div>
      {isSubgestorOnly && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Como <strong>Subgestor</strong>, esta tela envia uma solicitação ao{' '}
          <strong>Gestor</strong> do CC. A cessão só é efetivada após aprovação.
          Selecione equipamentos de um único CC de origem.
        </div>
      )}

      <form
        // Enter num campo não pode pular a revisão: antes do último passo ele só avança.
        onSubmit={(ev) => {
          if (passo < 3) {
            ev.preventDefault()
            if (podeAvancar) avancar()
            return
          }
          handleSubmit(ev)
        }}
        className="space-y-4"
      >
        <ol className="flex flex-wrap gap-x-5 gap-y-2 border-b pb-3 text-sm">
          {PASSOS.map((nome, i) => (
            <li
              key={nome}
              className={cn(
                'flex items-center gap-2 text-muted-foreground',
                i === passo && 'font-medium text-foreground',
              )}
            >
              <span
                className={cn(
                  'grid size-6 place-items-center rounded-full bg-muted text-xs font-bold',
                  i === passo && 'bg-primary text-primary-foreground',
                  i < passo && 'bg-ok text-white',
                )}
              >
                {i < passo ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </span>
              {nome}
              {i === 0 && selecionados.size > 0 && ` (${selecionados.size})`}
            </li>
          ))}
        </ol>

        {passo === 0 && (
          <>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Input
              placeholder="Buscar por nome, série ou patrimônio…"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
            />
            <SearchableSelect
              value={filtroCC}
              onChange={handleFiltroCC}
              options={[
                { value: 'todos', label: 'Todos os CCs disponíveis' },
                ...ccsDisponiveis.map((cc) => ({ value: cc, label: cc })),
              ]}
            />
          </div>

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[600px] text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="w-10 px-3 py-2">
                    <input
                      type="checkbox"
                      checked={todosMarcados}
                      onChange={toggleAll}
                      className="h-4 w-4"
                    />
                  </th>
                  <th className="px-3 py-2 text-left font-medium">Equipamento</th>
                  <th className="px-3 py-2 text-left font-medium">Nº Série</th>
                  <th className="px-3 py-2 text-left font-medium">Patrimônio</th>
                  <th className="px-3 py-2 text-left font-medium">CC</th>
                </tr>
              </thead>
              <tbody>
                {loadingTable ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                      Carregando…
                    </td>
                  </tr>
                ) : eletronicos.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                      Nenhum equipamento interno disponível.
                    </td>
                  </tr>
                ) : (
                  eletronicos.map((e) => (
                    <tr
                      key={e.id}
                      className="cursor-pointer border-b last:border-0 hover:bg-muted/30"
                      onClick={() => toggle(e.id)}
                    >
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={selecionados.has(e.id)}
                          onChange={() => toggle(e.id)}
                          onClick={(ev) => ev.stopPropagation()}
                          className="h-4 w-4"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <p className="font-medium">{e.nome}</p>
                        <p className="text-xs text-muted-foreground">{e.tipo}</p>
                      </td>
                      <td className="px-3 py-2">{e.numero_serie}</td>
                      <td className="px-3 py-2">{e.numero_patrimonio}</td>
                      <td className="px-3 py-2">
                        <Badge variant="outline">{e.centro_custo}</Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Paginação */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-muted-foreground">
              {total === 0
                ? 'Nenhum resultado'
                : `${inicioItem}–${fimItem} de ${total}`}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handlePage(Math.max(1, page - 1))}
                disabled={page === 1 || loadingTable}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40 hover:bg-muted"
              >
                ‹ Anterior
              </button>
              <span className="text-xs text-muted-foreground">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => handlePage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages || loadingTable}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40 hover:bg-muted"
              >
                Próxima ›
              </button>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Itens/pág.:</span>
              <select
                value={pageSize}
                onChange={(e) => handlePageSize(Number(e.target.value))}
                className="rounded border bg-background px-1.5 py-1 text-xs"
              >
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>
          </>
        )}

        {passo === 1 && (
          <>
          <div
            className={
              isSubgestorOnly
                ? 'grid grid-cols-1 gap-3 sm:grid-cols-2'
                : 'grid grid-cols-1 gap-3 sm:grid-cols-3'
            }
          >
            <div className="space-y-1">
              <Label>Responsável (recebedor) <RequiredMark /></Label>
              <Input
                value={responsavel}
                onChange={(e) => setResponsavel(e.target.value)}
                placeholder="Nome completo"
                required
              />
            </div>
            <div className="space-y-1">
              <Label>Centro de Custo destino <RequiredMark /></Label>
              <SearchableSelect
                value={ccDestino}
                onChange={setCcDestino}
                options={contratos.map((c) => ({
                  value: c.centro_custo,
                  label: `${c.centro_custo} — ${c.descricao}`,
                }))}
                placeholder="Selecione o CC destino"
              />
            </div>
            {!isSubgestorOnly && (
              <div className="space-y-1">
                <Label>Data da cessão</Label>
                <Input
                  type="date"
                  value={dataCessao}
                  onChange={(e) => setDataCessao(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Em branco usa hoje</p>
              </div>
            )}
          </div>
            {gestorDestino && (
              <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
                O gestor do CC {ccDestino}, <strong className="text-foreground">{gestorDestino}</strong>,
                fica responsável por conferir a devolução depois.
              </p>
            )}
          </>
        )}

        {passo === 2 && (
          <div className="space-y-2 rounded-md border bg-card p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Periféricos avulsos</p>
                  <p className="text-xs text-muted-foreground">
                    Mouse, teclado, kit teclado+mouse, etc. — sem patrimônio,
                    fora do controle de inventário, apenas para constar no termo.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addPeriferico}
                >
                  <Plus className="mr-1 h-4 w-4" /> Adicionar
                </Button>
              </div>
              {perifericos.length > 0 && (
                <div className="space-y-2">
                  {perifericos.map((p, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Input
                        value={p.nome}
                        onChange={(e) =>
                          updatePeriferico(idx, { nome: e.target.value })
                        }
                        placeholder="Ex.: Mouse, Teclado, Kit teclado e mouse"
                        className="flex-1"
                      />
                      <Input
                        type="number"
                        min={1}
                        value={p.quantidade}
                        onChange={(e) =>
                          updatePeriferico(idx, {
                            quantidade: Math.max(1, Number(e.target.value) || 1),
                          })
                        }
                        className="w-20"
                        title="Quantidade"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 shrink-0 text-destructive"
                        onClick={() => removePeriferico(idx)}
                        title="Remover"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
          </div>
        )}

        {passo === 3 && (
          <div className="space-y-4">
            <dl className="grid grid-cols-[9rem_1fr] gap-x-3 gap-y-2 rounded-md border bg-card p-4 text-sm">
              <dt className="text-muted-foreground">Responsável</dt>
              <dd>{responsavel}</dd>
              <dt className="text-muted-foreground">CC de destino</dt>
              <dd>
                {ccDestino}
                {contratos.find((c) => c.centro_custo === ccDestino)?.descricao &&
                  ` · ${contratos.find((c) => c.centro_custo === ccDestino)?.descricao}`}
              </dd>
              {!isSubgestorOnly && (
                <>
                  <dt className="text-muted-foreground">Data</dt>
                  <dd>{dataCessao ? dataCessao.split('-').reverse().join('/') : 'hoje'}</dd>
                </>
              )}
              <dt className="text-muted-foreground">Periféricos</dt>
              <dd>
                {perifericos.filter((x) => x.nome.trim()).map((x) => `${x.quantidade} ${x.nome}`).join(', ') ||
                  'nenhum'}
              </dd>
            </dl>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-2 text-left font-medium">Patrimônio</th>
                    <th className="px-3 py-2 text-left font-medium">Equipamento</th>
                    <th className="px-3 py-2 text-left font-medium">Nº Série</th>
                    <th className="px-3 py-2 text-left font-medium">CC</th>
                  </tr>
                </thead>
                <tbody>
                  {revisao.map((e) => (
                    <tr key={e.id} className="border-b last:border-0">
                      <td className="px-3 py-2 font-mono">{e.numero_patrimonio}</td>
                      <td className="px-3 py-2">{e.nome}</td>
                      <td className="px-3 py-2 font-mono text-xs">{e.numero_serie}</td>
                      <td className="px-3 py-2">{e.centro_custo}</td>
                    </tr>
                  ))}
                  {revisao.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                        Carregando os equipamentos marcados…
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              {isSubgestorOnly
                ? 'Ao enviar, o Gestor do CC recebe a solicitação para aprovar.'
                : 'Ao confirmar, o sistema registra a cessão e abre o termo para assinatura.'}
            </p>
          </div>
        )}

        <div className="sticky bottom-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border bg-card p-3 shadow-sm">
          <Button type="button" variant="outline" disabled={passo === 0} onClick={() => setPasso((n) => n - 1)}>
            <ArrowLeft className="h-4 w-4" /> Voltar
          </Button>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">
              <strong className="text-foreground">{selecionados.size}</strong> equipamento(s)
            </span>
            {passo < 3 ? (
              <Button type="button" disabled={!podeAvancar} onClick={avancar}>
                Continuar <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="submit" disabled={submitting || selecionados.size === 0 || !responsavel || !ccDestino}>
                {isSubgestorOnly ? <Send className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                {submitting
                  ? 'Processando…'
                  : isSubgestorOnly
                    ? 'Enviar solicitação ao Gestor'
                    : 'Ceder e gerar termo'}
              </Button>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

export default function CederPage() {
  return (
    <Suspense fallback={null}>
      <CederConteudo />
    </Suspense>
  )
}
