import type { TableData } from '../types'

interface TableArtifactProps {
  data: TableData
  title: string
}

export default function TableArtifact({ data, title }: TableArtifactProps) {
  const { columns, rows } = data
  const displayRows = rows.slice(0, 100) // Cap at 100 rows in view

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-text">{title}</h4>
          <span className="rounded-full bg-surface-alt px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-text-muted">
            {rows.length} rows
          </span>
        </div>
      )}
      <div className="overflow-x-auto rounded-[1.25rem] border border-border bg-surface shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-alt/80">
              {columns.map((col) => (
                <th
                  key={col}
                  className="border-b border-border px-3 py-2 text-left font-medium text-text-secondary"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-border last:border-0 hover:bg-surface-alt/50"
              >
                {(row as unknown[]).map((cell, j) => (
                  <td key={j} className="px-3 py-1.5 text-text-secondary">
                    {String(cell ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length > 100 && (
          <div className="border-t border-border bg-surface-alt px-3 py-2 text-xs text-text-muted">
            Showing 100 of {rows.length} rows
          </div>
        )}
      </div>
    </div>
  )
}
