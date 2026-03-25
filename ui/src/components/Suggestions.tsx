import { motion } from 'framer-motion'
import { useStore } from '../store'

export default function Suggestions() {
  const suggestions = useStore((s) => s.suggestions)
  const streaming = useStore((s) => s.streaming)
  const ask = useStore((s) => s.ask)
  const analyses = useStore((s) => s.analyses)

  if (suggestions.length === 0 || streaming) return null

  const heading = analyses.length > 0 ? 'Follow-up questions' : 'Try another angle'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.3 }}
      className="w-full rounded-[1.5rem] border border-border/60 bg-white/50 px-4 py-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)] backdrop-blur-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
          {heading}
        </p>
        <span className="text-xs text-text-muted">
          {suggestions.length} suggestion{suggestions.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, i) => (
          <motion.button
            key={suggestion}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i }}
            onClick={() => ask(suggestion)}
            className="rounded-full border border-border/80 bg-surface/75 px-3.5 py-2 text-sm text-text-secondary transition-colors hover:border-accent/25 hover:text-accent"
          >
            {suggestion}
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
