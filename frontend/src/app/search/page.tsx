'use client'
import { useState, useEffect, useRef } from 'react'
import { Search as SearchIcon } from 'lucide-react'
import { api, type Item } from '@/lib/api'
import { fmtShort } from '@/lib/time'

const TYPE_ICON: Record<string, string> = {
  task: '📋', reminder: '🔔', note: '📝', idea: '💡', journal: '📔',
}

export default function Search() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Item[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    clearTimeout(timer.current)
    if (!q.trim()) { setResults([]); setSearched(false); return }
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const r = await api.search(q)
        setResults(r.results)
        setSearched(true)
      } finally {
        setLoading(false)
      }
    }, 300)
  }, [q])

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">🔍 Search</div>
          <div className="page-sub">Full-text + fuzzy across everything</div>
        </div>
      </div>

      <div className="search-wrap">
        <SearchIcon size={15} />
        <input
          className="search-input"
          placeholder="Search everything… typos are ok"
          value={q}
          onChange={e => setQ(e.target.value)}
          autoFocus
        />
      </div>

      {loading && <div className="loading pulse">Searching…</div>}

      {!loading && searched && results.length === 0 && (
        <div className="empty">
          <div className="empty-text">Nothing found for &ldquo;{q}&rdquo;.</div>
          <div className="empty-sub">Try a different word or check the spelling.</div>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <div className="section-title" style={{ marginBottom: 12 }}>
            {results.length} result{results.length !== 1 ? 's' : ''} for &ldquo;{q}&rdquo;
          </div>
          <div className="item-list">
            {results.map(item => (
              <div key={item.id} className="item-row" style={{ opacity: item.status === 'done' ? 0.5 : 1 }}>
                <div style={{ fontSize: 14, flexShrink: 0 }}>{TYPE_ICON[item.type] ?? '•'}</div>
                <div className="item-content">
                  <div className={`item-text ${item.status === 'done' ? 'done' : ''}`}>{item.content}</div>
                  <div className="item-meta">
                    <span className="item-tag">{item.type}</span>
                    {item.due_at && <span className="item-time">{fmtShort(item.due_at)}</span>}
                    {item.status !== 'open' && <span className="pill pill-green" style={{ fontSize: 10 }}>{item.status}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!q && (
        <div className="empty">
          <div className="empty-icon">🔍</div>
          <div className="empty-text">Type to search.</div>
          <div className="empty-sub">Searches tasks, reminders, notes, ideas, and journal entries.</div>
        </div>
      )}
    </div>
  )
}
