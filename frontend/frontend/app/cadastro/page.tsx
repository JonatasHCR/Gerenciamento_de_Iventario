'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { createUser } from '@/lib/api/users'
import { createCargoInicial } from '@/lib/api/solicitacoes'
import { useAuth } from '@/context/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RequiredMark } from '@/components/ui/required-mark'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Link from 'next/link'

const CARGOS = ['Funcionario', 'Subgestor', 'Gestor', 'Tecnico_TI']

const DOMINIOS = [
  { value: 'ufcengenharia.com.br', label: '@ufcengenharia.com.br' },
  {
    value: 'sememail.com',
    label: '@sememail.com (não tenho email corporativo)',
  },
]

export default function CadastroPage() {
  const { login } = useAuth()
  const router = useRouter()
  const [nome, setNome] = useState('')
  const [emailLocal, setEmailLocal] = useState('')
  const [emailDominio, setEmailDominio] = useState(DOMINIOS[0].value)
  const [senha, setSenha] = useState('')
  const [cargo, setCargo] = useState('Funcionario')
  const [loading, setLoading] = useState(false)

  const email = emailLocal
    ? `${emailLocal.trim().toLowerCase()}@${emailDominio}`
    : ''

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!emailLocal.trim()) {
      toast.error('Digite a parte antes do @ no email.')
      return
    }
    if (senha.length < 8) {
      toast.error('Senha precisa ter ao menos 8 caracteres.')
      return
    }
    setLoading(true)
    try {
      await createUser({ nome, email, senha, tipo: cargo })
      await login(email, senha)

      if (cargo !== 'Funcionario') {
        try {
          await createCargoInicial({ cargo_solicitado: cargo })
          toast.success(`Conta criada! Solicitação de cargo "${cargo}" enviada ao Admin.`)
        } catch {
          toast.success('Conta criada como Funcionario.')
        }
      } else {
        toast.success('Conta criada com sucesso!')
      }

      router.push('/')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erro ao criar conta.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-center text-2xl">Criar conta</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="nome">Nome <RequiredMark /></Label>
            <Input
              id="nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              required
              autoComplete="name"
            />
          </div>
          <div className="space-y-1">
            <Label>Email <RequiredMark /></Label>
            <div className="flex gap-2">
              <Input
                id="email-local"
                value={emailLocal}
                onChange={(e) => setEmailLocal(e.target.value)}
                required
                placeholder="seu.nome"
                autoComplete="username"
                className="flex-1"
              />
              <Select value={emailDominio} onValueChange={setEmailDominio}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DOMINIOS.map((d) => (
                    <SelectItem key={d.value} value={d.value}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-muted-foreground">
              Email final: <strong>{email || `<digite>@${emailDominio}`}</strong>
            </p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="senha">Senha <RequiredMark /></Label>
            <Input
              id="senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
            <p className="text-xs text-muted-foreground">
              Mínimo 8 caracteres.
            </p>
          </div>
          <div className="space-y-1">
            <Label>Cargo desejado</Label>
            <Select value={cargo} onValueChange={setCargo}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CARGOS.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Criando…' : 'Criar conta'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Já tem conta?{' '}
            <Link href="/login" className="underline">
              Entrar
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  )
}
