import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from '../store'

export default function DataPanel() {
  const tables = useStore((s) => s.tables)
  const dataPanelOpen = useStore((s) => s.dataPanelOpen)

  return (
    <AnimatePresence>
      {dataPanelOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="border-b border-border bg-surface-alt overflow-hidden"
        >
          <div className="px-4 py-4">
            <div className="flex flex-wrap gap-4">
              {tables.map((table) => (
                <div
                  key={table.name}
                  className="flex-1 min-w-64 rounded-lg border border-border bg-surface p-4"
                >
                  <div className="font-medium text-text mb-1">{table.name}</div>
                  <div className="text-xs text-text-muted mb-3">
                    {table.rows.toLocaleString()} rows &middot; {table.columns.length} columns
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {table.columns.map((col) => (
                      <span
                        key={col.name}
                        className="text-xs px-2 py-0.5 rounded bg-surface-alt text-text-secondary"
                      >
                        {col.name}{' '}
                        <span className="text-text-muted">({col.dtype})</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
