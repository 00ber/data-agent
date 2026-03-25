import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { ChartData } from '../types'

const COLORS = ['#0f766e', '#0284c7', '#7c3aed', '#ca8a04', '#dc2626', '#0f766e', '#4f46e5', '#be185d']

interface ChartArtifactProps {
  data: ChartData
  title: string
}

export default function ChartArtifact({ data, title }: ChartArtifactProps) {
  const { chart_type, columns, records } = data
  const chartModel = buildChartModel(chart_type, columns, records)

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-text">{title}</h4>
          <span className="rounded-full bg-surface-alt px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-text-muted">
            {chart_type}
          </span>
        </div>
      )}
      <div className="rounded-[1.25rem] border border-border bg-surface p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
        <ResponsiveContainer width="100%" height={320}>
          {renderChart(chart_type, chartModel.xKey, chartModel.yKeys, chartModel.records)}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function buildChartModel(
  type: string,
  columns: string[],
  records: Record<string, unknown>[],
) {
  const valueKinds = classifyColumns(columns, records)
  const numericKeys = columns.filter((column) => valueKinds[column] === 'number')
  const labelKeys = columns.filter((column) => valueKinds[column] !== 'number')

  if (type === 'scatter') {
    return {
      xKey: numericKeys[0] ?? columns[0]!,
      yKeys: [numericKeys[1] ?? numericKeys[0] ?? columns[1] ?? columns[0]!],
      records,
    }
  }

  if (type === 'pie') {
    return {
      xKey: labelKeys[0] ?? columns[0]!,
      yKeys: [numericKeys[0] ?? columns[1] ?? columns[0]!],
      records,
    }
  }

  if (labelKeys.length > 1 && numericKeys.length > 0) {
    return {
      xKey: '__label',
      yKeys: numericKeys,
      records: records.map((record) => ({
        ...record,
        __label: labelKeys.map((key) => String(record[key] ?? '')).join(' / '),
      })),
    }
  }

  return {
    xKey: labelKeys[0] ?? columns[0]!,
    yKeys: numericKeys.length > 0 ? numericKeys : columns.slice(1),
    records,
  }
}

function classifyColumns(
  columns: string[],
  records: Record<string, unknown>[],
): Record<string, 'number' | 'other'> {
  const kinds: Record<string, 'number' | 'other'> = {}

  for (const column of columns) {
    const firstValue = records.find((record) => record[column] !== null && record[column] !== undefined)?.[column]
    kinds[column] = typeof firstValue === 'number' ? 'number' : 'other'
  }

  return kinds
}

function renderChart(
  type: string,
  xKey: string,
  yKeys: string[],
  records: Record<string, unknown>[],
) {
  switch (type) {
    case 'bar':
    case 'histogram':
      return (
        <BarChart data={records}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {yKeys.length > 1 && <Legend />}
          {yKeys.map((key, i) => (
            <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} />
          ))}
        </BarChart>
      )
    case 'line':
      return (
        <LineChart data={records}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {yKeys.length > 1 && <Legend />}
          {yKeys.map((key, i) => (
            <Line key={key} dataKey={key} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
          ))}
        </LineChart>
      )
    case 'scatter':
      return (
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} name={xKey} />
          <YAxis dataKey={yKeys[0]} tick={{ fontSize: 12 }} name={yKeys[0]} />
          <Tooltip />
          <Scatter data={records} fill={COLORS[0]} />
        </ScatterChart>
      )
    case 'pie':
      return (
        <PieChart>
          <Pie
            data={records}
            dataKey={yKeys[0]!}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name }) => name}
          >
            {records.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      )
    default:
      return (
        <BarChart data={records}>
          <XAxis dataKey={xKey} />
          <YAxis />
          <Bar dataKey={yKeys[0]!} fill={COLORS[0]} />
        </BarChart>
      )
  }
}
