'use client'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { fmtRelative } from '@/lib/time'

interface Skill {
  id: string
  name: string
  description: string | null
  progress: number
  goal: string | null
  created_at: string
}

interface SkillLog {
  id: string
  skill_id: string
  note: string
  duration: number | null
  created_at: string
}

export default function Skills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [logs, setLogs] = useState<Record<string, SkillLog[]>>({})
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    loadSkills()
  }, [])

  async function loadSkills() {
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'https://project-kowalski.vercel.app'
      const res = await fetch(`${BASE}/api/skills`)
      if (res.ok) {
        const data = await res.json()
        setSkills(data.skills || [])
      }
    } catch {
      // skills endpoint not yet wired — show empty state
    } finally {
      setLoading(false)
    }
  }

  async function loadLogs(skillId: string) {
    try {
      const BASE = process.env.NEXT_PUBLIC_API_URL || 'https://project-kowalski.vercel.app'
      const res = await fetch(`${BASE}/api/skills/${skillId}/logs`)
      if (res.ok) {
        const data = await res.json()
        setLogs(prev => ({ ...prev, [skillId]: data.logs || [] }))
      }
    } catch {}
  }

  function toggle(id: string) {
    if (expanded === id) {
      setExpanded(null)
    } else {
      setExpanded(id)
      if (!logs[id]) loadLogs(id)
    }
  }

  if (loading) return <div className="loading pulse">Loading…</div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">🎯 Skills</div>
          <div className="page-sub">Things you&apos;re learning</div>
        </div>
      </div>

      {skills.length === 0 && (
        <div className="empty">
          <div className="empty-icon">🎯</div>
          <div className="empty-text">No skills tracked yet.</div>
          <div className="empty-sub">Tell Kowalski: &quot;learning: Mandarin&quot; or &quot;learning: Boxing&quot;</div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {skills.map(skill => (
          <div key={skill.id} className="card" style={{ cursor: 'pointer' }}
            onClick={() => toggle(skill.id)}>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{skill.name}</div>
                {skill.goal && (
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                    Goal: {skill.goal}
                  </div>
                )}
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontWeight: 600, fontSize: 20,
                color: skill.progress >= 80 ? 'var(--green)' : skill.progress >= 40 ? 'var(--accent)' : 'var(--text-2)' }}>
                {skill.progress}%
              </div>
            </div>

            {/* Progress bar */}
            <div style={{ background: 'var(--bg-3)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${skill.progress}%`,
                background: skill.progress >= 80 ? 'var(--green)'
                          : skill.progress >= 40 ? 'var(--accent)'
                          : 'var(--text-3)',
                borderRadius: 4,
                transition: 'width 0.4s ease',
              }} />
            </div>

            {/* Session logs */}
            {expanded === skill.id && (
              <div style={{ marginTop: 16 }}>
                <div className="section-title" style={{ marginBottom: 8 }}>Recent sessions</div>
                {!logs[skill.id] ? (
                  <div style={{ color: 'var(--text-3)', fontSize: 13 }} className="pulse">Loading…</div>
                ) : logs[skill.id].length === 0 ? (
                  <div style={{ color: 'var(--text-3)', fontSize: 13 }}>
                    No sessions yet. Say &quot;skill log: {skill.name} — what you did&quot;
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {logs[skill.id].map(log => (
                      <div key={log.id} style={{ display: 'flex', gap: 12, fontSize: 13,
                        padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ color: 'var(--text-3)', flexShrink: 0 }}>
                          {fmtRelative(log.created_at)}
                        </span>
                        {log.duration && (
                          <span className="pill pill-violet">{log.duration}m</span>
                        )}
                        <span style={{ color: 'var(--text-2)' }}>{log.note}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
