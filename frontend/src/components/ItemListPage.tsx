'use client'
import { useEffect, useState, useCallback } from 'react'
import { Trash2, Check, X } from 'lucide-react'
import { api, type Item, type ItemType } from '@/lib/api'
import { fmtShort, isOverdue } from '@/lib/time'

interface Props {
  type: ItemType
  title: string
  icon: string
  emptyText: string
  showCheck?: boolean
}

export default function ItemListPage({ type, title, icon, emptyText, showCheck = true }: Props) {
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')

  const load = useCallback(async () => {
    const r = await api.items({ type, status: 'open' })
    setItems(r.items)
  }, [type])

  useEffect(() => { load().finally(() => setLoading(false)) }, [load])

  async function add() {
    if (!input.trim() || busy) return
    setBusy(true)
    setFeedback('')
    try {
      const r = await api.handle(input)
      setFeedback(r.text)
      setInput('')
      await load()
    } catch {
      setFeedback('Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function done(id: string) {
    await api.completeItem(id)
    setItems(prev => prev.filter(i => i.id !== id))
  }

  async function del(id: string) {
    await api.deleteItem(id)
    setItems(prev => prev.filter(i => i.id !== id))
  }

  function startEdit(item: Item) {
    setEditingId(item.id)
    setEditText(item.content)
  }

  async function saveEdit(id: string) {
    if (!editText.trim()) return
    await api.handle(`edit: ${items.find(i => i.id === id)?.content} → ${editText}`)
    setEditingId(null)
    await load()
  }

  function cancelEdit() {
    setEditingId(null)
    setEditText('')
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">{icon} {title}</div>
          <div className="page-sub">{items.length} open</div>
        </div>
      </div>

      {/* Quick-add */}
      <div className="quick-add">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder={`Add a ${type}…`}
        />
        <button className="btn btn-primary" onClick={add} disabled={busy}>
          {busy ? '…' : 'Add'}
        </button>
      </div>
      {feedback && (
        <div style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 16, marginTop: -12 }}>
          {feedback}
        </div>
      )}

      {loading && <div className="loading pulse">Loading…</div>}

      {!loading && items.length === 0 && (
        <div className="empty">
          <div className="empty-icon">{icon}</div>
          <div className="empty-text">{emptyText}</div>
          <div className="empty-sub">Use the box above or ⌘K to add one.</div>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="item-list">
          {items.map(item => (
            <div
              key={item.id}
              className={`item-row item-priority-${item.priority}`}
            >
              {showCheck && (
                <button className="item-check" onClick={() => done(item.id)} title="Mark done" />
              )}

              <div className="item-content">
                {editingId === item.id ? (
                  /* ── Inline edit mode ── */
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input
                      value={editText}
                      onChange={e => setEditText(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') saveEdit(item.id)
                        if (e.key === 'Escape') cancelEdit()
                      }}
                      autoFocus
                      style={{ flex: 1, padding: '4px 8px', fontSize: 13 }}
                    />
                    <button
                      className="btn btn-primary"
                      style={{ padding: '4px 8px' }}
                      onClick={() => saveEdit(item.id)}
                    >
                      <Check size={13} />
                    </button>
                    <button
                      className="btn btn-ghost"
                      style={{ padding: '4px 8px' }}
                      onClick={cancelEdit}
                    >
                      <X size={13} />
                    </button>
                  </div>
                ) : (
                  /* ── Normal display mode ── */
                  <div
                    className="item-text"
                    onClick={() => startEdit(item)}
                    title="Click to edit"
                    style={{ cursor: 'text' }}
                  >
                    {item.content}
                  </div>
                )}

                <div className="item-meta">
                  {item.due_at && (
                    <span className={`item-time ${isOverdue(item.due_at) ? 'overdue' : ''}`}>
                      {fmtShort(item.due_at)}
                    </span>
                  )}
                  {item.recurrence && <span className="item-tag">🔁 {item.recurrence}</span>}
                  {item.tags?.map(t => <span key={t} className="item-tag">#{t}</span>)}
                  {item.priority > 0 && (
                    <span className="item-tag" style={{ color: item.priority > 1 ? 'var(--red)' : 'var(--yellow)' }}>
                      {'!'.repeat(item.priority)}
                    </span>
                  )}
                </div>
              </div>

              {/* Delete button — appears on hover */}
              {editingId !== item.id && (
                <button
                  className="btn btn-danger"
                  style={{ opacity: 0, transition: 'opacity 0.1s', padding: '4px 8px', flexShrink: 0 }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '0')}
                  onClick={() => del(item.id)}
                  title="Delete"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
