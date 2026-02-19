import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Item {
  id: number
  title: string
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ItemCreate {
  title: string
  description?: string
}

export interface ItemUpdate {
  title?: string
  description?: string
}

export const itemsApi = {
  getAll: () => api.get<Item[]>('/items/'),
  getById: (id: number) => api.get<Item>(`/items/${id}`),
  create: (data: ItemCreate) => api.post<Item>('/items/', data),
  update: (id: number, data: ItemUpdate) => api.put<Item>(`/items/${id}`, data),
  delete: (id: number) => api.delete(`/items/${id}`),
}
