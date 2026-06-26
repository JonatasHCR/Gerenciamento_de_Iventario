'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getModelos,
  createModelo,
  updateModelo,
  deleteModelo,
  type Modelo,
} from '@/lib/api/modelos'
import { getMarcas, type Marca } from '@/lib/api/marcas'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { SearchableSelect } from '@/components/app/searchable-select'
import { Plus, Pencil, Trash2 } from 'lucide-react'

export default function ModelosPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [modelos, setModelos] = useState<Modelo[]>([])
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [loading, setLoading] = useState(true)
  const [filtroMarca, setFiltroMarca] = useState('todas')

  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<Modelo | null>(null)
  const [form, setForm] = useState({ nome: '', descricao: '', marca_id: '' })

  const isAdmin = user?.tipo === 'Admin'

  useEffect(() => {
    if (!isLoading && user && !isAdmin) {
      router.replace('/')
    }
  }, [user, isAdmin, isLoading, router])

  const load = () => {
    getModelos()
      .then(setModelos)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    getMarcas().then(setMarcas).catch(() => {})
  }, [])

  function abrirNovo() {
    setEditando(null)
    setForm({ nome: '', descricao: '', marca_id: '' })
    setOpen(true)
  }

  function abrirEditar(m: Modelo) {
    setEditando(m)
    setForm({
      nome: m.nome,
      descricao: m.descricao ?? '',
      marca_id: String(m.marca_id),
    })
    setOpen(true)
  }

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault()
    if (!form.marca_id) {
      toast.error('Selecione a marca do modelo.')
      return
    }
    try {
      if (editando) {
        await updateModelo(editando.id, {
          nome: form.nome,
          descricao: form.descricao || null,
          marca_id: Number(form.marca_id),
        })
        toast.success('Modelo atualizado.')
      } else {
        await createModelo({
          nome: form.nome,
          descricao: form.descricao || null,
          marca_id: Number(form.marca_id),
        })
        toast.success('Modelo criado.')
      }
      setOpen(false)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  async function handleDelete(m: Modelo) {
    if (!confirm(`Excluir "${m.nome}"?`)) return
    try {
      await deleteModelo(m.id)
      toast.success('Modelo removido.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  if (!isAdmin) return null

  const modelosFiltrados =
    filtroMarca === 'todas'
      ? modelos
      : modelos.filter((m) => String(m.marca_id) === filtroMarca)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Modelos</h1>
          <p className="text-sm text-muted-foreground">
            Modelos de equipamentos, sempre associados a uma marca. Qualquer
            usuário pode criar ao cadastrar um equipamento; aqui o Admin
            consolida.
          </p>
        </div>
        <Button size="sm" onClick={abrirNovo} className="shrink-0">
          <Plus className="mr-1 h-4 w-4" /> Novo modelo
        </Button>
      </div>

      <div className="max-w-xs">
        <SearchableSelect
          value={filtroMarca}
          onChange={setFiltroMarca}
          options={[
            { value: 'todas', label: 'Todas as marcas' },
            ...marcas.map((m) => ({ value: String(m.id), label: m.nome })),
          ]}
        />
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-2 text-left font-medium">Nome</th>
              <th className="px-4 py-2 text-left font-medium">Marca</th>
              <th className="px-4 py-2 text-left font-medium">Descrição</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : modelosFiltrados.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                  Nenhum modelo cadastrado.
                </td>
              </tr>
            ) : (
              modelosFiltrados.map((m) => (
                <tr key={m.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2 font-medium">{m.nome}</td>
                  <td className="px-4 py-2">{m.marca_nome ?? '—'}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {m.descricao || '—'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={() => abrirEditar(m)}
                        title="Editar"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-destructive"
                        onClick={() => handleDelete(m)}
                        title="Excluir"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editando ? `Editar "${editando.nome}"` : 'Novo modelo'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSalvar} className="space-y-3">
            <div className="space-y-1">
              <Label>Marca <RequiredMark /></Label>
              <SearchableSelect
                value={form.marca_id}
                onChange={(v) => setForm((f) => ({ ...f, marca_id: v }))}
                options={marcas.map((m) => ({
                  value: String(m.id),
                  label: m.nome,
                }))}
                placeholder="Selecione a marca"
              />
            </div>
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                placeholder="Ex.: Latitude 5420, EliteBook 840, …"
              />
            </div>
            <div className="space-y-1">
              <Label>Descrição (opcional)</Label>
              <Input
                value={form.descricao}
                onChange={(e) =>
                  setForm((f) => ({ ...f, descricao: e.target.value }))
                }
              />
            </div>
            <Button type="submit" className="w-full">
              {editando ? 'Salvar' : 'Criar'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
