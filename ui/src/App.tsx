import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from './store'
import Onboarding from './components/Onboarding'
import Header from './components/Header'
import DataBar from './components/DataBar'
import DataPanel from './components/DataPanel'
import AnalysisStream from './components/AnalysisStream'
import Suggestions from './components/Suggestions'
import InputBar from './components/InputBar'
import ArtifactOverlay from './components/ArtifactOverlay'

export default function App() {
  const view = useStore((s) => s.view)

  return (
    <>
      <AnimatePresence mode="wait">
        {view === 'onboarding' ? (
          <motion.div
            key="onboarding"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.3 }}
          >
            <Onboarding />
          </motion.div>
        ) : (
          <motion.div
            key="analysis"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="flex min-h-screen flex-col bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.10),_transparent_28%),linear-gradient(180deg,_rgba(255,255,255,0.92),_rgba(247,243,235,0.88))]"
          >
            <Header />
            <DataBar />
            <DataPanel />
            <main className="mx-auto flex w-full max-w-6xl flex-1 overflow-y-auto px-4 py-8">
              <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
                <AnalysisStream />
                <Suggestions />
              </div>
            </main>
            <InputBar />
          </motion.div>
        )}
      </AnimatePresence>
      <ArtifactOverlay />
    </>
  )
}
