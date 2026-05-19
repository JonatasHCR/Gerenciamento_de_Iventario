import { apiFetch } from './client'
import type { User } from '@/types/api'

export interface UserCreate {
  nome: string
  email: string
  senha: string
  tipo?: string
}

export interface UserUpdate {
  nome?: string
  email?: string
  senha?: string
  tipo?: string
}

export async function getUsers(): Promise<User[]> {
  const res = await apiFetch<{ users: User[] }>('/users/')
  return res.users
}

export async function createUser(data: UserCreate): Promise<User> {
  return apiFetch<User>('/users/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createUserAdmin(data: UserCreate): Promise<User> {
  return apiFetch<User>('/users/admin', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateUser(
  id: number,
  data: UserUpdate,
): Promise<User> {
  return apiFetch<User>(`/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteUser(id: number): Promise<User> {
  return apiFetch<User>(`/users/${id}`, { method: 'DELETE' })
}
