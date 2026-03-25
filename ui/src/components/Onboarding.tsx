import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../store'
import { listDatasets } from '../api'
import type { DatasetInfo } from '../types'
import DatasetCard from './DatasetCard'
import DropZone from './DropZone'

export default function Onboarding() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const loadDataset = useStore((s) => s.loadDataset)
  const uploadFiles = useStore((s) => s.uploadFiles)

  useEffect(() => {
    listDatasets().then(setDatasets).catch(() => {})
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-10 p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        <h1 className="text-3xl font-semibold text-text mb-2">DataAgent</h1>
        <p className="text-text-secondary">Explore your data with AI</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex gap-4"
      >
        {datasets.map((ds) => (
          <DatasetCard key={ds.id} dataset={ds} onSelect={loadDataset} />
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-text-muted text-sm"
      >
        — or —
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="w-full max-w-lg"
      >
        <DropZone onFiles={uploadFiles} />
      </motion.div>
    </div>
  )
}
