'use client'
import { useEffect, useState } from 'react'
import { api, type Item } from '@/lib/api'
import { fmtTime, isOverdue } from '@/lib/time'
import { AlertTriangle } from 'lucide-react'

export default function Today() {
  const [today, setToday] = useState<Item[]>([])
  const [overdue, setOverdue] = useState<Item[]>([])
  const [tasks, setTasks] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    const [t, all] = await Promise.all([api.today(), api.items({ type: 'task' })])
    setToday(t.items)
    setOverdue(t.overdue)
    setTasks(all.items.filter(i => !i.due_at))
  }

  useEffect(() => { load().finally(() => setLoading(false)) }, [])

  async function done(id: string) {
    await api.completeItem(id)
    await load()
  }

  if (loading) return <div className="loading pulse">Loading…</div>

  const empty = today.length === 0 && overdue.length === 0 && tasks.length === 0

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">⚡ Today</div>
          <div className="page-sub">
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}
          </div>
        </div>
      </div>

      {empty && (
        <div className="empty">
          <div className="empty-icon">🧘</div>
          <div className="empty-text">Nothing on today.</div>
          <div className="empty-sub">Clear head. Use ⌘K to add something.</div>
        </div>
      )}

      {overdue.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title" style={{ color: 'var(--red)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={11} /> Overdue ({overdue.length})
          </div>
          <div className="item-list">
            {overdue.map(item => <Row key={item.id} item={item} onDone={done} />)}
          </div>
        </div>
      )}

      {today.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title">Due Today</div>
          <div className="item-list">
            {today.map(item => <Row key={item.id} item={item} onDone={done} />)}
          </div>
        </div>
      )}

      {tasks.length > 0 && (
        <div>
          <div className="section-title">Open Tasks</div>
          <div className="item-list">
            {tasks.slice(0, 10).map(item => <Row key={item.id} item={item} onDone={done} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ item, onDone }: { item: Item; onDone: (id: string) => void }) {
  return (
    <div className={`item-row item-priority-${item.priority}`}>
      <button className="item-check" onClick={() => onDone(item.id)} />
      <div className="item-content">
        <div className="item-text">{item.content}</div>
        <div className="item-meta">
          {item.due_at && (
            <span className={`item-time ${isOverdue(item.due_at) ? 'overdue' : ''}`}>
              {fmtTime(item.due_at)}
            </span>
          )}
          {item.recurrence && <span className="item-tag">🔁 {item.recurrence}</span>}
        </div>
      </div>
    </div>
  )
}
