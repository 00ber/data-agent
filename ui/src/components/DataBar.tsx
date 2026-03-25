import { ChevronDown, ChevronUp } from 'lucide-react'
import { useStore } from '../store'

export default function DataBar() {
  const tables = useStore((s) => s.tables)
  const dataPanelOpen = useStore((s) => s.dataPanelOpen)
  const toggleDataPanel = useStore((s) => s.toggleDataPanel)

  if (tables.length === 0) return null

  const summary = tables
    .map((t) => `${t.name} ${t.rows.toLocaleString()} rows`)
    .join(' \u00B7 ')

  return (
    <div className="border-b border-border/80 bg-[rgba(255,252,247,0.72)]">
      <button
        onClick={toggleDataPanel}
        className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 text-left text-sm text-text-secondary transition-colors hover:bg-surface-alt/40"
      >
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
            Loaded tables
          </p>
          <span className="mt-1 block truncate">{summary}</span>
        </div>
        {dataPanelOpen ? (
          <ChevronUp className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0" />
        )}
      </button>
    </div>
  )
}
