// Time helpers. Mirrors the Python timeutil.py logic on the frontend.
// Everything from the API is UTC. Everything displayed is Asia/Dhaka.

const TZ = 'Asia/Dhaka'

export function fmtDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', {
    timeZone: TZ,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export function fmtTime(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', {
    timeZone: TZ,
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export function fmtShort(iso: string | null): string {
  if (!iso) return ''
  const now = new Date()
  const d = new Date(iso)
  const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000)
  if (diffDays === 0) return `Today ${fmtTime(iso)}`
  if (diffDays === 1) return `Tomorrow ${fmtTime(iso)}`
  if (diffDays === -1) return `Yesterday ${fmtTime(iso)}`
  return fmtDate(iso)
}

export function isOverdue(iso: string | null): boolean {
  if (!iso) return false
  return new Date(iso) < new Date()
}

export function fmtRelative(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return fmtDate(iso)
}
