import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listDatasets,
  createSession,
  loadSampleDataset,
  uploadFiles,
  getTables,
  getSuggestions,
  getArtifact,
  streamAsk,
} from '../api'
import type { AgentEvent } from '../types'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

function jsonResponse(data: unknown) {
  return { ok: true, json: () => Promise.resolve(data) }
}

describe('listDatasets', () => {
  it('fetches GET /api/datasets', async () => {
    const datasets = [{ id: 'ecommerce', name: 'E-Commerce' }]
    mockFetch.mockResolvedValueOnce(jsonResponse(datasets))
    const result = await listDatasets()
    expect(mockFetch).toHaveBeenCalledWith('/api/datasets')
    expect(result).toEqual(datasets)
  })
})

describe('createSession', () => {
  it('posts to /api/sessions and returns session_id', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ session_id: 'abc' }))
    const result = await createSession()
    expect(mockFetch).toHaveBeenCalledWith('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
    expect(result).toEqual({ session_id: 'abc' })
  })
})

describe('loadSampleDataset', () => {
  it('posts to load-sample endpoint', async () => {
    const tables = [{ name: 'orders', rows: 100, columns: 5 }]
    mockFetch.mockResolvedValueOnce(jsonResponse({ tables }))
    const result = await loadSampleDataset('s1', 'ecommerce')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/sessions/s1/load-sample/ecommerce',
      { method: 'POST' },
    )
    expect(result).toEqual({ tables })
  })
})

describe('uploadFiles', () => {
  it('posts multipart form data', async () => {
    const tables = [{ name: 'sales', rows: 50, columns: 3 }]
    mockFetch.mockResolvedValueOnce(jsonResponse({ tables }))
    const file = new File(['a,b\n1,2'], 'test.csv', { type: 'text/csv' })
    const result = await uploadFiles('s1', [file])
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/sessions/s1/upload',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(result).toEqual({ tables })
  })
})

describe('getTables', () => {
  it('fetches table metadata', async () => {
    const tables = [{ name: 'orders', rows: 100, columns: [{ name: 'id', dtype: 'int64' }] }]
    mockFetch.mockResolvedValueOnce(jsonResponse({ tables }))
    const result = await getTables('s1')
    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/s1/tables')
    expect(result).toEqual({ tables })
  })
})

describe('getSuggestions', () => {
  it('posts and returns suggestions', async () => {
    const suggestions = ['Revenue trends', 'Top customers']
    mockFetch.mockResolvedValueOnce(jsonResponse({ suggestions }))
    const result = await getSuggestions('s1')
    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/s1/suggestions', {
      method: 'POST',
    })
    expect(result).toEqual({ suggestions })
  })
})

describe('getArtifact', () => {
  it('fetches a specific artifact', async () => {
    const artifact = { id: 'art_1', kind: 'chart', title: 'Test', data: {} }
    mockFetch.mockResolvedValueOnce(jsonResponse(artifact))
    const result = await getArtifact('s1', 'art_1')
    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/s1/artifacts/art_1')
    expect(result).toEqual(artifact)
  })
})

function makeSSEStream(chunks: string[]) {
  let i = 0
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i]!))
        i++
      } else {
        controller.close()
      }
    },
  })
}

describe('streamAsk', () => {
  it('parses SSE events and calls onEvent', async () => {
    const events: AgentEvent[] = []
    const body = makeSSEStream([
      'event: thinking\ndata: {"text":"planning"}\n\n',
      'event: code\ndata: {"text":"x = 1"}\n\n',
      'event: answer\ndata: {"text":"done"}\n\n',
    ])
    mockFetch.mockResolvedValueOnce({ ok: true, body })
    const handle = streamAsk('s1', 'test query', (e) => events.push(e))
    await new Promise((r) => setTimeout(r, 50))
    expect(events).toHaveLength(3)
    expect(events[0]).toEqual({ kind: 'thinking', data: { text: 'planning' } })
    expect(events[1]).toEqual({ kind: 'code', data: { text: 'x = 1' } })
    expect(events[2]).toEqual({ kind: 'answer', data: { text: 'done' } })
  })

  it('handles chunked SSE lines split across reads', async () => {
    const events: AgentEvent[] = []
    const body = makeSSEStream([
      'event: think',
      'ing\ndata: {"text":"hi"}\n\n',
    ])
    mockFetch.mockResolvedValueOnce({ ok: true, body })
    streamAsk('s1', 'q', (e) => events.push(e))
    await new Promise((r) => setTimeout(r, 50))
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({ kind: 'thinking', data: { text: 'hi' } })
  })

  it('returns a close function that aborts the request', async () => {
    const body = makeSSEStream([])
    mockFetch.mockResolvedValueOnce({ ok: true, body })
    const handle = streamAsk('s1', 'q', () => {})
    expect(typeof handle.close).toBe('function')
  })
})
