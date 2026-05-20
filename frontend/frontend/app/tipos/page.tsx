'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useAuth } from '@/context/auth-context'
import {
  getTipos,
  createTipo,
  updateTipo,
  deleteTipo,
  type TipoEletronico,
} from '@/lib/api/tipos'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Plus, Pencil, Power, Trash2 } from 'lucide-react'

export default function TiposPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [tipos, setTipos] = useState<TipoEletronico[]>([])
  const [loading, setLoading] = useState(true)

  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState<TipoEletronico | null>(null)
  const [form, setForm] = useState({ nome: '', descricao: '' })

  const isAdmin = user?.tipo === 'Admin'

  useEffect(() => {
    if (!isLoading && user && !isAdmin) {
      router.replace('/')
    }
  }, [user, isAdmin, isLoading, router])

  const load = () => {
    getTipos()
      .then(setTipos)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  function abrirNovo() {
    setEditando(null)
    setForm({ nome: '', descricao: '' })
    setOpen(true)
  }

  function abrirEditar(t: TipoEletronico) {
    setEditando(t)
    setForm({ nome: t.nome, descricao: t.descricao ?? '' })
    setOpen(true)
  }

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault()
    try {
      if (editando) {
        await updateTipo(editando.id, {
          nome: form.nome,
          descricao: form.descricao || null,
        })
        toast.success('Tipo atualizado.')
      } else {
        await createTipo({
          nome: form.nome,
          descricao: form.descricao || null,
        })
        toast.success('Tipo criado.')
      }
      setOpen(false)
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro ao salvar.')
    }
  }

  async function handleToggleAtivo(t: TipoEletronico) {
    try {
      await updateTipo(t.id, { ativo: !t.ativo })
      toast.success(t.ativo ? 'Tipo desativado.' : 'Tipo reativado.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  async function handleDelete(t: TipoEletronico) {
    if (
      !confirm(
        `Excluir "${t.nome}"? Se houver equipamentos usando este tipo, será apenas desativado.`,
      )
    )
      return
    try {
      await deleteTipo(t.id)
      toast.success('Tipo removido / desativado.')
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Erro.')
    }
  }

  if (!isAdmin) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tipos de Equipamento</h1>
          <p className="text-sm text-muted-foreground">
            Catálogo dinâmico. Inativos não aparecem em novos cadastros, mas
            permanecem em equipamentos existentes.
          </p>
        </div>
        <Button size="sm" onClick={abrirNovo}>
          <Plus className="mr-1 h-4 w-4" /> Novo tipo
        </Button>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[500px] text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-2 text-left font-medium">Nome</th>
              <th className="px-4 py-2 text-left font-medium">Descrição</th>
              <th className="px-4 py-2 text-left font-medium">Status</th>
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
            ) : tipos.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                  Nenhum tipo cadastrado.
                </td>
              </tr>
            ) : (
              tipos.map((t) => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-2 font-medium">{t.nome}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {t.descricao || '—'}
                  </td>
                  <td className="px-4 py-2">
                    <Badge variant={t.ativo ? 'default' : 'secondary'}>
                      {t.ativo ? 'Ativo' : 'Inativo'}
                    </Badge>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={() => abrirEditar(t)}
                        title="Editar"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={() => handleToggleAtivo(t)}
                        title={t.ativo ? 'Desativar' : 'Reativar'}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-destructive"
                        onClick={() => handleDelete(t)}
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
              {editando ? `Editar "${editando.nome}"` : 'Novo tipo'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSalvar} className="space-y-3">
            <div className="space-y-1">
              <Label>Nome <RequiredMark /></Label>
              <Input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                required
                placeholder="Ex.: Tablet, Trena Digital, …"
              />
            </div>
            <div className="space-y-1">
              <Label>Descrição (opcional)</Label>
              <Input
                value={form.descricao}
                onChange={(e) =>
                  setForm((f) => ({ ...f, descricao: e.target.value }))
                }
                placeholder="Ex.: Tablet Android para campo"
              />
            </div>
            <Button type="submit" className="w-full">
              {editando ? 'Salvar alterações' : 'Criar tipo'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
