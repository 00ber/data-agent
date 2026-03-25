import type {
  DatasetInfo,
  TableSummary,
  TableMeta,
  ArtifactData,
  AgentEvent,
  EventKind,
} from './types'

// -- Helpers --------------------------------------------------------------

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${text || res.statusText}`)
  }
  return res.json()
}

// -- REST functions -------------------------------------------------------

export async function listDatasets(): Promise<DatasetInfo[]> {
  const res = await fetch('/api/datasets')
  return jsonOrThrow(res)
}

export async function createSession(
  config: { model?: string; temperature?: number } = {},
): Promise<{ session_id: string }> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return jsonOrThrow(res)
}

export async function loadSampleDataset(
  sessionId: string,
  datasetId: string,
): Promise<{ tables: TableSummary[] }> {
  const res = await fetch(`/api/sessions/${sessionId}/load-sample/${datasetId}`, {
    method: 'POST',
  })
  return jsonOrThrow(res)
}

export async function uploadFiles(
  sessionId: string,
  files: File[],
): Promise<{ tables: TableSummary[] }> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const res = await fetch(`/api/sessions/${sessionId}/upload`, {
    method: 'POST',
    body: form,
  })
  return jsonOrThrow(res)
}

export async function getTables(
  sessionId: string,
): Promise<{ tables: TableMeta[] }> {
  const res = await fetch(`/api/sessions/${sessionId}/tables`)
  return jsonOrThrow(res)
}

export async function getSuggestions(
  sessionId: string,
): Promise<{ suggestions: string[] }> {
  const res = await fetch(`/api/sessions/${sessionId}/suggestions`, {
    method: 'POST',
  })
  return jsonOrThrow(res)
}

export async function getArtifact(
  sessionId: string,
  artifactId: string,
): Promise<ArtifactData> {
  const res = await fetch(`/api/sessions/${sessionId}/artifacts/${artifactId}`)
  return jsonOrThrow(res)
}

// -- SSE stream -----------------------------------------------------------

export function streamAsk(
  sessionId: string,
  message: string,
  onEvent: (event: AgentEvent) => void,
): { close: () => void } {
  const controller = new AbortController()

  const promise = fetch(`/api/sessions/${sessionId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })

  promise.then(async (response) => {
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts.pop()!

      let currentEvent = ''
      for (const line of parts) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ') && currentEvent) {
          const data = JSON.parse(line.slice(6))
          onEvent({ kind: currentEvent as EventKind, data })
          currentEvent = ''
        }
      }
    }
  }).catch(() => {
    // AbortError is expected when close() is called
  })

  return { close: () => controller.abort() }
}
