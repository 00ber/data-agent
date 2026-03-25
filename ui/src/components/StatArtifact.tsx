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
    <div className="rounded-lg border border-border bg-surface p-4 text-center">
      <div className="text-2xl font-semibold text-text">{displayValue}</div>
      <div className="text-sm text-text-secondary mt-1">{title || data.label}</div>
    </div>
  )
}
