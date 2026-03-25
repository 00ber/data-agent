import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { ChartData } from '../types'

const COLORS = ['#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626', '#0891b2', '#4f46e5', '#be185d']

interface ChartArtifactProps {
  data: ChartData
  title: string
}

export default function ChartArtifact({ data, title }: ChartArtifactProps) {
  const { chart_type, columns, records } = data
  const xKey = columns[0]!
  const yKeys = columns.slice(1)

  return (
    <div>
      {title && <h4 className="text-sm font-medium text-text mb-2">{title}</h4>}
      <ResponsiveContainer width="100%" height={300}>
        {renderChart(chart_type, xKey, yKeys, records)}
      </ResponsiveContainer>
    </div>
  )
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
