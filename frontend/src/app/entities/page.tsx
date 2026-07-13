'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Plus, X } from 'lucide-react'
import { api, type Entity } from '@/lib/api'

const KIND_ICON: Record<string, string> = {
  person: '👤', business: '🏢', project: '📁', place: '📍', topic: '🏷',
}

export default function Entities() {
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('person')
  const [saving, setSaving] = useState(false)

  async function load() {
    const r = await api.entities()
    setEntities(r.entities)
  }

  useEffect(() => { load().finally(() => setLoading(false)) }, [])

  async function create() {
    if (!name.trim() || saving) return
    setSaving(true)
    try {
      await api.createEntity(name.trim(), kind)
      setName('')
      setKind('person')
      setShowForm(false)
      await load()
    } finally {
      setSaving(false)
    }
  }

  const kinds = ['all', ...Array.from(new Set(entities.map(e => e.kind)))]
  const shown = filter === 'all' ? entities : entities.filter(e => e.kind === filter)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">👥 People & Entities</div>
          <div className="page-sub">{entities.length} total</div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>
          {showForm ? <X size={14} /> : <Plus size={14} />}
          {showForm ? 'Cancel' : 'Add new'}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Name</div>
              <input
                style={{ width: '100%', padding: '8px 12px' }}
                placeholder="Fatima, Corner Cafe…"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && create()}
                autoFocus
              />
            </div>
            <div style={{ minWidth: 140 }}>
              <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Type</div>
              <select
                value={kind}
                onChange={e => setKind(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-3)', border: '1px solid var(--border)', borderRadius: 'var(--r)', color: 'var(--text)', fontSize: 14 }}
              >
                <option value="person">👤 Person</option>
                <option value="business">🏢 Business</option>
                <option value="project">📁 Project</option>
                <option value="place">📍 Place</option>
                <option value="topic">🏷 Topic</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={create} disabled={saving || !name.trim()}>
              {saving ? '…' : 'Create'}
            </button>
          </div>
        </div>
      )}

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
          <div className="empty-sub">Click "Add new" above or tell the bot "add person: Rahim".</div>
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
