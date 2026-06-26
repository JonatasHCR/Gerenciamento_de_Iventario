'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getMarcas,
  createMarca,
  updateMarca,
  deleteMarca,
  type Marca,
} from '@/lib/api/marcas'
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
import { Plus, Pencil, Trash2 } from 'lucide-react'

export default function MarcasPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [loading, setLoading] = useState(true)

  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<Marca | null>(null)
  const [form, setForm] = useState({ nome: '' })

  const isAdmin = user?.tipo === 'Admin'

  useEffect(() => {
    if (!isLoading && user && !isAdmin) {
      router.replace('/')
    }
  }, [user, isAdmin, isLoading, router])

  const load = () => {
    getMarcas()
      .then(setMarcas)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  function abrirNova() {
    setEditando(null)
    setForm({ nome: '' })
    setOpen(true)
  }

  function abrirEditar(m: Marca) {
    setEditando(m)
    setForm({ nome: m.nome })
    setOpen(true)
  }

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault()
    try {
      if (editando) {
        await updateMarca(editando.id, { nome: form.nome })
        toast.success('Marca atualizada.')
      } else {
        await createMarca({ nome: form.nome })
        toast.success('Marca criada.')
      }
      setOpen(false)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  async function handleDelete(m: Marca) {
    if (
      !confirm(
        `Excluir "${m.nome}"? Os modelos dessa marca também serão removidos.`,
      )
    )
      return
    try {
      await deleteMarca(m.id)
      toast.success('Marca removida.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  if (!isAdmin) return null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Marcas</h1>
          <p className="text-sm text-muted-foreground">
            Fabricantes dos equipamentos. Qualquer usuário pode criar marca
            ao cadastrar um equipamento; aqui o Admin consolida.
          </p>
        </div>
        <Button size="sm" onClick={abrirNova} className="shrink-0">
          <Plus className="mr-1 h-4 w-4" /> Nova marca
        </Button>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-2 text-left font-medium">Nome</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={2} className="px-4 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : marcas.length === 0 ? (
              <tr>
                <td colSpan={2} className="px-4 py-6 text-center text-muted-foreground">
                  Nenhuma marca cadastrada.
                </td>
              </tr>
            ) : (
              marcas.map((m) => (
                <tr key={m.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2 font-medium">{m.nome}</td>
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
              {editando ? `Editar "${editando.nome}"` : 'Nova marca'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSalvar} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                placeholder="Ex.: Dell, HP, Samsung, …"
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
