import type { StatData } from '../types'

interface StatArtifactProps {
  data: StatData
  title: string
}

export default function StatArtifact({ data, title }: StatArtifactProps) {
  const displayValue =
    typeof data.value === 'number'
      ? data.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : String(data.value)

  return (
    <div className="rounded-[1.25rem] border border-border bg-[linear-gradient(145deg,rgba(255,255,255,0.92),rgba(240,249,255,0.9))] p-5 text-center shadow-[0_16px_48px_rgba(15,23,42,0.06)]">
      <div className="text-3xl font-semibold tracking-tight text-text">{displayValue}</div>
      <div className="mt-2 text-sm text-text-secondary">{title || data.label}</div>
    </div>
  )
}
