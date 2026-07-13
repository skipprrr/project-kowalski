'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowRight } from 'lucide-react'
import { api, type Item, type Counts } from '@/lib/api'
import { fmtShort, isOverdue } from '@/lib/time'

export default function Dashboard() {
  const [counts, setCounts] = useState<Counts | null>(null)
  const [today, setToday] = useState<Item[]>([])
  const [overdue, setOverdue] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.counts(), api.today()])
      .then(([c, t]) => {
        setCounts(c)
        setToday(t.items)
        setOverdue(t.overdue)
      })
      .finally(() => setLoading(false))
  }, [])

  async function done(id: string) {
    await api.completeItem(id)
    const t = await api.today()
    setToday(t.items)
    setOverdue(t.overdue)
    const c = await api.counts()
    setCounts(c)
  }

  if (loading) return <div className="loading pulse">Loading…</div>

  const tiles = [
    { label: 'Today',     value: counts?.today ?? 0,    cls: 'accent', href: '/today' },
    { label: 'Overdue',   value: counts?.overdue ?? 0,  cls: overdue.length ? 'red' : '', href: '/today' },
    { label: 'Tasks',     value: counts?.task ?? 0,     cls: '', href: '/tasks' },
    { label: 'Reminders', value: counts?.reminder ?? 0, cls: '', href: '/reminders' },
    { label: 'Notes',     value: counts?.note ?? 0,     cls: '', href: '/notes' },
    { label: 'Ideas',     value: counts?.idea ?? 0,     cls: '', href: '/ideas' },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-sub">{new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</div>
        </div>
      </div>

      {/* Stat tiles */}
      <div className="stat-grid">
        {tiles.map(t => (
          <Link key={t.label} href={t.href} className={`stat-tile ${t.cls}`} style={{ textDecoration: 'none' }}>
            <div className="num">{t.value}</div>
            <div className="label">{t.label}</div>
          </Link>
        ))}
      </div>

      {/* Overdue */}
      {overdue.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--red)' }}>
            <AlertTriangle size={11} /> Overdue
          </div>
          <div className="item-list">
            {overdue.slice(0, 5).map(item => (
              <ItemRow key={item.id} item={item} onDone={done} />
            ))}
          </div>
        </div>
      )}

      {/* Today */}
      {today.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title">Due Today</div>
          <div className="item-list">
            {today.map(item => (
              <ItemRow key={item.id} item={item} onDone={done} />
            ))}
          </div>
        </div>
      )}

      {overdue.length === 0 && today.length === 0 && (
        <div className="empty">
          <div className="empty-icon">🧘</div>
          <div className="empty-text">Nothing due today.</div>
          <div className="empty-sub">Clear head. Use ⌘K to add something.</div>
        </div>
      )}

      {/* Quick links */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {['/tasks', '/reminders', '/notes', '/ideas', '/money', '/entities'].map(href => (
          <Link key={href} href={href} className="btn btn-ghost" style={{ fontSize: 12 }}>
            {href.replace('/', '').replace(/^\w/, c => c.toUpperCase())}
            <ArrowRight size={12} />
          </Link>
        ))}
      </div>
    </div>
  )
}

function ItemRow({ item, onDone }: { item: Item; onDone: (id: string) => void }) {
  const over = isOverdue(item.due_at)
  return (
    <div className={`item-row item-priority-${item.priority}`}>
      <button className="item-check" onClick={() => onDone(item.id)} title="Mark done" />
      <div className="item-content">
        <div className="item-text">{item.content}</div>
        <div className="item-meta">
          {item.due_at && (
            <span className={`item-time ${over ? 'overdue' : ''}`}>
              {fmtShort(item.due_at)}
            </span>
          )}
          {item.recurrence && <span className="item-tag">🔁 {item.recurrence}</span>}
          {item.tags?.map(t => <span key={t} className="item-tag">#{t}</span>)}
        </div>
      </div>
    </div>
  )
}
