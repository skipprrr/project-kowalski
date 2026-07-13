'use client'
export default function Settings() {
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="page-title">⚙️ Settings</div>
          <div className="page-sub">Configuration & info</div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 540 }}>

        <div className="card">
          <div className="section-title" style={{ marginBottom: 12 }}>Stack</div>
          {[
            ['Interface',    'Telegram bot + this dashboard'],
            ['Database',     'Supabase (Singapore)'],
            ['Hosting',      'Vercel (serverless)'],
            ['Reminders',    'pg_cron — fires every 60s, free forever'],
            ['AI',           'Groq → Cerebras → Gemini (auto-failover)'],
            ['Parsing',      'Rules engine first, AI only as fallback'],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <span style={{ color: 'var(--text-2)' }}>{k}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="section-title" style={{ marginBottom: 12 }}>Quick Reference</div>
          {[
            ['remind me tomorrow 9pm to …',   'Reminder with time'],
            ['task: …',                        'New task'],
            ['note: …',                        'Save a note'],
            ['idea: …',                        'Capture an idea'],
            ['Fatima owes me 500',             'Money — they owe you'],
            ['i owe Rahim 1200',               'Money — you owe them'],
            ['done',                           'Complete latest task'],
            ['search …',                       'Search everything'],
            ['today',                          'What\'s on today'],
            ['list tasks',                     'List open tasks'],
          ].map(([cmd, desc]) => (
            <div key={cmd} style={{ display: 'flex', gap: 16, padding: '7px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <code style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)', minWidth: 220, flexShrink: 0 }}>{cmd}</code>
              <span style={{ color: 'var(--text-2)' }}>{desc}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="section-title" style={{ marginBottom: 8 }}>Philosophy</div>
          <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7 }}>
            Python owns the data. AI interprets the data.<br />
            AI is never responsible for critical data operations.<br />
            Every feature should save time. If it creates more work than it removes, it should not exist.
          </p>
        </div>

      </div>
    </div>
  )
}
