'use client'
import { useEffect, useState } from 'react'
import { api, type MoneyRecord } from '@/lib/api'
import { fmtRelative } from '@/lib/time'

export default function Money() {
  const [records, setRecords] = useState<MoneyRecord[]>([])
  const [summary, setSummary] = useState({ owed_to_me: 0, i_owe: 0, net: 0 })
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'all' | 'they_owe_me' | 'i_owe_them'>('all')

  async function load() {
    const r = await api.money()
    setRecords(r.money)
    setSummary(r.summary)
  }

  useEffect(() => { load().finally(() => setLoading(false)) }, [])

  async function settle(id: string) {
    await api.settleMoney(id)
    await load()
  }

  const shown = tab === 'all' ? records : records.filter(r => r.direction === tab)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">💰 Money</div>
          <div className="page-sub">Pending ledger</div>
        </div>
      </div>

      {/* Summary tiles */}
      <div className="stat-grid" style={{ marginBottom: 24 }}>
        <div className="stat-tile green">
          <div className="num">৳{summary.owed_to_me.toLocaleString()}</div>
          <div className="label">Owed to me</div>
        </div>
        <div className="stat-tile red">
          <div className="num">৳{summary.i_owe.toLocaleString()}</div>
          <div className="label">I owe</div>
        </div>
        <div className={`stat-tile ${summary.net >= 0 ? 'green' : 'red'}`}>
          <div className="num">৳{Math.abs(summary.net).toLocaleString()}</div>
          <div className="label">{summary.net >= 0 ? 'Net positive' : 'Net negative'}</div>
        </div>
      </div>

      {/* Tab filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {(['all', 'they_owe_me', 'i_owe_them'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pill ${tab === t ? 'pill-violet' : ''}`}
            style={{ cursor: 'pointer', border: tab === t ? 'none' : '1px solid var(--border)', background: tab === t ? undefined : 'transparent' }}
          >
            {t === 'all' ? 'All' : t === 'they_owe_me' ? '→ Owed to me' : '← I owe'}
          </button>
        ))}
      </div>

      {loading && <div className="loading pulse">Loading…</div>}

      {!loading && shown.length === 0 && (
        <div className="empty">
          <div className="empty-icon">💰</div>
          <div className="empty-text">No pending records.</div>
          <div className="empty-sub">Tell Kowalski "Fatima owes me 500" or "I owe Rahim 1200".</div>
        </div>
      )}

      {!loading && shown.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="money-table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Direction</th>
                <th>Amount</th>
                <th>Note</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shown.map(r => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500 }}>
                    {r.entities?.name ?? r.person_text ?? '—'}
                  </td>
                  <td>
                    {r.direction === 'they_owe_me'
                      ? <span className="pill pill-green">→ owes me</span>
                      : <span className="pill pill-red">← I owe</span>
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
      )}
    </div>
  )
}
