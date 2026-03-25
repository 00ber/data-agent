import { ChevronRight, ChevronDown, Loader2, Check, AlertCircle } from 'lucide-react'
import type { ProcessStep } from '../types'

interface ProcessSectionProps {
  steps: ProcessStep[]
  collapsed: boolean
  onToggle: () => void
  status: 'streaming' | 'complete' | 'error'
}

function StepIcon({ kind, isLast, streaming }: { kind: string; isLast: boolean; streaming: boolean }) {
  if (isLast && streaming) return <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
  if (kind === 'error') return <AlertCircle className="w-3.5 h-3.5 text-error" />
  return <Check className="w-3.5 h-3.5 text-success" />
}

export default function ProcessSection({ steps, collapsed, onToggle, status }: ProcessSectionProps) {
  if (steps.length === 0) return null

  const artifactCount = steps.filter((s) => s.kind === 'artifact').length
  const summary = `${steps.length} steps${artifactCount > 0 ? ` \u00B7 ${artifactCount} artifacts` : ''}`

  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary
                   transition-colors py-1"
      >
        <ChevronRight className="w-3.5 h-3.5" />
        {summary}
      </button>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-surface-alt p-3">
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary
                   transition-colors mb-2"
      >
        <ChevronDown className="w-3.5 h-3.5" />
        Process
      </button>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-2">
            <div className="mt-0.5">
              <StepIcon
                kind={step.kind}
                isLast={i === steps.length - 1}
                streaming={status === 'streaming'}
              />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-xs font-medium text-text-secondary capitalize">
                {step.kind}
              </span>
              <pre
                className={`text-xs mt-0.5 whitespace-pre-wrap break-words
                  ${step.kind === 'code' ? 'font-mono bg-surface p-2 rounded border border-border' : ''}
                  ${step.kind === 'error' ? 'text-error' : 'text-text-secondary'}`}
              >
                {step.text}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
