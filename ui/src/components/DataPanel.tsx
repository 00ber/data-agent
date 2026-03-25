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
          className="overflow-hidden border-b border-border/80 bg-[rgba(255,252,247,0.72)]"
        >
          <div className="mx-auto max-w-6xl px-4 py-4">
            <div className="flex flex-wrap gap-4">
              {tables.map((table) => (
                <div
                  key={table.name}
                  className="min-w-64 flex-1 rounded-[1.5rem] border border-border bg-surface p-4 shadow-[0_16px_48px_rgba(15,23,42,0.05)]"
                >
                  <div className="mb-1 font-medium text-text">{table.name}</div>
                  <div className="mb-3 text-xs text-text-muted">
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
