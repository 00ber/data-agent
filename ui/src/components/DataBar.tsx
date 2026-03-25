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
    <button
      onClick={toggleDataPanel}
      className="flex items-center justify-between w-full px-4 py-2 text-sm
                 text-text-secondary border-b border-border hover:bg-surface-alt transition-colors"
    >
      <span className="truncate">{summary}</span>
      {dataPanelOpen ? (
        <ChevronUp className="w-4 h-4 shrink-0" />
      ) : (
        <ChevronDown className="w-4 h-4 shrink-0" />
      )}
    </button>
  )
}
