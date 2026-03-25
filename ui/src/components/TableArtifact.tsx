import type { TableData } from '../types'

interface TableArtifactProps {
  data: TableData
  title: string
}

export default function TableArtifact({ data, title }: TableArtifactProps) {
  const { columns, rows } = data
  const displayRows = rows.slice(0, 100) // Cap at 100 rows in view

  return (
    <div>
      {title && <h4 className="text-sm font-medium text-text mb-2">{title}</h4>}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-alt">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left font-medium text-text-secondary border-b border-border"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i} className="border-b border-border last:border-0 hover:bg-surface-alt/50">
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
          <div className="px-3 py-2 text-xs text-text-muted bg-surface-alt border-t border-border">
            Showing 100 of {rows.length} rows
          </div>
        )}
      </div>
    </div>
  )
}
