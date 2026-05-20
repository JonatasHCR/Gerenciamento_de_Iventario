'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getLocalizacoes,
  createLocalizacao,
  updateLocalizacao,
  deleteLocalizacao,
  type Localizacao,
} from '@/lib/api/localizacoes'
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

export default function LocalizacoesPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [locs, setLocs] = useState<Localizacao[]>([])
  const [loading, setLoading] = useState(true)

  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<Localizacao | null>(null)
  const [form, setForm] = useState({ nome: '', descricao: '' })

  const isAdmin = user?.tipo === 'Admin'

  useEffect(() => {
    if (!isLoading && user && !isAdmin) {
      router.replace('/')
    }
  }, [user, isAdmin, isLoading, router])

  const load = () => {
    getLocalizacoes()
      .then(setLocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  function abrirNova() {
    setEditando(null)
    setForm({ nome: '', descricao: '' })
    setOpen(true)
  }

  function abrirEditar(l: Localizacao) {
    setEditando(l)
    setForm({ nome: l.nome, descricao: l.descricao ?? '' })
    setOpen(true)
  }

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault()
    try {
      if (editando) {
        await updateLocalizacao(editando.id, {
          nome: form.nome,
          descricao: form.descricao || null,
        })
        toast.success('Localização atualizada.')
      } else {
        await createLocalizacao({
          nome: form.nome,
          descricao: form.descricao || null,
        })
        toast.success('Localização criada.')
      }
      setOpen(false)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  async function handleDelete(l: Localizacao) {
    if (!confirm(`Excluir "${l.nome}"?`)) return
    try {
      await deleteLocalizacao(l.id)
      toast.success('Localização removida.')
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
          <h1 className="text-2xl font-bold">Localizações</h1>
          <p className="text-sm text-muted-foreground">
            Locais onde equipamentos podem estar. Qualquer usuário pode
            criar localização ao cadastrar um equipamento; aqui o Admin
            consolida.
          </p>
        </div>
        <Button size="sm" onClick={abrirNova} className="shrink-0">
          <Plus className="mr-1 h-4 w-4" /> Nova localização
        </Button>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-2 text-left font-medium">Nome</th>
              <th className="px-4 py-2 text-left font-medium">Descrição</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            ) : locs.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  Nenhuma localização cadastrada.
                </td>
              </tr>
            ) : (
              locs.map((l) => (
                <tr key={l.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2 font-medium">{l.nome}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {l.descricao || '—'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={() => abrirEditar(l)}
                        title="Editar"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-destructive"
                        onClick={() => handleDelete(l)}
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
              {editando ? `Editar "${editando.nome}"` : 'Nova localização'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSalvar} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                placeholder="Ex.: Sala TI, Almoxarifado, …"
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
