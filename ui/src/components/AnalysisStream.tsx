import { useRef, useEffect } from 'react'
import { useStore } from '../store'
import AnalysisBlock from './AnalysisBlock'

export default function AnalysisStream() {
  const analyses = useStore((s) => s.analyses)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [analyses])

  if (analyses.length === 0) return null

  return (
    <div className="w-full divide-y divide-border/45">
      {analyses.map((block, index) => (
        <AnalysisBlock key={block.id} block={block} isFirst={index === 0} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
