'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import { getEletronicos } from '@/lib/api/eletronicos'
import { createCessao } from '@/lib/api/cessoes'
import { createSolicitacaoCessao } from '@/lib/api/solicitacoes'
import { getContratos } from '@/lib/api/contratos'
import { getAssociacoesContrato } from '@/lib/api/associacoes'
import type { Eletronico, Contrato } from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { SearchableSelect } from '@/components/app/searchable-select'
import { ArrowLeft, FileText, Send } from 'lucide-react'
import Link from 'next/link'

export default function CederPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [eletronicos, setEletronicos] = useState<Eletronico[]>([])
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [meusCCsGestor, setMeusCCsGestor] = useState<string[]>([])
  const [meusCCsSubgestor, setMeusCCsSubgestor] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [filtroCC, setFiltroCC] = useState('todos')
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set())
  const [responsavel, setResponsavel] = useState('')
  const [ccDestino, setCcDestino] = useState('')
  const [dataCessao, setDataCessao] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const isAdmin = user?.tipo === 'Admin'
  const isTI = user?.tipo === 'Tecnico_TI'
  const hasFullAccess = isAdmin || isTI
  const isSubgestorOnly =
    !hasFullAccess &&
    meusCCsGestor.length === 0 &&
    meusCCsSubgestor.length > 0

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
        }
      })
      .catch(() => {})
    getEletronicos().then(setEletronicos).catch(() => {})
    getContratos().then(setContratos).catch(() => {})
  }, [user, hasFullAccess, router])

  const meusCCsOperaveis = useMemo(
    () => [...meusCCsGestor, ...meusCCsSubgestor],
    [meusCCsGestor, meusCCsSubgestor],
  )

  const ccsDisponiveis = useMemo(() => {
    return hasFullAccess
      ? contratos.map((c) => c.centro_custo)
      : meusCCsOperaveis
  }, [hasFullAccess, contratos, meusCCsOperaveis])

  const filtrados = useMemo(() => {
    const term = search.toLowerCase()
    return eletronicos
      .filter((e) => e.status === 'Interno')
      .filter(
        (e) => hasFullAccess || meusCCsOperaveis.includes(e.centro_custo),
      )
      .filter((e) => filtroCC === 'todos' || e.centro_custo === filtroCC)
      .filter(
        (e) =>
          !term ||
          e.nome.toLowerCase().includes(term) ||
          e.numero_serie.toLowerCase().includes(term) ||
          e.numero_patrimonio.toLowerCase().includes(term),
      )
  }, [eletronicos, search, filtroCC, hasFullAccess, meusCCsOperaveis])

  function toggle(id: number) {
    setSelecionados((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  function toggleAll() {
    if (filtrados.every((e) => selecionados.has(e.id))) {
      setSelecionados((s) => {
        const n = new Set(s)
        filtrados.forEach((e) => n.delete(e.id))
        return n
      })
    } else {
      setSelecionados((s) => {
        const n = new Set(s)
        filtrados.forEach((e) => n.add(e.id))
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
    const itensSelecionados = eletronicos.filter((el) => ids.includes(el.id))
    setSubmitting(true)
    try {
      if (isSubgestorOnly) {
        // Subgestor: precisa ser um único CC de origem (Subgestor seu).
        const ccsOrigem = new Set(itensSelecionados.map((e) => e.centro_custo))
        if (ccsOrigem.size !== 1) {
          toast.error(
            'Selecione equipamentos de apenas um CC de origem.',
          )
          setSubmitting(false)
          return
        }
        const cc = [...ccsOrigem][0]
        if (!meusCCsSubgestor.includes(cc)) {
          toast.error(
            'Você só pode solicitar cessão dos CCs em que é Subgestor.',
          )
          setSubmitting(false)
          return
        }
        await createSolicitacaoCessao({
          eletronico_ids: ids,
          responsavel,
          centro_custo_destino: ccDestino,
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
      })
      toast.success('Cessão registrada! Abrindo termo…')
      router.push(`/cessoes/${cessao.id}/termo`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao ceder.')
    } finally {
      setSubmitting(false)
    }
  }

  const todosMarcados =
    filtrados.length > 0 && filtrados.every((e) => selecionados.has(e.id))

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

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          className={
            isSubgestorOnly
              ? 'grid grid-cols-1 gap-3 sm:grid-cols-2'
              : 'grid grid-cols-1 gap-3 sm:grid-cols-3'
          }
        >
          <div className="space-y-1">
            <Label>Responsável (recebedor)</Label>
            <Input
              value={responsavel}
              onChange={(e) => setResponsavel(e.target.value)}
              placeholder="Nome completo"
              required
            />
          </div>
          <div className="space-y-1">
            <Label>Centro de Custo destino</Label>
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
              <p className="text-xs text-muted-foreground">
                Em branco usa hoje
              </p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Input
            placeholder="Buscar por nome, série ou patrimônio…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <SearchableSelect
            value={filtroCC}
            onChange={setFiltroCC}
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
              {filtrados.map((e) => (
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
              ))}
              {filtrados.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                    Nenhum equipamento interno disponível.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between rounded-md border bg-card p-3">
          <p className="text-sm">
            <strong>{selecionados.size}</strong> equipamento(s) selecionado(s)
          </p>
          <Button
            type="submit"
            disabled={
              submitting ||
              selecionados.size === 0 ||
              !responsavel ||
              !ccDestino
            }
          >
            {isSubgestorOnly ? (
              <Send className="mr-2 h-4 w-4" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            {submitting
              ? 'Processando…'
              : isSubgestorOnly
                ? 'Enviar solicitação ao Gestor'
                : 'Ceder e gerar termo'}
          </Button>
        </div>
      </form>
    </div>
  )
}
