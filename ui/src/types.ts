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

// -- Final answer blocks --------------------------------------------------

export interface MarkdownAnswerBlockData {
  type: 'markdown'
  content: string
}

export interface ArtifactAnswerBlockData {
  type: 'artifact'
  artifact_id: string
}

export type AnswerBlockData = MarkdownAnswerBlockData | ArtifactAnswerBlockData

// -- Agent event types ----------------------------------------------------

export type EventKind = 'thinking' | 'code' | 'artifact' | 'result' | 'answer' | 'error'

export interface AgentEvent {
  kind: EventKind
  data: Record<string, unknown>
}

// -- Analysis types (used in store) ---------------------------------------

export interface TraceTurn {
  id: string
  thought: string
  code: string | null
  artifacts: ArtifactData[]
  result: string | null
  error: string | null
}

export interface AnalysisBlock {
  id: string
  query: string
  turns: TraceTurn[]
  artifacts: ArtifactData[]
  answerBlocks: AnswerBlockData[] | null
  status: 'streaming' | 'complete' | 'error'
  collapsed: boolean
}
