'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getContratos,
  createContrato,
  updateContrato,
  deleteContrato,
} from '@/lib/api/contratos'
import {
  getAssociacoesContrato,
  deleteAssociacaoContrato,
} from '@/lib/api/associacoes'
import { createEntradaCC } from '@/lib/api/solicitacoes'
import type {
  Contrato,
  AssociacaoUserContrato,
  Ocupacao,
} from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Pencil, Trash2, Users, LogOut, UserPlus } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { BarraSituacao, useResumoPor } from '@/components/app/distribuicao'

const OCUPACOES: Ocupacao[] = ['Gestor', 'Subgestor', 'Funcionario']

export default function CentrosDeCustoPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [assocs, setAssocs] = useState<AssociacaoUserContrato[]>([])
  const [search, setSearch] = useState('')
  const [filtroMeus, setFiltroMeus] = useState<'todos' | 'meus' | 'outros'>(
    'todos',
  )

  const [openNovo, setOpenNovo] = useState(false)
  const [novoCc, setNovoCc] = useState('')
  const [novaDesc, setNovaDesc] = useState('')

  const [editando, setEditando] = useState<Contrato | null>(null)
  const [editCc, setEditCc] = useState('')
  const [editDesc, setEditDesc] = useState('')

  const [openEntrada, setOpenEntrada] = useState<string | null>(null)
  const resumo = useResumoPor('centro_custo')
  const [cargoEntrada, setCargoEntrada] = useState<Ocupacao>('Funcionario')

  const load = () => {
    getContratos().then(setContratos).catch(() => {})
    getAssociacoesContrato().then(setAssocs).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const canCreate = user?.tipo === 'Admin' || user?.tipo === 'Gestor'
  const isAdminOuTI = user?.tipo === 'Admin' || user?.tipo === 'Tecnico_TI'

  const meusCCs = new Set(
    assocs.filter((a) => a.user_id === user?.id).map((a) => a.centro_custo),
  )

  const filtrados = contratos
    .filter((c) => {
      if (filtroMeus === 'meus') return meusCCs.has(c.centro_custo)
      if (filtroMeus === 'outros') return !meusCCs.has(c.centro_custo)
      return true
    })
    .filter((c) => {
      if (!search) return true
      const t = search.toLowerCase()
      return (
        c.centro_custo.toLowerCase().includes(t) ||
        c.descricao.toLowerCase().includes(t)
      )
    })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createContrato({ centro_custo: novoCc, descricao: novaDesc })
      toast.success('Centro de custo criado!')
      setOpenNovo(false)
      setNovoCc('')
      setNovaDesc('')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao criar.')
    }
  }

  function abrirEditar(c: Contrato) {
    setEditando(c)
    setEditCc(c.centro_custo)
    setEditDesc(c.descricao)
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    if (!editando) return
    const codigoMudou = editCc !== editando.centro_custo
    if (
      codigoMudou &&
      !confirm(
        `Alterar o código de "${editando.centro_custo}" para "${editCc}"? ` +
          'Isso vai atualizar todos os equipamentos, associações, ' +
          'cessões e solicitações desse CC.',
      )
    ) {
      return
    }
    try {
      await updateContrato(editando.centro_custo, {
        centro_custo: editCc,
        descricao: editDesc,
      })
      toast.success('Centro de custo atualizado!')
      setEditando(null)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  async function handleDelete(cc: string) {
    try {
      await deleteContrato(cc)
      toast.success('Removido!')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao remover.')
    }
  }

  async function handleSair(cc: string) {
    if (!user) return
    if (!confirm(`Sair do CC ${cc}?`)) return
    try {
      await deleteAssociacaoContrato(user.id, cc)
      toast.success(`Você saiu do CC ${cc}.`)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao sair.')
    }
  }

  async function handleEntrada(e: React.FormEvent) {
    e.preventDefault()
    if (!openEntrada) return
    try {
      await createEntradaCC({
        centro_custo: openEntrada,
        ocupacao_solicitada: cargoEntrada,
      })
      toast.success(
        `Solicitação enviada ao Gestor do CC ${openEntrada} como ${cargoEntrada}.`,
      )
      setOpenEntrada(null)
      setCargoEntrada('Funcionario')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao solicitar.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Centros de custo</h1>
          <p className="text-sm text-muted-foreground">
            Vêm da Receita. O gestor de cada CR aprova entradas e confere devoluções.
          </p>
        </div>
        {canCreate && (
          <Dialog open={openNovo} onOpenChange={setOpenNovo}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-1 h-4 w-4" /> Novo CC
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Novo Centro de Custo</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-3">
                <div className="space-y-1">
                  <Label>Código <RequiredMark /></Label>
                  <Input
                    value={novoCc}
                    onChange={(e) => setNovoCc(e.target.value.toUpperCase())}
                    required
                    maxLength={4}
                    placeholder="Ex.: TI01"
                  />
                  <p className="text-xs text-muted-foreground">Máximo 4 caracteres</p>
                </div>
                <div className="space-y-1">
                  <Label>Descrição <RequiredMark /></Label>
                  <Input
                    value={novaDesc}
                    onChange={(e) => setNovaDesc(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="w-full">
                  Criar
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar por código ou descrição…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Select
          value={filtroMeus}
          onValueChange={(v) => setFiltroMeus(v as typeof filtroMeus)}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os CCs</SelectItem>
            <SelectItem value="meus">Só os meus</SelectItem>
            <SelectItem value="outros">Que não faço parte</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-xs text-muted-foreground">
              <th className="px-4 py-2 text-left font-medium">CR</th>
              <th className="px-4 py-2 text-left font-medium">Descrição</th>
              <th className="px-4 py-2 text-left font-medium">Gestor</th>
              <th className="px-4 py-2 text-right font-medium">Equipamentos</th>
              <th className="px-4 py-2 text-right font-medium">Cedidos</th>
              <th className="w-44 px-4 py-2 text-left font-medium">Distribuição</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {filtrados.map((c) => {
              const minhaAssoc = assocs.find(
                (a) => a.centro_custo === c.centro_custo && a.user_id === user?.id,
              )
              const jaSou = minhaAssoc != null
              // Conta gestores apenas das associações que o usuário enxerga
              // (pra decidir 'único gestor' quando ele é o gestor)
              const gestoresVisiveis = assocs.filter(
                (a) => a.centro_custo === c.centro_custo && a.ocupacao === 'Gestor',
              )
              const ehUnicoGestor =
                minhaAssoc?.ocupacao === 'Gestor' && gestoresVisiveis.length === 1
              const podeEditar =
                user?.tipo === 'Admin' || minhaAssoc?.ocupacao === 'Gestor'
              const r = resumo(c.centro_custo)
              const verLista = () =>
                router.push(`/equipamentos?centro_custo=${encodeURIComponent(c.centro_custo)}`)

              return (
                <tr
                  key={c.centro_custo}
                  className="cursor-pointer border-b last:border-0 hover:bg-muted/40"
                  onClick={verLista}
                  title="Ver os equipamentos deste CR"
                >
                  <td className="px-4 py-2.5 font-mono">{c.centro_custo}</td>
                  <td className="px-4 py-2.5">{c.descricao}</td>
                  <td className="px-4 py-2.5">
                    {c.gestor_nome ?? '—'}
                    <span className="ml-1.5 inline-flex items-center gap-0.5 text-xs text-muted-foreground" title="Membros">
                      <Users className="h-3 w-3" />
                      {c.total_membros ?? 0}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums">{r.total}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums">{r.Externo}</td>
                  <td className="px-4 py-2.5">
                    <BarraSituacao c={r} />
                  </td>
                  <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      {jaSou ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs"
                          onClick={() => handleSair(c.centro_custo)}
                          disabled={ehUnicoGestor}
                          title={ehUnicoGestor ? 'Você é o único Gestor — nomeie outro antes de sair' : 'Sair do CC'}
                        >
                          <LogOut className="h-3.5 w-3.5" /> Sair
                        </Button>
                      ) : (
                        !isAdminOuTI && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => setOpenEntrada(c.centro_custo)}
                          >
                            <UserPlus className="h-3.5 w-3.5" /> Entrar
                          </Button>
                        )
                      )}
                      {podeEditar && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          onClick={() => abrirEditar(c)}
                          title="Editar CC"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {canCreate && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-destructive"
                          onClick={() => handleDelete(c.centro_custo)}
                          title="Excluir CC"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {filtrados.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  Nenhum resultado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Dialog
        open={editando !== null}
        onOpenChange={(o) => !o && setEditando(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar CC {editando?.centro_custo}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-3">
            <div className="space-y-1">
              <Label>Código <RequiredMark /></Label>
              <Input
                value={editCc}
                onChange={(e) => setEditCc(e.target.value.toUpperCase())}
                required
                maxLength={4}
                placeholder="Ex.: TI01"
              />
              <p className="text-xs text-muted-foreground">
                Máximo 4 caracteres. Mudar o código atualiza
                automaticamente equipamentos, associações, cessões e
                solicitações vinculados.
              </p>
            </div>
            <div className="space-y-1">
              <Label>Descrição <RequiredMark /></Label>
              <Input
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Salvar
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={openEntrada !== null}
        onOpenChange={(o) => !o && setOpenEntrada(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Solicitar entrada no CC {openEntrada}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEntrada} className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Sua solicitação será enviada ao Gestor do CC, que aprova ou
              rejeita.
            </p>
            <div className="space-y-1">
              <Label>Cargo desejado no CC <RequiredMark /></Label>
              <Select
                value={cargoEntrada}
                onValueChange={(v) => setCargoEntrada(v as Ocupacao)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OCUPACOES.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" className="w-full">
              Enviar solicitação
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
