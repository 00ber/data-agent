// -- Backend response types -----------------------------------------------

export interface DatasetInfo {
  id: string
  name: string
  description: string
  icon: string
  tables: number
  preview: string
}

export interface TableSummary {
  name: string
  rows: number
  columns: number
}

export interface ColumnMeta {
  name: string
  dtype: string
}

export interface TableMeta {
  name: string
  rows: number
  columns: ColumnMeta[]
}

// -- Artifact types -------------------------------------------------------

export interface ArtifactData {
  id: string
  kind: 'table' | 'chart' | 'stat'
  title: string
  data: Record<string, unknown>
}

export interface ChartData {
  chart_type: 'bar' | 'line' | 'scatter' | 'pie' | 'histogram'
  columns: string[]
  records: Record<string, unknown>[]
}

export interface TableData {
  columns: string[]
  rows: unknown[][]
  shape: [number, number]
}

export interface StatData {
  label: string
  value: unknown
}

// -- Agent event types ----------------------------------------------------

export type EventKind = 'thinking' | 'code' | 'artifact' | 'result' | 'answer' | 'error'

export interface AgentEvent {
  kind: EventKind
  data: Record<string, unknown>
}

// -- Analysis types (used in store) ---------------------------------------

export interface ProcessStep {
  kind: EventKind
  text: string
}

export interface AnalysisBlock {
  id: string
  query: string
  steps: ProcessStep[]
  artifacts: ArtifactData[]
  answer: string | null
  status: 'streaming' | 'complete' | 'error'
  collapsed: boolean
}
