'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { api, type Entity, type Item, type MoneyRecord } from '@/lib/api'
import { fmtShort, fmtRelative } from '@/lib/time'

const TYPE_ICON: Record<string, string> = {
  task: '📋', reminder: '🔔', note: '📝', idea: '💡', journal: '📔',
}

export default function EntityDetail() {
  const { id } = useParams<{ id: string }>()
  const [entity, setEntity] = useState<Entity | null>(null)
  const [timeline, setTimeline] = useState<Item[]>([])
  const [money, setMoney] = useState<MoneyRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.entity(id), api.money()])
      .then(([e, m]) => {
        setEntity(e.entity)
        setTimeline(e.timeline)
        // filter money records belonging to this entity
        setMoney(m.money.filter(r => r.entity_id === id))
      })
      .finally(() => setLoading(false))
  }, [id])

  async function settle(mid: string) {
    await api.settleMoney(mid)
    const m = await api.money()
    setMoney(m.money.filter(r => r.entity_id === id))
  }

  if (loading) return <div className="loading pulse">Loading…</div>
  if (!entity) return <div className="empty"><div className="empty-text">Entity not found.</div></div>

  const open = timeline.filter(i => i.status === 'open')
  const done = timeline.filter(i => i.status === 'done')

  const owedToMe = money.filter(m => m.direction === 'they_owe_me' && m.status === 'pending')
  const iOwe    = money.filter(m => m.direction === 'i_owe_them'   && m.status === 'pending')
  const totalOwed = owedToMe.reduce((s, r) => s + Number(r.amount), 0)
  const totalIOwe = iOwe.reduce((s, r) => s + Number(r.amount), 0)
  const net = totalOwed - totalIOwe

  return (
    <div className="page">
      <div style={{ marginBottom: 24 }}>
        <Link href="/entities" className="btn btn-ghost" style={{ marginBottom: 16, display: 'inline-flex' }}>
          <ArrowLeft size={13} /> Back
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div className="entity-avatar" style={{ width: 48, height: 48, fontSize: 20 }}>
            {entity.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="page-title">{entity.name}</div>
            <div className="page-sub" style={{ textTransform: 'capitalize' }}>{entity.kind}</div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid" style={{ marginBottom: 28 }}>
        <div className="stat-tile">
          <div className="num">{open.length}</div>
          <div className="label">Open items</div>
        </div>
        <div className="stat-tile">
          <div className="num">{done.length}</div>
          <div className="label">Done</div>
        </div>
        {net !== 0 && (
          <div className={`stat-tile ${net > 0 ? 'green' : 'red'}`}>
            <div className="num">৳{Math.abs(net).toLocaleString()}</div>
            <div className="label">{net > 0 ? 'Owes you' : 'You owe'}</div>
          </div>
        )}
      </div>

      {/* Money section */}
      {money.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title">💰 Money</div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="money-table">
              <thead>
                <tr>
                  <th>Direction</th>
                  <th>Amount</th>
                  <th>Note</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {money.filter(r => r.status === 'pending').map(r => (
                  <tr key={r.id}>
                    <td>
                      {r.direction === 'they_owe_me'
                        ? <span className="pill pill-green">→ owes you</span>
                        : <span className="pill pill-red">← you owe</span>
                      }
                    </td>
                    <td>
                      <span className={r.direction === 'they_owe_me' ? 'amount-positive' : 'amount-negative'}>
                        ৳{Number(r.amount).toLocaleString()}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-2)' }}>{r.note ?? '—'}</td>
                    <td style={{ color: 'var(--text-3)', fontSize: 12 }}>{fmtRelative(r.created_at)}</td>
                    <td>
                      <button className="btn btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => settle(r.id)}>
                        Settle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Open items */}
      {open.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div className="section-title">Open</div>
          <div className="item-list">
            {open.map(item => (
              <div key={item.id} className="item-row">
                <div style={{ fontSize: 14 }}>{TYPE_ICON[item.type] ?? '•'}</div>
                <div className="item-content">
                  <div className="item-text">{item.content}</div>
                  <div className="item-meta">
                    {item.due_at && <span className="item-time">{fmtShort(item.due_at)}</span>}
                    <span className="item-tag">{item.type}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      {done.length > 0 && (
        <div>
          <div className="section-title">History</div>
          <div className="item-list">
            {done.slice(0, 20).map(item => (
              <div key={item.id} className="item-row" style={{ opacity: 0.5 }}>
                <div style={{ fontSize: 14 }}>{TYPE_ICON[item.type] ?? '•'}</div>
                <div className="item-content">
                  <div className="item-text done">{item.content}</div>
                  <div className="item-meta">
                    <span className="item-time">{fmtRelative(item.updated_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {timeline.length === 0 && money.length === 0 && (
        <div className="empty">
          <div className="empty-text">Nothing linked to {entity.name} yet.</div>
          <div className="empty-sub">Mention them in Telegram and it appears here.</div>
        </div>
      )}
    </div>
  )
}