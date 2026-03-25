import { Upload } from 'lucide-react'
import { useRef } from 'react'
import { useStore } from '../store'

export default function Header() {
  const uploadFiles = useStore((s) => s.uploadFiles)
  const fileRef = useRef<HTMLInputElement>(null)

  return (
    <header className="sticky top-0 z-20 border-b border-border/80 bg-[rgba(255,252,247,0.86)] backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text">DataAgent</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Trace every step, inspect every artifact, and keep your analysis grounded.
          </p>
        </div>
      <button
        onClick={() => fileRef.current?.click()}
        className="flex items-center gap-2 rounded-2xl border border-border bg-surface px-4 py-2.5
                   text-sm font-medium text-text-secondary shadow-[0_10px_30px_rgba(15,23,42,0.05)]
                   transition-colors hover:bg-surface-alt"
      >
        <Upload className="w-4 h-4" />
        Upload
      </button>
      </div>
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
