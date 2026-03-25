import { motion } from 'framer-motion'
import { useStore } from '../store'

export default function Suggestions() {
  const suggestions = useStore((s) => s.suggestions)
  const streaming = useStore((s) => s.streaming)
  const ask = useStore((s) => s.ask)

  if (suggestions.length === 0 || streaming) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.3 }}
      className="flex flex-col items-center gap-2 py-4"
    >
      {suggestions.map((suggestion, i) => (
        <motion.button
          key={suggestion}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 * i }}
          onClick={() => ask(suggestion)}
          className="text-sm text-accent hover:text-accent-hover hover:underline transition-colors"
        >
          {suggestion}
        </motion.button>
      ))}
    </motion.div>
  )
}
