import { useEffect, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useStore } from '../store'
import type { ArtifactData, ChartData, TableData, StatData } from '../types'
import ChartArtifact from './ChartArtifact'
import TableArtifact from './TableArtifact'
import StatArtifact from './StatArtifact'

export default function ArtifactOverlay() {
  const overlay = useStore((s) => s.overlay)
  const analyses = useStore((s) => s.analyses)
  const setOverlay = useStore((s) => s.setOverlay)

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOverlay(null)
    },
    [setOverlay],
  )

  useEffect(() => {
    if (overlay) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [overlay, handleKeyDown])

  // Find the artifact across all analyses
  let artifact: ArtifactData | undefined
  if (overlay) {
    for (const block of analyses) {
      artifact = block.artifacts.find((a) => a.id === overlay.artifactId)
      if (artifact) break
    }
  }

  return (
    <AnimatePresence>
      {overlay && artifact && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setOverlay(null)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="relative bg-surface rounded-xl border border-border shadow-xl
                       max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setOverlay(null)}
              className="absolute top-3 right-3 p-1.5 rounded-lg hover:bg-surface-alt transition-colors"
            >
              <X className="w-5 h-5 text-text-secondary" />
            </button>

            {artifact.kind === 'chart' && (
              <ChartArtifact
                data={artifact.data as unknown as ChartData}
                title={artifact.title}
              />
            )}
            {artifact.kind === 'table' && (
              <TableArtifact
                data={artifact.data as unknown as TableData}
                title={artifact.title}
              />
            )}
            {artifact.kind === 'stat' && (
              <StatArtifact
                data={artifact.data as unknown as StatData}
                title={artifact.title}
              />
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
