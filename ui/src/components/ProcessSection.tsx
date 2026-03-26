import { useEffect, useState } from 'react'
import { AlertCircle, ChevronDown, ChevronRight, Code2 } from 'lucide-react'

import type { TraceTurn } from '../types'
import ArtifactGrid from './ArtifactGrid'

interface ProcessSectionProps {
  turns: TraceTurn[]
  expanded: boolean
  onToggle: () => void
  status: 'streaming' | 'reviewing' | 'complete' | 'error'
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

function turnBadgeClass(turn: TraceTurn, isExpanded: boolean): string {
  if (turn.error) {
    return isExpanded
      ? 'border-error/40 bg-error/10'
      : 'border-error/20 bg-error/5'
  }
  if (turn.result) {
    return isExpanded
      ? 'border-success/30 bg-success/10'
      : 'border-border/70 bg-surface/70'
  }
  return isExpanded
    ? 'border-accent/35 bg-accent/10'
    : 'border-border/70 bg-surface/70'
}

function previewThought(turn: TraceTurn): string {
  if (turn.thought.length <= 96) {
    return turn.thought
  }
  return `${turn.thought.slice(0, 93)}...`
}

export default function ProcessSection({
  turns,
  expanded,
  onToggle,
  status,
}: ProcessSectionProps) {
  const latestTurn = turns[turns.length - 1] ?? null
  const [expandedTurnId, setExpandedTurnId] = useState<string | null>(null)
  const [codeTurnId, setCodeTurnId] = useState<string | null>(null)
  const artifactCount = turns.reduce((count, turn) => count + turn.artifacts.length, 0)
  const thoughtLabel = turns.length === 1 ? 'thought' : 'thoughts'
  const artifactLabel = artifactCount === 1 ? 'artifact' : 'artifacts'
  const summary = `${turns.length} ${thoughtLabel}${artifactCount > 0 ? ` · ${artifactCount} ${artifactLabel}` : ''}`

  useEffect(() => {
    if (latestTurn === null) {
      if (expandedTurnId !== null) {
        setExpandedTurnId(null)
      }
      if (codeTurnId !== null) {
        setCodeTurnId(null)
      }
      return
    }

    if (expandedTurnId !== null && !turns.some((turn) => turn.id === expandedTurnId)) {
      setExpandedTurnId(null)
    }
    if (codeTurnId !== null && !turns.some((turn) => turn.id === codeTurnId)) {
      setCodeTurnId(null)
    }
  }, [codeTurnId, expandedTurnId, latestTurn, turns])

  if (latestTurn === null) {
    return null
  }

  if (!expanded) {
    return (
      <button
        onClick={onToggle}
        aria-label="Trace"
        className="mt-5 flex w-full items-center justify-between rounded-2xl border border-border/55
                   bg-white/45 px-4 py-3 text-left text-sm text-text-secondary transition-colors
                   hover:border-accent/18 hover:text-text"
      >
        <div className="min-w-0">
          <span className="flex items-center gap-2">
            <ChevronRight className="h-4 w-4" />
            <span className="text-[12px] font-semibold uppercase tracking-[0.16em] text-text">Trace</span>
          </span>
          <p className="mt-1 truncate text-sm leading-6 text-text-secondary">
            {previewThought(latestTurn)}
          </p>
        </div>
        <span className="shrink-0 pl-4 text-[11px] uppercase tracking-[0.16em] text-text-muted">
          {summary}
        </span>
      </button>
    )
  }

  return (
    <section className="mt-5 overflow-hidden rounded-[1.2rem] border border-border/55 bg-white/35">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between border-b border-border/55
                   bg-white/30 px-4 py-3 text-left transition-colors hover:bg-white/45"
      >
        <div className="min-w-0">
          <span className="flex items-center gap-2">
            <ChevronDown className="h-4 w-4 text-text-muted" />
            <span className="text-[12px] font-semibold uppercase tracking-[0.16em] text-text">Trace</span>
          </span>
          <p className="mt-1 text-sm text-text-secondary">
            Open any thought to inspect its details.
          </p>
        </div>
        <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
          {summary}
        </span>
      </button>

      <div className="space-y-3 p-4">
        {status === 'reviewing' && (
          <div className="rounded-2xl border border-[rgba(245,158,11,0.16)] bg-[rgba(255,251,235,0.78)] px-3 py-3 text-sm leading-6 text-[rgb(146,64,14)]">
            Analysis is complete. The agent is reviewing the handoff and composing the final response.
          </div>
        )}

        {turns.map((turn, index) => {
          const isExpanded = turn.id === expandedTurnId
          const isLiveTurn = index === turns.length - 1 && status === 'streaming'
          const isCodeExpanded = codeTurnId === turn.id
          const turnArtifactLabel = turn.artifacts.length === 1 ? 'artifact' : 'artifacts'

          return (
            <article
              key={turn.id}
              className={`overflow-hidden rounded-[1.1rem] border transition-colors ${turnBadgeClass(turn, isExpanded)}`}
            >
              <button
                aria-label={`Trace thought ${index + 1}`}
                onClick={() => {
                  setExpandedTurnId((current) => (current === turn.id ? null : turn.id))
                  if (expandedTurnId === turn.id) {
                    setCodeTurnId(null)
                  }
                }}
                className="flex w-full items-start justify-between gap-3 px-4 py-3.5 text-left"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {isLiveTurn && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                        Live
                      </span>
                    )}
                    {turn.error && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-error/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-error">
                        <AlertCircle className="h-3 w-3" />
                        Error
                      </span>
                    )}
                    {!turn.error && turn.result && (
                      <span className="rounded-full bg-success/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-success">
                        Complete
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm leading-6 text-text">
                    {previewThought(turn)}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-text-muted">
                    <span>{turnSummary(turn)}</span>
                    {turn.artifacts.length > 0 && (
                      <span>{turn.artifacts.length} {turnArtifactLabel}</span>
                    )}
                  </div>
                </div>

                {isExpanded ? (
                  <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
                ) : (
                  <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
                )}
              </button>

              {isExpanded && (
                <div className="border-t border-border/55 bg-white/35 px-4 py-4">
                  <div>
                    <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                      Thought
                    </div>
                    <p className="rounded-2xl bg-surface/80 px-3 py-3 text-sm leading-6 text-text">
                      {turn.thought}
                    </p>
                  </div>

                  {turn.code && (
                    <div className="mt-4">
                      <button
                        onClick={() =>
                          setCodeTurnId((current) => (current === turn.id ? null : turn.id))
                        }
                        className="flex w-full items-center justify-between rounded-2xl border border-border/65 bg-surface/80 px-3 py-3 text-left transition-colors hover:border-accent/20 hover:text-text"
                        aria-label={isCodeExpanded ? 'Hide code' : 'Show code'}
                      >
                        <span className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                          <Code2 className="h-3.5 w-3.5" />
                          Code
                        </span>
                        {isCodeExpanded ? (
                          <ChevronDown className="h-4 w-4 text-text-muted" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-text-muted" />
                        )}
                      </button>

                      {isCodeExpanded && (
                        <pre className="mt-3 whitespace-pre-wrap break-words rounded-2xl border border-border bg-[#111827] px-3 py-3 text-sm leading-6 text-[#f8fafc]">
                          {turn.code}
                        </pre>
                      )}
                    </div>
                  )}

                  {turn.artifacts.length > 0 && (
                    <div className="mt-4">
                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                        Intermediate artifacts
                      </div>
                      <ArtifactGrid artifacts={turn.artifacts} showHeader={false} />
                    </div>
                  )}

                  {turn.result && (
                    <div className="mt-4">
                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                        Result
                      </div>
                      <p className="rounded-2xl bg-surface/80 px-3 py-3 text-sm leading-6 text-text-secondary">
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
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
