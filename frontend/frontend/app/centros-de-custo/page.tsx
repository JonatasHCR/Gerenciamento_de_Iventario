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

const OCUPACOES: Ocupacao[] = ['Gestor', 'Subgestor', 'Funcionario']

export default function CentrosDeCustoPage() {
  const { user } = useAuth()
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Centros de Custo</h1>
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

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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

          return (
            <div
              key={c.centro_custo}
              className="rounded-lg border bg-card p-4 space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold">{c.centro_custo}</p>
                  <p className="text-sm text-muted-foreground">
                    {c.descricao}
                  </p>
                </div>
                <div className="flex gap-1">
                  {podeEditar && (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => abrirEditar(c)}
                      title="Editar CC"
                    >
                      <Pencil className="h-4 w-4" />
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
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between border-t pt-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Gestor</p>
                  <p className="font-medium">{c.gestor_nome ?? '—'}</p>
                </div>
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Users className="h-4 w-4" />
                  <span className="font-medium text-foreground">
                    {c.total_membros ?? 0}
                  </span>
                </div>
              </div>
              {jaSou ? (
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => handleSair(c.centro_custo)}
                  disabled={ehUnicoGestor}
                  title={
                    ehUnicoGestor
                      ? 'Você é o único Gestor — nomeie outro antes de sair'
                      : ''
                  }
                >
                  <LogOut className="mr-1 h-4 w-4" />
                  {ehUnicoGestor ? 'Único Gestor (não pode sair)' : 'Sair do CC'}
                </Button>
              ) : (
                !isAdminOuTI && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full"
                    onClick={() => setOpenEntrada(c.centro_custo)}
                  >
                    <UserPlus className="mr-1 h-4 w-4" />
                    Solicitar entrada
                  </Button>
                )
              )}
            </div>
          )
        })}
        {filtrados.length === 0 && (
          <p className="col-span-full text-sm text-muted-foreground">
            Nenhum resultado.
          </p>
        )}
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
