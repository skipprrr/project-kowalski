// All API calls go through here. One place, one base URL.
// The dashboard never talks to Supabase directly — only to FastAPI.

const BASE = process.env.NEXT_PUBLIC_API_URL || 'https://project-kowalski.vercel.app'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

// ── Types ────────────────────────────────────────────────────
export type ItemType = 'task' | 'reminder' | 'note' | 'idea' | 'journal'
export type ItemStatus = 'open' | 'done' | 'cancelled' | 'archived'

export interface Item {
  id: string
  type: ItemType
  content: string
  status: ItemStatus
  due_at: string | null
  due_text: string | null
  notify: boolean
  recurrence: string | null
  priority: number
  tags: string[]
  source: string
  parsed_by: string | null
  created_at: string
  updated_at: string
}

export interface Entity {
  id: string
  name: string
  kind: 'person' | 'business' | 'project' | 'place' | 'topic'
  meta: Record<string, unknown>
  created_at: string
}

export interface MoneyRecord {
  id: string
  entity_id: string | null
  person_text: string | null
  direction: 'they_owe_me' | 'i_owe_them'
  amount: number
  currency: string
  note: string | null
  status: 'pending' | 'settled' | 'cancelled'
  created_at: string
  entities?: { name: string }
}

export interface Counts {
  task: number
  reminder: number
  note: number
  idea: number
  journal: number
  overdue: number
  today: number
}

// ── Items ────────────────────────────────────────────────────
export const api = {
  handle: (text: string) =>
    req<{ ok: boolean; text: string; data: Record<string, unknown> }>('/api/handle', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  counts: () => req<Counts>('/api/items/counts'),

  today: () => req<{ items: Item[]; overdue: Item[] }>('/api/items/today'),

  items: (params?: { type?: string; status?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.type) q.set('type', params.type)
    if (params?.status) q.set('status', params.status ?? 'open')
    if (params?.limit) q.set('limit', String(params.limit))
    return req<{ items: Item[]; count: number }>(`/api/items?${q}`)
  },

  completeItem: (id: string) =>
    req<Item>(`/api/items/${id}/done`, { method: 'PATCH' }),

  deleteItem: (id: string) =>
    req<{ ok: boolean }>(`/api/items/${id}`, { method: 'DELETE' }),

  search: (q: string) =>
    req<{ results: Item[]; count: number; query: string }>(`/api/search?q=${encodeURIComponent(q)}`),

  // ── Entities ──────────────────────────────────────────────
  entities: (kind?: string) => {
    const q = kind ? `?kind=${kind}` : ''
    return req<{ entities: Entity[]; count: number }>(`/api/entities${q}`)
  },

  entity: (id: string) =>
    req<{ entity: Entity; timeline: Item[] }>(`/api/entities/${id}`),

  createEntity: (name: string, kind: string) =>
    req<Entity>('/api/entities', {
      method: 'POST',
      body: JSON.stringify({ name, kind }),
    }),

  // ── Money ─────────────────────────────────────────────────
  money: () =>
    req<{
      money: MoneyRecord[]
      summary: { owed_to_me: number; i_owe: number; net: number; people: unknown[] }
    }>('/api/money'),

  settleMoney: (id: string) =>
    req<MoneyRecord>(`/api/money/${id}/settle`, { method: 'PATCH' }),
}
