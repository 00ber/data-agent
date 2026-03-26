import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
} from 'lucide-react'

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

function turnBadgeClass(turn: TraceTurn, isSelected: boolean): string {
  if (turn.error) {
    return isSelected
      ? 'border-error/40 bg-error/10'
      : 'border-error/20 bg-error/5'
  }
  if (turn.result) {
    return isSelected
      ? 'border-success/30 bg-success/10'
      : 'border-border/70 bg-surface/70'
  }
  return isSelected
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
  if (turns.length === 0) return null

  const [selectedTurnId, setSelectedTurnId] = useState<string>(turns[turns.length - 1]!.id)
  const artifactCount = turns.reduce((count, turn) => count + turn.artifacts.length, 0)
  const summary = `${turns.length} turns${artifactCount > 0 ? ` · ${artifactCount} artifacts` : ''}`
  const latestTurn = turns[turns.length - 1]!
  const selectedTurn = useMemo(
    () => turns.find((turn) => turn.id === selectedTurnId) ?? latestTurn,
    [latestTurn, selectedTurnId, turns],
  )

  useEffect(() => {
    if (!turns.some((turn) => turn.id === selectedTurnId)) {
      setSelectedTurnId(latestTurn.id)
    }
  }, [latestTurn.id, selectedTurnId, turns])

  if (!expanded) {
    return (
      <button
        onClick={onToggle}
        aria-label="Behind the answer"
        className="mt-4 flex w-full items-center justify-between rounded-2xl border border-border/70
                   bg-white/55 px-4 py-4 text-left text-sm text-text-secondary transition-colors
                   hover:border-accent/20 hover:text-text"
      >
        <div className="min-w-0">
          <span className="flex items-center gap-2">
            <ChevronRight className="h-4 w-4" />
            <span className="font-medium text-text">Behind the answer</span>
          </span>
          <p className="mt-1 truncate text-sm text-text-secondary">
            {previewThought(latestTurn)}
          </p>
        </div>
        <span className="shrink-0 pl-4 text-xs uppercase tracking-[0.16em] text-text-muted">
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
        <div className="min-w-0">
          <span className="flex items-center gap-2">
            <ChevronDown className="h-4 w-4 text-text-muted" />
            <span className="text-sm font-semibold text-text">Behind the answer</span>
          </span>
          <p className="mt-1 text-sm text-text-secondary">
            Open the reasoning workspace to inspect one turn at a time.
          </p>
        </div>
        <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
          {summary}
        </span>
      </button>

      <div className="grid gap-4 p-4 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside className="rounded-[1.15rem] border border-border/60 bg-surface/65 p-3">
          <div className="mb-3 flex items-center gap-2 px-1">
            <Sparkles className="h-4 w-4 text-accent" />
            <span className="text-sm font-semibold text-text">Reasoning workspace</span>
          </div>

          <div className="space-y-2">
            {turns.map((turn, index) => {
              const isSelected = turn.id === selectedTurn.id
              const isLiveTurn = index === turns.length - 1 && status === 'streaming'

              return (
                <button
                  key={turn.id}
                  aria-label={`Turn ${index + 1}`}
                  onClick={() => setSelectedTurnId(turn.id)}
                  className={`w-full rounded-2xl border px-3 py-3 text-left transition-colors ${turnBadgeClass(turn, isSelected)}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
                      Turn {index + 1}
                    </span>
                    {isLiveTurn && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Live
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm leading-6 text-text">
                    {previewThought(turn)}
                  </p>

                  <div className="mt-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-text-muted">
                    <span>{turnSummary(turn)}</span>
                    {turn.artifacts.length > 0 && (
                      <span>{turn.artifacts.length} artifacts</span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </aside>

        <div className="rounded-[1.15rem] border border-border/60 bg-surface/75 px-4 py-4">
          <div className="mb-4 flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-text">Selected turn</span>
            <span className="text-xs uppercase tracking-[0.16em] text-text-muted">
              {turnSummary(selectedTurn)}
            </span>
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
              {turns.findIndex((turn) => turn.id === selectedTurn.id) + 1}
            </span>
            {selectedTurn.error && (
              <span className="inline-flex items-center gap-1 rounded-full bg-error/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-error">
                <AlertCircle className="h-3.5 w-3.5" />
                Error
              </span>
            )}
            {!selectedTurn.error && selectedTurn.result && (
              <span className="rounded-full bg-success/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-success">
                Complete
              </span>
            )}
          </div>

          <div>
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
              Thought
            </div>
            <p className="rounded-2xl bg-surface px-3 py-3 text-sm leading-6 text-text">
              {selectedTurn.thought}
            </p>
          </div>

          {selectedTurn.code && (
            <div className="mt-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                Code
              </div>
              <pre className="whitespace-pre-wrap break-words rounded-2xl border border-border bg-[#111827] px-3 py-3 text-sm leading-6 text-[#f8fafc]">
                {selectedTurn.code}
              </pre>
            </div>
          )}

          {selectedTurn.artifacts.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                Intermediate artifacts
              </div>
              <ArtifactGrid artifacts={selectedTurn.artifacts} showHeader={false} />
            </div>
          )}

          {selectedTurn.result && (
            <div className="mt-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
                Result
              </div>
              <p className="rounded-2xl bg-surface px-3 py-3 text-sm leading-6 text-text-secondary">
                {selectedTurn.result}
              </p>
            </div>
          )}

          {selectedTurn.error && (
            <div className="mt-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-error">
                Error
              </div>
              <p className="rounded-2xl bg-error/6 px-3 py-3 text-sm leading-6 text-error">
                {selectedTurn.error}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
