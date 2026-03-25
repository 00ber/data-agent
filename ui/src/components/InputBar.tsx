import { useState } from 'react'
import { Send, Square } from 'lucide-react'
import { useStore } from '../store'

export default function InputBar() {
  const [text, setText] = useState('')
  const streaming = useStore((s) => s.streaming)
  const ask = useStore((s) => s.ask)
  const stopStreaming = useStore((s) => s.stopStreaming)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || streaming) return
    setText('')
    ask(trimmed)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 border-t border-border/80 bg-[rgba(255,252,247,0.88)] backdrop-blur-xl"
    >
      <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-4 py-4">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask a question, inspect a trend, or compare a segment..."
          disabled={streaming}
          className="flex-1 rounded-2xl border border-border bg-surface px-4 py-3
                     text-text shadow-[0_12px_36px_rgba(15,23,42,0.05)] placeholder:text-text-muted
                     focus:border-accent focus:outline-none disabled:opacity-50"
        />
        {streaming ? (
          <button
            type="button"
            onClick={stopStreaming}
            className="rounded-2xl bg-error px-4 py-3 text-white transition-colors hover:bg-error/90"
          >
            <Square className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!text.trim()}
            className="rounded-2xl bg-accent px-4 py-3 text-white shadow-[0_12px_36px_rgba(15,118,110,0.28)]
                       transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>
    </form>
  )
}
