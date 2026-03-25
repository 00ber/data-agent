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
      className="flex items-center gap-2 px-4 py-3 border-t border-border bg-surface"
    >
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ask about your data..."
        disabled={streaming}
        className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface
                   text-text placeholder:text-text-muted focus:outline-none focus:border-accent
                   disabled:opacity-50"
      />
      {streaming ? (
        <button
          type="button"
          onClick={stopStreaming}
          className="p-2 rounded-lg bg-error text-white hover:bg-error/90 transition-colors"
        >
          <Square className="w-4 h-4" />
        </button>
      ) : (
        <button
          type="submit"
          disabled={!text.trim()}
          className="p-2 rounded-lg bg-accent text-white hover:bg-accent-hover
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      )}
    </form>
  )
}
