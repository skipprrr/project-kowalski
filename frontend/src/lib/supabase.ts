/**
 * Direct Supabase access for the dashboard.
 *
 * WHY: Vercel serverless Python functions have a cold start of 1-2 seconds.
 * For READ operations (showing your tasks, reminders etc.) we don't need
 * to go through Python at all — Supabase can be queried directly from
 * the browser. Python still owns all WRITES (create, complete, delete).
 *
 * This does NOT break "Python owns the data" — reads are just SELECTs,
 * not business logic. The anon key has read-only access enforced by RLS.
 */

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

async function supabase<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T[]> {
  const url = new URL(`${SUPABASE_URL}/rest/v1/${path}`)
  url.searchParams.set('apikey', SUPABASE_ANON_KEY)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  }
  const res = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
    },
    // Cache for 10 seconds — feels instant on navigation, still fresh
    next: { revalidate: 10 },
  })
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${path}`)
  return res.json()
}

// ── Types (same as api.ts) ───────────────────────────────────
export type ItemType = 'task' | 'reminder' | 'note' | 'idea' | 'journal'

export interface Item {
  id: string
  type: ItemType
  content: string
  status: string
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
  kind: string
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
  status: string
  created_at: string
}

// ── Queries ──────────────────────────────────────────────────

const TZ = 'Asia/Dhaka'

function todayRange() {
  const now = new Date()
  // Get today's date in Dhaka timezone
  const dhaka = new Date(now.toLocaleString('en-US', { timeZone: TZ }))
  const start = new Date(dhaka)
  start.setHours(0, 0, 0, 0)
  const end = new Date(dhaka)
  end.setHours(23, 59, 59, 999)
  // Convert back to UTC for the query
  const offsetMs = now.getTime() - dhaka.getTime()
  return {
    start: new Date(start.getTime() + offsetMs).toISOString(),
    end: new Date(end.getTime() + offsetMs).toISOString(),
  }
}

export const db = {
  items: async (type?: string, status = 'open', limit = 50): Promise<Item[]> => {
    const params: Record<string, string> = {
      select: '*',
      deleted_at: 'is.null',
      status: `eq.${status}`,
      order: 'priority.desc,due_at.asc.nullslast,created_at.desc',
      limit: String(limit),
    }
    if (type) params.type = `eq.${type}`
    return supabase<Item>('items', params)
  },

  today: async (): Promise<Item[]> => {
    const { start, end } = todayRange()
    return supabase<Item>('items', {
      select: '*',
      deleted_at: 'is.null',
      status: 'eq.open',
      due_at: `gte.${start}`,
      'due_at.lte': end,
      order: 'due_at.asc',
    })
  },

  overdue: async (): Promise<Item[]> => {
    return supabase<Item>('items', {
      select: '*',
      deleted_at: 'is.null',
      status: 'eq.open',
      due_at: `lt.${new Date().toISOString()}`,
      order: 'due_at.asc',
    })
  },

  counts: async (): Promise<Record<string, number>> => {
    const types = ['task', 'reminder', 'note', 'idea', 'journal']
    const results = await Promise.all(
      types.map(async t => {
        const rows = await supabase<Item>('items', {
          select: 'id',
          deleted_at: 'is.null',
          status: 'eq.open',
          type: `eq.${t}`,
        })
        return [t, rows.length] as [string, number]
      })
    )
    const counts: Record<string, number> = Object.fromEntries(results)
    const [tod, over] = await Promise.all([db.today(), db.overdue()])
    counts.today = tod.length
    counts.overdue = over.length
    return counts
  },

  entities: async (kind?: string): Promise<Entity[]> => {
    const params: Record<string, string> = {
      select: '*',
      deleted_at: 'is.null',
      order: 'name.asc',
    }
    if (kind) params.kind = `eq.${kind}`
    return supabase<Entity>('entities', params)
  },

  entity: async (id: string): Promise<Entity | null> => {
    const rows = await supabase<Entity>('entities', {
      select: '*',
      id: `eq.${id}`,
    })
    return rows[0] ?? null
  },

  money: async (): Promise<MoneyRecord[]> => {
    return supabase<MoneyRecord>('money', {
      select: '*',
      deleted_at: 'is.null',
      status: 'eq.pending',
      order: 'created_at.desc',
    })
  },

  search: async (q: string): Promise<Item[]> => {
    return supabase<Item>('items', {
      select: '*',
      deleted_at: 'is.null',
      content: `ilike.*${q}*`,
      order: 'created_at.desc',
      limit: '20',
    })
  },
}
