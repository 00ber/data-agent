import { useCallback, useState } from 'react'
import { Upload } from 'lucide-react'

interface DropZoneProps {
  onFiles: (files: File[]) => void
}

export default function DropZone({ onFiles }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const files = Array.from(e.dataTransfer.files)
      if (files.length > 0) onFiles(files)
    },
    [onFiles],
  )

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? [])
      if (files.length > 0) onFiles(files)
    },
    [onFiles],
  )

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`flex flex-col items-center justify-center gap-3 p-8 rounded-xl
                  border-2 border-dashed cursor-pointer transition-colors duration-200
                  ${dragOver ? 'border-accent bg-accent/5' : 'border-border hover:border-text-muted'}`}
    >
      <Upload className="w-6 h-6 text-text-muted" />
      <span className="text-text-secondary">
        Drop CSV, XLSX, or Parquet files here
      </span>
      <span className="text-sm text-text-muted">or click to browse</span>
      <input
        type="file"
        multiple
        accept=".csv,.xlsx,.xls,.parquet"
        onChange={handleChange}
        className="hidden"
      />
    </label>
  )
}
