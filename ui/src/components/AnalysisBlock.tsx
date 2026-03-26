import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'

import type { AnalysisBlock as AnalysisBlockType } from '../types'
import { useStore } from '../store'
import ProcessSection from './ProcessSection'
import AnswerBlocks from './AnswerBlocks'

interface AnalysisBlockProps {
  block: AnalysisBlockType
  isFirst?: boolean
}

function isReferencedArtifact(
  artifact: AnalysisBlockType['artifacts'][number] | null,
): artifact is AnalysisBlockType['artifacts'][number] {
  return artifact !== null
}

function buildAnswerPreview(block: AnalysisBlockType): string | null {
  if (!block.answerBlocks) {
    return null
  }

  const markdownParts = block.answerBlocks
    .filter((answerBlock) => answerBlock.type === 'markdown')
    .map((answerBlock) => answerBlock.content.trim())
    .filter((content) => content.length > 0)

  if (markdownParts.length === 0) {
    return null
  }

  return markdownParts.join('\n\n')
}

function statusLabel(status: AnalysisBlockType['status']) {
  switch (status) {
    case 'streaming':
      return 'Running'
    case 'reviewing':
      return 'Finalizing response'
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
    case 'reviewing':
      return 'bg-[rgba(245,158,11,0.12)] text-[rgb(180,83,9)]'
    case 'complete':
      return 'bg-success/10 text-success'
    case 'error':
      return 'bg-error/10 text-error'
  }
}

export default function AnalysisBlock({ block, isFirst = false }: AnalysisBlockProps) {
  const toggleCollapse = useStore((state) => state.toggleCollapse)
  const [processExpanded, setProcessExpanded] = useState(false)

  const turnCount = block.turns.length
  const thoughtLabel = turnCount === 1 ? 'thought' : 'thoughts'
  const artifactCount = block.artifacts.length
  const isExpanded = !block.collapsed
  const isProcessExpanded =
    block.status === 'streaming' || block.status === 'reviewing'
      ? true
      : processExpanded
  const answerPreview = buildAnswerPreview(block)
  const referencedArtifacts = useMemo(
    () =>
      (block.answerBlocks ?? [])
        .filter((answerBlock) => answerBlock.type === 'artifact')
        .map(
          (answerBlock) =>
            block.artifacts.find((artifact) => artifact.id === answerBlock.artifact_id) ?? null,
        )
        .filter(isReferencedArtifact),
    [block.answerBlocks, block.artifacts],
  )

  return (
    <article className={`py-7 ${isFirst ? 'pt-0' : ''}`}>
      <div className="flex justify-end">
        <div className="max-w-3xl rounded-[1.65rem] border border-border/70 bg-[rgba(255,250,243,0.96)] px-5 py-4 shadow-[0_10px_30px_rgba(15,23,42,0.04)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
            You
          </p>
          <p className="mt-2 text-[15px] leading-7 text-text">
            {block.query}
          </p>
        </div>
      </div>

      <div className="mt-5 flex gap-4">
        <div className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-accent/70" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${statusClass(block.status)}`}
                >
                  {(block.status === 'streaming' || block.status === 'reviewing') && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  )}
                  {statusLabel(block.status)}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                  {turnCount} {thoughtLabel}
                </span>
                {artifactCount > 0 && (
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                    {artifactCount} artifacts
                  </span>
                )}
              </div>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-secondary">
                {block.status === 'streaming'
                  ? 'Live reasoning trace and intermediate outputs update as the agent works.'
                  : block.status === 'reviewing'
                    ? 'The analysis is complete. Final response review is synthesizing the answer from the handoff and supporting artifacts.'
                    : 'Review the answer, inspect the trace, and open intermediate artifacts when you need to verify how the conclusion was produced.'}
              </p>
            </div>
            <button
              onClick={() => toggleCollapse(block.id)}
              className="rounded-2xl border border-border/70 bg-white/75 p-2 text-text-secondary transition-colors hover:border-accent/20 hover:text-text"
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
      </div>

      {!isExpanded && (
        <div className="ml-6 mt-4 space-y-3">
          {answerPreview && (
            <p className="max-w-3xl text-sm leading-7 text-text-secondary line-clamp-3">
              {answerPreview}
            </p>
          )}
          {(artifactCount > 0 || turnCount > 0) && (
            <div className="flex flex-wrap gap-2">
              {turnCount > 0 && (
                <span className="rounded-full bg-surface-alt px-3 py-1 text-xs text-text-muted">
                  Trace available
                </span>
              )}
              {referencedArtifacts.map((artifact) => (
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
        <div className="ml-6 mt-5">
          {block.answerBlocks && (
            <section className="max-w-4xl border-l-2 border-accent/18 pl-6">
              <AnswerBlocks blocks={block.answerBlocks} artifacts={block.artifacts} />
            </section>
          )}

          <ProcessSection
            turns={block.turns}
            expanded={isProcessExpanded}
            onToggle={() => setProcessExpanded((current) => !current)}
            status={block.status}
          />
        </div>
      )}
    </article>
  )
}
