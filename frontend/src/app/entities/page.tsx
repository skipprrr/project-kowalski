'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api, type Entity } from '@/lib/api'

const KIND_ICON: Record<string, string> = {
  person: '👤', business: '🏢', project: '📁', place: '📍', topic: '🏷',
}

export default function Entities() {
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    api.entities().then(r => setEntities(r.entities)).finally(() => setLoading(false))
  }, [])

  const kinds = ['all', ...Array.from(new Set(entities.map(e => e.kind)))]
  const shown = filter === 'all' ? entities : entities.filter(e => e.kind === filter)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">👥 People & Entities</div>
          <div className="page-sub">{entities.length} total</div>
        </div>
      </div>

      {/* Kind filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {kinds.map(k => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            className={`pill ${filter === k ? 'pill-violet' : ''}`}
            style={{ cursor: 'pointer', border: filter === k ? 'none' : '1px solid var(--border)', background: filter === k ? undefined : 'transparent' }}
          >
            {KIND_ICON[k] ?? ''} {k.charAt(0).toUpperCase() + k.slice(1)}
          </button>
        ))}
      </div>

      {loading && <div className="loading pulse">Loading…</div>}

      {!loading && shown.length === 0 && (
        <div className="empty">
          <div className="empty-icon">👥</div>
          <div className="empty-text">No entities yet.</div>
          <div className="empty-sub">They&apos;re created automatically when you mention people in Telegram.</div>
        </div>
      )}

      {!loading && shown.length > 0 && (
        <div className="entity-grid">
          {shown.map(e => (
            <Link key={e.id} href={`/entities/${e.id}`} className="entity-card">
              <div className="entity-avatar">{e.name.charAt(0).toUpperCase()}</div>
              <div className="entity-name">{e.name}</div>
              <div className="entity-kind">{KIND_ICON[e.kind]} {e.kind}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
