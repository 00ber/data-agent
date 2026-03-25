import type { AnalysisBlock as AnalysisBlockType } from '../types'
import { useStore } from '../store'
import ProcessSection from './ProcessSection'
import ArtifactGrid from './ArtifactGrid'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface AnalysisBlockProps {
  block: AnalysisBlockType
}

export default function AnalysisBlock({ block }: AnalysisBlockProps) {
  const toggleCollapse = useStore((s) => s.toggleCollapse)

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3
        className="font-medium text-text mb-3 cursor-pointer hover:text-accent transition-colors"
        onClick={() => toggleCollapse(block.id)}
      >
        {block.query}
      </h3>

      <ProcessSection
        steps={block.steps}
        collapsed={block.status === 'complete' || block.collapsed}
        onToggle={() => toggleCollapse(block.id)}
        status={block.status}
      />

      {block.artifacts.length > 0 && !block.collapsed && (
        <div className="mt-4">
          <ArtifactGrid artifacts={block.artifacts} />
        </div>
      )}

      {block.answer && !block.collapsed && (
        <div className="mt-4 text-sm text-text-secondary prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.answer}</ReactMarkdown>
        </div>
      )}

      {/* Collapsed preview: artifact indicators + answer excerpt */}
      {block.collapsed && (
        <>
          {block.artifacts.length > 0 && (
            <div className="flex gap-2 mt-2">
              {block.artifacts.map((a) => (
                <span key={a.id} className="text-xs px-2 py-0.5 rounded bg-surface-alt text-text-muted">
                  {a.kind === 'chart' ? '\u{1F4C8}' : a.kind === 'stat' ? '\u{1F4CA}' : '\u{1F4CB}'}{' '}
                  {a.title}
                </span>
              ))}
            </div>
          )}
          {block.answer && (
            <p className="mt-2 text-sm text-text-muted truncate">{block.answer}</p>
          )}
        </>
      )}
    </div>
  )
}
