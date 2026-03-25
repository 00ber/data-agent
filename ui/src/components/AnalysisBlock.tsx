import { useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import type { AnalysisBlock as AnalysisBlockType } from '../types'
import { useStore } from '../store'
import ProcessSection from './ProcessSection'
import ArtifactGrid from './ArtifactGrid'

interface AnalysisBlockProps {
  block: AnalysisBlockType
}

function isDefinedArtifact(
  artifact: AnalysisBlockType['artifacts'][number] | null,
): artifact is AnalysisBlockType['artifacts'][number] {
  return artifact !== null
}

function statusLabel(status: AnalysisBlockType['status']) {
  switch (status) {
    case 'streaming':
      return 'Running'
    case 'complete':
      return 'Complete'
    case 'error':
      return 'Needs review'
  }
}

function statusClass(status: AnalysisBlockType['status']) {
  switch (status) {
    case 'streaming':
      return 'bg-accent/10 text-accent'
    case 'complete':
      return 'bg-success/10 text-success'
    case 'error':
      return 'bg-error/10 text-error'
  }
}

export default function AnalysisBlock({ block }: AnalysisBlockProps) {
  const toggleCollapse = useStore((state) => state.toggleCollapse)
  const [processExpanded, setProcessExpanded] = useState(true)

  const turnCount = block.turns.length
  const artifactCount = block.artifacts.length
  const isExpanded = !block.collapsed
  const responseArtifacts = block.responseArtifactIds
    .map((artifactId) => block.artifacts.find((artifact) => artifact.id === artifactId) ?? null)
    .filter(isDefinedArtifact)

  return (
    <article className="overflow-hidden rounded-[1.75rem] border border-border/80 bg-surface shadow-[0_30px_80px_rgba(15,23,42,0.08)]">
      <div className="border-b border-border/70 bg-[linear-gradient(135deg,rgba(16,185,129,0.08),rgba(14,165,233,0.04),rgba(255,255,255,0.9))] px-5 py-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${statusClass(block.status)}`}
              >
                {block.status === 'streaming' && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {statusLabel(block.status)}
              </span>
              <span className="rounded-full bg-surface/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                {turnCount} turns
              </span>
              {artifactCount > 0 && (
                <span className="rounded-full bg-surface/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                  {artifactCount} artifacts
                </span>
              )}
            </div>
            <h3 className="mt-3 text-xl font-semibold leading-8 text-text">
              {block.query}
            </h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
              {block.status === 'streaming'
                ? 'Live reasoning trace and intermediate outputs update as the agent works.'
                : 'Review the answer, inspect the trace, and open intermediate artifacts when you need to verify how the conclusion was produced.'}
            </p>
          </div>
          <button
            onClick={() => toggleCollapse(block.id)}
            className="rounded-2xl border border-border bg-surface/80 p-2.5 text-text-secondary transition-colors hover:bg-surface hover:text-text"
            aria-label={isExpanded ? 'Collapse analysis' : 'Expand analysis'}
          >
            {isExpanded ? (
              <ChevronDown className="h-5 w-5" />
            ) : (
              <ChevronRight className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {!isExpanded && (
        <div className="space-y-3 px-5 py-4">
          {block.answer && (
            <p className="text-sm leading-6 text-text-secondary line-clamp-2">
              {block.answer}
            </p>
          )}
          {(artifactCount > 0 || turnCount > 0) && (
            <div className="flex flex-wrap gap-2">
              {turnCount > 0 && (
                <span className="rounded-full bg-surface-alt px-3 py-1 text-xs text-text-muted">
                  Trace available
                </span>
              )}
              {responseArtifacts.map((artifact) => (
                <span
                  key={artifact.id}
                  className="rounded-full bg-surface-alt px-3 py-1 text-xs text-text-muted"
                >
                  {artifact.title}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {isExpanded && (
        <div className="px-5 py-5">
          {block.answer && (
            <section className="rounded-[1.5rem] border border-border/80 bg-surface-alt/60 p-5 shadow-[0_16px_48px_rgba(15,23,42,0.05)]">
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-text-muted">
                  Final answer
                </h4>
                <span className="rounded-full bg-surface px-3 py-1 text-xs text-text-muted">
                  Ready to share
                </span>
              </div>
              <div className="prose prose-sm mt-4 max-w-none text-text-secondary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.answer}</ReactMarkdown>
              </div>
              {responseArtifacts.length > 0 && (
                <ArtifactGrid
                  artifacts={responseArtifacts}
                  title="Evidence"
                  expandByDefault
                />
              )}
            </section>
          )}

          <ProcessSection
            turns={block.turns}
            expanded={processExpanded}
            onToggle={() => setProcessExpanded((current) => !current)}
            status={block.status}
          />
        </div>
      )}
    </article>
  )
}
