import { Maximize2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { useStore } from '../store'
import type {
  AnswerBlockData,
  ArtifactAnswerBlockData,
  ArtifactData,
  ChartData,
  MarkdownAnswerBlockData,
  StatData,
  TableData,
} from '../types'
import ChartArtifact from './ChartArtifact'
import StatArtifact from './StatArtifact'
import TableArtifact from './TableArtifact'

interface AnswerBlocksProps {
  blocks: AnswerBlockData[]
  artifacts: ArtifactData[]
}

function findArtifact(
  artifacts: ArtifactData[],
  block: ArtifactAnswerBlockData,
): ArtifactData | null {
  return artifacts.find((artifact) => artifact.id === block.artifact_id) ?? null
}

function renderArtifactBody(artifact: ArtifactData) {
  if (artifact.kind === 'chart') {
    return (
      <ChartArtifact
        data={artifact.data as unknown as ChartData}
        title={artifact.title}
      />
    )
  }

  if (artifact.kind === 'table') {
    return (
      <TableArtifact
        data={artifact.data as unknown as TableData}
        title={artifact.title}
      />
    )
  }

  return (
    <StatArtifact
      data={artifact.data as unknown as StatData}
      title={artifact.title}
    />
  )
}

function MarkdownBlock({ block }: { block: MarkdownAnswerBlockData }) {
  return (
    <div className="answer-markdown max-w-none text-text-secondary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-3xl font-semibold tracking-[-0.02em] text-text">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-8 text-2xl font-semibold tracking-[-0.02em] text-text">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-6 text-lg font-semibold text-text">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="mt-4 text-[15px] leading-8 text-text-secondary first:mt-0">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="mt-4 list-disc space-y-2 pl-6 text-[15px] leading-8 text-text-secondary">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="mt-4 list-decimal space-y-2 pl-6 text-[15px] leading-8 text-text-secondary">
              {children}
            </ol>
          ),
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-text">{children}</strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mt-4 border-l-2 border-accent/35 pl-4 italic text-text-secondary">
              {children}
            </blockquote>
          ),
          code: ({ children }) => (
            <code className="rounded-md bg-surface-alt px-1.5 py-0.5 text-[0.9em] text-text">
              {children}
            </code>
          ),
        }}
      >
        {block.content}
      </ReactMarkdown>
    </div>
  )
}

export default function AnswerBlocks({ blocks, artifacts }: AnswerBlocksProps) {
  const setOverlay = useStore((state) => state.setOverlay)

  return (
    <div className="space-y-5">
      {blocks.map((block, index) => {
        if (block.type === 'markdown') {
          return <MarkdownBlock key={`markdown-${index}`} block={block} />
        }

        const artifact = findArtifact(artifacts, block)
        if (!artifact) return null

        return (
          <section
            key={artifact.id}
            className="overflow-hidden rounded-[1.5rem] border border-border/70 bg-surface/85 shadow-[0_18px_40px_rgba(15,23,42,0.04)]"
          >
            <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-surface-alt/40 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-text">
                  {artifact.title}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.16em] text-text-muted">
                  {artifact.kind}
                </p>
              </div>
              <button
                onClick={() => setOverlay(artifact.id)}
                className="rounded-xl border border-border bg-surface p-2 text-text-secondary transition-colors hover:bg-surface-alt hover:text-text"
                title="Open in overlay"
              >
                <Maximize2 className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="px-5 py-5">
              {renderArtifactBody(artifact)}
            </div>
          </section>
        )
      })}
    </div>
  )
}
