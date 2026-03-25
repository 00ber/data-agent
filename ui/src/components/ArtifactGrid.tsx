import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Download, Maximize2, Table } from 'lucide-react'
import { motion } from 'framer-motion'

import { useStore } from '../store'
import type { ArtifactData, ChartData, TableData, StatData } from '../types'
import ChartArtifact from './ChartArtifact'
import TableArtifact from './TableArtifact'
import StatArtifact from './StatArtifact'

interface ArtifactGridProps {
  artifacts: ArtifactData[]
  title?: string
  showHeader?: boolean
  expandByDefault?: boolean
}

function downloadCSV(artifact: ArtifactData) {
  const data = artifact.data as unknown as TableData
  if (!data.columns || !data.rows) return

  const header = data.columns.join(',')
  const rows = data.rows.map((row) => (row as unknown[]).join(','))
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${artifact.title || 'data'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function artifactSummary(artifact: ArtifactData) {
  if (artifact.kind === 'table') {
    const table = artifact.data as unknown as TableData
    return `${table.shape[0]} rows · ${table.shape[1]} columns`
  }

  if (artifact.kind === 'chart') {
    const chart = artifact.data as unknown as ChartData
    return `${chart.records.length} points · ${chart.columns.join(' × ')}`
  }

  const stat = artifact.data as unknown as StatData
  return `${stat.label}: ${String(stat.value)}`
}

export default function ArtifactGrid({
  artifacts,
  title = 'Artifacts',
  showHeader = true,
  expandByDefault = false,
}: ArtifactGridProps) {
  const setOverlay = useStore((state) => state.setOverlay)
  const [expandedArtifactIds, setExpandedArtifactIds] = useState<string[]>(
    expandByDefault ? artifacts.map((artifact) => artifact.id) : [],
  )

  const toggleArtifact = (artifactId: string) => {
    setExpandedArtifactIds((current) =>
      current.includes(artifactId)
        ? current.filter((id) => id !== artifactId)
        : [...current, artifactId],
    )
  }

  useEffect(() => {
    if (!expandByDefault) return
    setExpandedArtifactIds(artifacts.map((artifact) => artifact.id))
  }, [artifacts, expandByDefault])

  const content = (
    <div className="space-y-3 p-4">
        {artifacts.map((artifact, index) => {
          const isExpanded = expandedArtifactIds.includes(artifact.id)

          return (
            <motion.div
              key={artifact.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: index * 0.04 }}
              className="overflow-hidden rounded-2xl border border-border/80 bg-surface-alt/50"
            >
              <div className="flex items-center justify-between gap-3 px-3 py-3">
                <button
                  onClick={() => toggleArtifact(artifact.id)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                  aria-expanded={isExpanded}
                  aria-label={artifact.title || `Artifact ${index + 1}`}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-text-muted" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-text-muted" />
                  )}
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-semibold text-text">
                        {artifact.title || `Artifact ${index + 1}`}
                      </span>
                      <span className="rounded-full bg-surface px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                        {artifact.kind}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-xs text-text-muted">
                      {artifactSummary(artifact)}
                    </p>
                  </div>
                </button>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setOverlay(artifact.id)}
                    className="rounded-xl border border-border bg-surface p-2 text-text-secondary transition-colors hover:bg-surface-alt hover:text-text"
                    title="Open in overlay"
                  >
                    <Maximize2 className="h-3.5 w-3.5" />
                  </button>
                  {(artifact.kind === 'table' || artifact.kind === 'chart') && (
                    <button
                      onClick={() => downloadCSV(artifact)}
                      className="rounded-xl border border-border bg-surface p-2 text-text-secondary transition-colors hover:bg-surface-alt hover:text-text"
                      title="Download CSV"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {artifact.kind === 'chart' && (
                    <button
                      onClick={() => setOverlay(artifact.id)}
                      className="rounded-xl border border-border bg-surface p-2 text-text-secondary transition-colors hover:bg-surface-alt hover:text-text"
                      title="Inspect chart data"
                    >
                      <Table className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-border/70 bg-surface px-3 py-4">
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
                </div>
              )}
            </motion.div>
          )
        })}
    </div>
  )

  if (!showHeader) {
    return <div className="mt-3">{content}</div>
  }

  return (
    <section className="mt-4 overflow-hidden rounded-[1.5rem] border border-border/80 bg-surface shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
      <div className="border-b border-border/70 bg-surface-alt/70 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-semibold text-text">{title}</span>
          <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
            {artifacts.length} total
          </span>
        </div>
      </div>
      {content}
    </section>
  )
}
