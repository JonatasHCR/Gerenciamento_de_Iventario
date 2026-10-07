'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Boxes, Factory, Tags } from 'lucide-react'
import { useAuth } from '@/context/auth-context'
import { getTipos, type TipoEletronico } from '@/lib/api/tipos'
import { getMarcas, type Marca } from '@/lib/api/marcas'
import { getModelos, type Modelo } from '@/lib/api/modelos'
import { getEletronicos } from '@/lib/api/eletronicos'
import type { Eletronico } from '@/types/api'
import { Button } from '@/components/ui/button'

/**
 * Tipos, marcas e modelos numa visão só: o que existe no catálogo e quanto
 * dele está no inventário. Cadastrar e editar continua nas telas de cada um.
 */
export default function CatalogoPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [tipos, setTipos] = useState<TipoEletronico[]>([])
  const [marcas, setMarcas] = useState<Marca[]>([])
  const [modelos, setModelos] = useState<Modelo[]>([])
  const [equipamentos, setEquipamentos] = useState<Eletronico[]>([])

  useEffect(() => {
    if (isLoading) return
    if (user?.tipo !== 'Admin') {
      router.replace('/')
      return
    }
    getTipos().then(setTipos).catch(() => {})
    getMarcas().then(setMarcas).catch(() => {})
    getModelos().then(setModelos).catch(() => {})
    getEletronicos().then(setEquipamentos).catch(() => {})
  }, [isLoading, user, router])

  // tipo → marca → modelo → quantidade no inventário
  const arvore = useMemo(() => {
    const m = new Map<string, Map<string, Map<string, number>>>()
    for (const e of equipamentos) {
      const porMarca = m.get(e.tipo) ?? new Map<string, Map<string, number>>()
      const marca = e.marca || 'Sem marca'
      const porModelo = porMarca.get(marca) ?? new Map<string, number>()
      const modelo = e.modelo || 'sem modelo'
      porModelo.set(modelo, (porModelo.get(modelo) ?? 0) + 1)
      porMarca.set(marca, porModelo)
      m.set(e.tipo, porMarca)
    }
    return m
  }, [equipamentos])

  const usados = new Set(equipamentos.map((e) => `${e.marca}|${e.modelo}`))
  const semUso = modelos.filter((x) => !usados.has(`${x.marca_nome}|${x.nome}`))

  if (user?.tipo !== 'Admin') return null

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tipos e modelos</h1>
          <p className="text-sm text-muted-foreground">
            {tipos.length} tipo(s), {marcas.length} marca(s) e {modelos.length} modelo(s) no catálogo.
            Clique num modelo para ver os equipamentos dele.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link href="/tipos">
              <Tags className="h-4 w-4" /> Tipos
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/marcas">
              <Factory className="h-4 w-4" /> Marcas
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/modelos">
              <Boxes className="h-4 w-4" /> Modelos
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {tipos.map((t) => {
          const porMarca = arvore.get(t.nome)
          const total = porMarca
            ? [...porMarca.values()].reduce((s, mm) => s + [...mm.values()].reduce((a, b) => a + b, 0), 0)
            : 0
          return (
            <section key={t.id} className="space-y-3 rounded-xl border bg-card p-4 shadow-xs">
              <header className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-semibold">
                    {t.nome}
                    {!t.ativo && (
                      <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                        inativo
                      </span>
                    )}
                  </h2>
                  {t.descricao && <p className="text-xs text-muted-foreground">{t.descricao}</p>}
                </div>
                <Link
                  href={`/equipamentos?tipo=${encodeURIComponent(t.nome)}`}
                  className="shrink-0 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium hover:bg-secondary"
                >
                  {total} no inventário
                </Link>
              </header>
              {porMarca ? (
                [...porMarca.entries()]
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([marca, porModelo]) => (
                    <div key={marca}>
                      <p className="text-sm font-medium">{marca}</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {[...porModelo.entries()].map(([modelo, n]) => (
                          <Link
                            key={modelo}
                            href={`/equipamentos?tipo=${encodeURIComponent(t.nome)}`}
                            className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
                          >
                            {modelo} · {n}
                          </Link>
                        ))}
                      </div>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-muted-foreground">Nenhum equipamento deste tipo ainda.</p>
              )}
            </section>
          )
        })}
      </div>

      {semUso.length > 0 && (
        <section className="rounded-xl border bg-card p-4 shadow-xs">
          <h2 className="text-sm font-semibold">Modelos cadastrados sem nenhum equipamento</h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {semUso.map((x) => (
              <span key={x.id} className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {x.marca_nome} {x.nome}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
