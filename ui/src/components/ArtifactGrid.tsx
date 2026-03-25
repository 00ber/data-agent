import { Maximize2, Download, Table } from 'lucide-react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
import type { ArtifactData, ChartData, TableData, StatData } from '../types'
import ChartArtifact from './ChartArtifact'
import TableArtifact from './TableArtifact'
import StatArtifact from './StatArtifact'

interface ArtifactGridProps {
  artifacts: ArtifactData[]
}

function downloadCSV(artifact: ArtifactData) {
  const data = artifact.data as unknown as TableData
  if (!data.columns || !data.rows) return
  const header = data.columns.join(',')
  const rows = data.rows.map((r) => (r as unknown[]).join(','))
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${artifact.title || 'data'}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function ArtifactGrid({ artifacts }: ArtifactGridProps) {
  const setOverlay = useStore((s) => s.setOverlay)

  return (
    <div className="space-y-4">
      {artifacts.map((artifact) => (
        <motion.div
          key={artifact.id}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="group relative"
        >
          {/* Hover actions */}
          <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <button
              onClick={() => setOverlay(artifact.id)}
              className="p-1.5 rounded-md bg-surface/90 border border-border hover:bg-surface-alt transition-colors"
              title="Expand"
            >
              <Maximize2 className="w-3.5 h-3.5 text-text-secondary" />
            </button>
            {(artifact.kind === 'table' || artifact.kind === 'chart') && (
              <button
                onClick={() => downloadCSV(artifact)}
                className="p-1.5 rounded-md bg-surface/90 border border-border hover:bg-surface-alt transition-colors"
                title="Download CSV"
              >
                <Download className="w-3.5 h-3.5 text-text-secondary" />
              </button>
            )}
            {artifact.kind === 'chart' && (
              <button
                onClick={() => setOverlay(artifact.id)}
                className="p-1.5 rounded-md bg-surface/90 border border-border hover:bg-surface-alt transition-colors"
                title="View data"
              >
                <Table className="w-3.5 h-3.5 text-text-secondary" />
              </button>
            )}
          </div>

          {/* Artifact content */}
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
      ))}
    </div>
  )
}
