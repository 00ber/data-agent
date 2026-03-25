import { Upload } from 'lucide-react'
import { useRef } from 'react'
import { useStore } from '../store'

export default function Header() {
  const uploadFiles = useStore((s) => s.uploadFiles)
  const fileRef = useRef<HTMLInputElement>(null)

  return (
    <header className="flex items-center justify-between px-4 py-3 border-b border-border">
      <h1 className="text-lg font-semibold text-text">DataAgent</h1>
      <button
        onClick={() => fileRef.current?.click()}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg
                   text-text-secondary hover:bg-surface-alt transition-colors"
      >
        <Upload className="w-4 h-4" />
        Upload
      </button>
      <input
        ref={fileRef}
        type="file"
        multiple
        accept=".csv,.xlsx,.xls,.parquet"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length > 0) uploadFiles(files)
        }}
        className="hidden"
      />
    </header>
  )
}
