import type { DatasetInfo } from '../types'
import { ShoppingCart, Store, Globe } from 'lucide-react'

const ICONS: Record<string, React.ElementType> = {
  'shopping-cart': ShoppingCart,
  store: Store,
  globe: Globe,
}

interface DatasetCardProps {
  dataset: DatasetInfo
  onSelect: (id: string) => void
}

export default function DatasetCard({ dataset, onSelect }: DatasetCardProps) {
  const Icon = ICONS[dataset.icon] ?? Globe

  return (
    <button
      onClick={() => onSelect(dataset.id)}
      className="flex flex-col items-center gap-3 p-6 rounded-xl border border-border bg-surface
                 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer
                 text-left w-52"
    >
      <Icon className="w-8 h-8 text-accent" />
      <span className="font-medium text-text">{dataset.name}</span>
      <span className="text-sm text-text-secondary text-center">{dataset.description}</span>
      <span className="text-xs text-text-muted">{dataset.tables} tables</span>
    </button>
  )
}
