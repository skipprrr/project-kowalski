'use client'
import { useEffect, useState } from 'react'
import { CheckSquare, Circle } from 'lucide-react'
import { fmtShort } from '@/lib/time'

interface Project {
  id: string
  name: string
  description: string | null
  status: string
  due_at: string | null
  created_at: string
}

interface Task {
  id: string
  content: string
  status: string
  priority: number
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Record<string, Task[]>>({})
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [tab, setTab] = useState<'active' | 'done'>('active')

  const BASE = process.env.NEXT_PUBLIC_API_URL || 'https://project-kowalski.vercel.app'

  async function load() {
    try {
      const res = await fetch(`${BASE}/api/projects?status=${tab}`)
      if (res.ok) {
        const data = await res.json()
        setProjects(data.projects || [])
      }
    } catch {} finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [tab])

  async function loadTasks(projectId: string) {
    try {
      const res = await fetch(`${BASE}/api/projects/${projectId}/tasks`)
      if (res.ok) {
        const data = await res.json()
        setTasks(prev => ({ ...prev, [projectId]: data.tasks || [] }))
      }
    } catch {}
  }

  function toggle(id: string) {
    if (expanded === id) {
      setExpanded(null)
    } else {
      setExpanded(id)
      if (!tasks[id]) loadTasks(id)
    }
  }

  const shown = projects.filter(p => tab === 'active'
    ? p.status === 'active' || p.status === 'paused'
    : p.status === 'done' || p.status === 'cancelled')

  if (loading) return <div className="loading pulse">Loading…</div>

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">📁 Projects</div>
          <div className="page-sub">{shown.length} {tab}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {(['active', 'done'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`pill ${tab === t ? 'pill-violet' : ''}`}
            style={{ cursor: 'pointer', border: tab === t ? 'none' : '1px solid var(--border)', background: tab === t ? undefined : 'transparent' }}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {shown.length === 0 && (
        <div className="empty">
          <div className="empty-icon">📁</div>
          <div className="empty-text">No {tab} projects.</div>
          <div className="empty-sub">Tell Kowalski: &quot;project: Jersey Fiesta Website&quot;</div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {shown.map(proj => (
          <div key={proj.id} className="card" style={{ cursor: 'pointer' }}
            onClick={() => toggle(proj.id)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 18 }}>📁</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{proj.name}</div>
                {proj.due_at && (
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                    Due: {fmtShort(proj.due_at)}
                  </div>
                )}
              </div>
              <span className={`pill ${proj.status === 'active' ? 'pill-green' : proj.status === 'done' ? 'pill-violet' : ''}`}>
                {proj.status}
              </span>
            </div>

            {expanded === proj.id && (
              <div style={{ marginTop: 14 }}>
                <div className="section-title" style={{ marginBottom: 8 }}>Tasks</div>
                {!tasks[proj.id] ? (
                  <div className="pulse" style={{ color: 'var(--text-3)', fontSize: 13 }}>Loading…</div>
                ) : tasks[proj.id].length === 0 ? (
                  <div style={{ color: 'var(--text-3)', fontSize: 13 }}>
                    No tasks yet. Say &quot;task under {proj.name}: do something&quot;
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {tasks[proj.id].map(task => (
                      <div key={task.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                        {task.status === 'done'
                          ? <CheckSquare size={13} color="var(--green)" />
                          : <Circle size={13} color="var(--text-3)" />
                        }
                        <span style={{ color: task.status === 'done' ? 'var(--text-3)' : 'var(--text)',
                          textDecoration: task.status === 'done' ? 'line-through' : 'none' }}>
                          {task.content}
                        </span>
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
