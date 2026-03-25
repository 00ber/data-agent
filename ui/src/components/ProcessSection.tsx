import { AlertCircle, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'

import type { TraceTurn } from '../types'
import ArtifactGrid from './ArtifactGrid'

interface ProcessSectionProps {
  turns: TraceTurn[]
  expanded: boolean
  onToggle: () => void
  status: 'streaming' | 'complete' | 'error'
}

function turnSummary(turn: TraceTurn): string {
  if (turn.error) {
    return 'Ended with an error'
  }
  if (turn.result) {
    return 'Produced an execution result'
  }
  return 'In progress'
}

export default function ProcessSection({
  turns,
  expanded,
  onToggle,
  status,
}: ProcessSectionProps) {
  if (turns.length === 0) return null

  const artifactCount = turns.reduce((count, turn) => count + turn.artifacts.length, 0)
  const summary = `${turns.length} turns${artifactCount > 0 ? ` · ${artifactCount} artifacts` : ''}`

  if (!expanded) {
    return (
      <button
        onClick={onToggle}
        className="mt-4 flex w-full items-center justify-between rounded-2xl border border-border/70
                   bg-white/55 px-4 py-3 text-left text-sm text-text-secondary transition-colors
                   hover:border-accent/20 hover:text-text"
      >
        <span className="flex items-center gap-2">
          <ChevronRight className="h-4 w-4" />
          <span className="font-medium text-text">Reasoning trace</span>
        </span>
        <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
          {summary}
        </span>
      </button>
    )
  }

  return (
    <section className="mt-4 overflow-hidden rounded-[1.35rem] border border-border/70 bg-white/45 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between border-b border-border/60
                   bg-white/40 px-4 py-3 text-left transition-colors hover:bg-white/55"
      >
        <span className="flex items-center gap-2">
          <ChevronDown className="h-4 w-4 text-text-muted" />
          <span className="text-sm font-semibold text-text">Reasoning trace</span>
        </span>
        <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
          {summary}
        </span>
      </button>

      <div className="space-y-3 p-4">
        {turns.map((turn, index) => {
          const isLiveTurn = index === turns.length - 1 && status === 'streaming'

          return (
            <div
              key={turn.id}
              className="rounded-[1.15rem] border border-border/60 bg-surface/55 px-4 py-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                      Turn {index + 1}
                    </span>
                    {turn.error && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-error/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-error">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Error
                      </span>
                    )}
                    {!turn.error && turn.result && (
                      <span className="rounded-full bg-success/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-success">
                        Complete
                      </span>
                    )}
                    {isLiveTurn && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Live
                      </span>
                    )}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-text">
                    {turn.thought}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-text-muted">
                  {turnSummary(turn)}
                </span>
              </div>

              <div className="mt-4">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                  Thought
                </div>
                <p className="rounded-2xl bg-surface px-3 py-3 text-sm leading-6 text-text">
                  {turn.thought}
                </p>
              </div>

              {turn.code && (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                    Code
                  </div>
                  <pre className="whitespace-pre-wrap break-words rounded-2xl border border-border bg-[#111827] px-3 py-3 text-sm leading-6 text-[#f8fafc]">
                    {turn.code}
                  </pre>
                </div>
              )}

              {turn.artifacts.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                    Artifacts
                  </div>
                  <ArtifactGrid artifacts={turn.artifacts} showHeader={false} />
                </div>
              )}

              {turn.result && (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                    Result
                  </div>
                  <p className="rounded-2xl bg-surface px-3 py-3 text-sm leading-6 text-text-secondary">
                    {turn.result}
                  </p>
                </div>
              )}

              {turn.error && (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-error">
                    Error
                  </div>
                  <p className="rounded-2xl bg-error/6 px-3 py-3 text-sm leading-6 text-error">
                    {turn.error}
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
