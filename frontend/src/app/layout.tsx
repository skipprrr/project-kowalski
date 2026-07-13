'use client'
import './globals.css'
import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, CheckSquare, Bell, FileText, Lightbulb,
  BookOpen, Users, Wallet, Search, Settings, Zap,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { Counts } from '@/lib/api'

const NAV = [
  { href: '/',           icon: LayoutDashboard, label: 'Dashboard',  key: null },
  { href: '/today',      icon: Zap,             label: 'Today',      key: 'today' as keyof Counts },
  { href: '/tasks',      icon: CheckSquare,     label: 'Tasks',      key: 'task' as keyof Counts },
  { href: '/reminders',  icon: Bell,            label: 'Reminders',  key: 'reminder' as keyof Counts },
  { href: '/notes',      icon: FileText,        label: 'Notes',      key: 'note' as keyof Counts },
  { href: '/ideas',      icon: Lightbulb,       label: 'Ideas',      key: 'idea' as keyof Counts },
  { href: '/journal',    icon: BookOpen,        label: 'Journal',    key: 'journal' as keyof Counts },
  { href: '/entities',   icon: Users,           label: 'People',     key: null },
  { href: '/money',      icon: Wallet,          label: 'Money',      key: null },
  { href: '/search',     icon: Search,          label: 'Search',     key: null },
  { href: '/settings',   icon: Settings,        label: 'Settings',   key: null },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const [counts, setCounts] = useState<Counts | null>(null)
  const [palette, setPalette] = useState(false)
  const [paletteText, setPaletteText] = useState('')
  const [paletteResult, setPaletteResult] = useState('')
  const [paletteBusy, setPaletteBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.counts().then(setCounts).catch(() => {})
  }, [path])

  const openPalette = useCallback(() => {
    setPalette(true)
    setPaletteText('')
    setPaletteResult('')
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        openPalette()
      }
      if (e.key === 'Escape') setPalette(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [openPalette])

  async function submitPalette() {
    if (!paletteText.trim() || paletteBusy) return
    setPaletteBusy(true)
    setPaletteResult('...')
    try {
      const r = await api.handle(paletteText)
      setPaletteResult(r.text)
      setPaletteText('')
      api.counts().then(setCounts).catch(() => {})
    } catch {
      setPaletteResult('Something went wrong.')
    } finally {
      setPaletteBusy(false)
    }
  }

  return (
    <html lang="en">
      <head>
        <title>Kowalski</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <div className="layout">
          {/* ── Sidebar ── */}
          <nav className="sidebar">
            <div className="sidebar-logo">
              <div className="sidebar-logo-icon">🦊</div>
              <span className="sidebar-logo-text">Kowalski</span>
            </div>

            {/* Quick-add */}
            <div className="nav-section" style={{ marginBottom: 12 }}>
              <button
                className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'center', padding: '8px 12px' }}
                onClick={openPalette}
              >
                + Quick add <kbd style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff' }}>⌘K</kbd>
              </button>
            </div>

            <div className="nav-section">
              {NAV.map(({ href, icon: Icon, label, key }) => {
                const active = href === '/' ? path === '/' : path.startsWith(href)
                const count = key && counts ? counts[key] : null
                return (
                  <Link key={href} href={href} className={`nav-item ${active ? 'active' : ''}`}>
                    <Icon size={15} strokeWidth={1.8} />
                    {label}
                    {count != null && count > 0 && (
                      <span className="badge">{count}</span>
                    )}
                  </Link>
                )
              })}
            </div>
          </nav>

          {/* ── Main ── */}
          <main className="main">{children}</main>
        </div>

        {/* ── Command Palette ── */}
        {palette && (
          <div className="overlay" onClick={() => setPalette(false)}>
            <div className="palette" onClick={e => e.stopPropagation()}>
              <input
                ref={inputRef}
                className="palette-input"
                placeholder="Tell Kowalski anything…"
                value={paletteText}
                onChange={e => setPaletteText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') submitPalette()
                  if (e.key === 'Escape') setPalette(false)
                }}
              />
              <div className="palette-result">
                {paletteBusy
                  ? <span className="pulse">Thinking…</span>
                  : paletteResult || <span style={{ color: 'var(--text-3)' }}>e.g. "remind me tomorrow 9pm to call Ali"</span>
                }
              </div>
              <div className="palette-hint">
                <span><kbd>Enter</kbd> send</span>
                <span><kbd>Esc</kbd> close</span>
                <span>All natural language works</span>
              </div>
            </div>
          </div>
        )}
      </body>
    </html>
  )
}
