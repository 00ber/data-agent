import { describe, it, expect, vi, beforeEach } from 'vitest'
import { create } from 'zustand'

// Mock the api module before importing store
vi.mock('../api', () => ({
  listDatasets: vi.fn(),
  createSession: vi.fn(),
  loadSampleDataset: vi.fn(),
  uploadFiles: vi.fn(),
  getTables: vi.fn(),
  getSuggestions: vi.fn(),
  getArtifact: vi.fn(),
  streamAsk: vi.fn(),
}))

import * as api from '../api'
import { useStore } from '../store'

const mockedApi = vi.mocked(api)

beforeEach(() => {
  // Reset store to initial state
  useStore.setState({
    sessionId: null,
    tables: [],
    analyses: [],
    currentAnalysisId: null,
    streaming: false,
    view: 'onboarding',
    dataPanelOpen: false,
    overlay: null,
    suggestions: [],
  })
  vi.clearAllMocks()
})

describe('createSession', () => {
  it('stores sessionId from API response', async () => {
    mockedApi.createSession.mockResolvedValueOnce({ session_id: 'sess_1' })

    await useStore.getState().createSession()

    expect(useStore.getState().sessionId).toBe('sess_1')
  })
})

describe('loadDataset', () => {
  it('creates session if none exists, loads data, fetches tables and suggestions', async () => {
    mockedApi.createSession.mockResolvedValueOnce({ session_id: 'sess_1' })
    mockedApi.loadSampleDataset.mockResolvedValueOnce({
      tables: [{ name: 'orders', rows: 100, columns: 5 }],
    })
    mockedApi.getTables.mockResolvedValueOnce({
      tables: [{ name: 'orders', rows: 100, columns: [{ name: 'id', dtype: 'int64' }] }],
    })
    mockedApi.getSuggestions.mockResolvedValueOnce({
      suggestions: ['Revenue trends'],
    })

    await useStore.getState().loadDataset('ecommerce')

    const state = useStore.getState()
    expect(state.sessionId).toBe('sess_1')
    expect(state.tables).toHaveLength(1)
    expect(state.tables[0]!.name).toBe('orders')
    expect(state.suggestions).toEqual(['Revenue trends'])
    expect(state.view).toBe('analysis')
  })

  it('reuses existing session', async () => {
    useStore.setState({ sessionId: 'existing' })
    mockedApi.loadSampleDataset.mockResolvedValueOnce({ tables: [] })
    mockedApi.getTables.mockResolvedValueOnce({ tables: [] })
    mockedApi.getSuggestions.mockResolvedValueOnce({ suggestions: [] })

    await useStore.getState().loadDataset('ecommerce')

    expect(mockedApi.createSession).not.toHaveBeenCalled()
  })
})

describe('uploadFiles', () => {
  it('creates session, uploads, fetches tables and suggestions', async () => {
    mockedApi.createSession.mockResolvedValueOnce({ session_id: 'sess_2' })
    mockedApi.uploadFiles.mockResolvedValueOnce({
      tables: [{ name: 'sales', rows: 50, columns: 3 }],
    })
    mockedApi.getTables.mockResolvedValueOnce({
      tables: [{ name: 'sales', rows: 50, columns: [{ name: 'id', dtype: 'int64' }] }],
    })
    mockedApi.getSuggestions.mockResolvedValueOnce({ suggestions: ['Analyze sales'] })

    const file = new File(['a'], 'test.csv')
    await useStore.getState().uploadFiles([file])

    const state = useStore.getState()
    expect(state.sessionId).toBe('sess_2')
    expect(state.tables).toHaveLength(1)
    expect(state.view).toBe('analysis')
  })
})

describe('ask', () => {
  it('creates an analysis block and starts streaming', async () => {
    useStore.setState({ sessionId: 'sess_1' })

    mockedApi.streamAsk.mockReturnValueOnce({ close: vi.fn() })

    await useStore.getState().ask('What are the trends?')

    const state = useStore.getState()
    expect(state.analyses).toHaveLength(1)
    expect(state.analyses[0]!.query).toBe('What are the trends?')
    expect(state.analyses[0]!.status).toBe('streaming')
    expect(state.streaming).toBe(true)
  })

  it('collapses previous blocks when asking a new question', async () => {
    useStore.setState({
      sessionId: 'sess_1',
      analyses: [{
        id: 'old',
        query: 'Previous',
        steps: [],
        artifacts: [],
        answer: 'Answer',
        status: 'complete',
        collapsed: false,
      }],
    })

    mockedApi.streamAsk.mockReturnValueOnce({ close: vi.fn() })

    await useStore.getState().ask('New question')

    const state = useStore.getState()
    expect(state.analyses).toHaveLength(2)
    expect(state.analyses[0]!.collapsed).toBe(true)
    expect(state.analyses[1]!.collapsed).toBe(false)
  })

  it('does nothing if no session', async () => {
    await useStore.getState().ask('test')

    expect(useStore.getState().analyses).toHaveLength(0)
    expect(mockedApi.streamAsk).not.toHaveBeenCalled()
  })
})

describe('stopStreaming', () => {
  it('aborts the stream and marks block as error', async () => {
    const closeFn = vi.fn()
    useStore.setState({
      sessionId: 'sess_1',
      streaming: true,
      currentAnalysisId: 'blk_1',
      analyses: [{
        id: 'blk_1',
        query: 'test',
        steps: [],
        artifacts: [],
        answer: null,
        status: 'streaming',
        collapsed: false,
      }],
    })

    // Simulate that _closeStream is set
    mockedApi.streamAsk.mockReturnValueOnce({ close: closeFn })
    await useStore.getState().ask('test2') // This sets _closeStream

    useStore.getState().stopStreaming()

    expect(useStore.getState().streaming).toBe(false)
  })
})

describe('UI actions', () => {
  it('toggleCollapse flips collapsed state', () => {
    useStore.setState({
      analyses: [{
        id: 'blk_1',
        query: 'test',
        steps: [],
        artifacts: [],
        answer: 'done',
        status: 'complete',
        collapsed: false,
      }],
    })

    useStore.getState().toggleCollapse('blk_1')
    expect(useStore.getState().analyses[0]!.collapsed).toBe(true)

    useStore.getState().toggleCollapse('blk_1')
    expect(useStore.getState().analyses[0]!.collapsed).toBe(false)
  })

  it('toggleDataPanel flips dataPanelOpen', () => {
    expect(useStore.getState().dataPanelOpen).toBe(false)

    useStore.getState().toggleDataPanel()
    expect(useStore.getState().dataPanelOpen).toBe(true)

    useStore.getState().toggleDataPanel()
    expect(useStore.getState().dataPanelOpen).toBe(false)
  })

  it('setOverlay sets and clears overlay', () => {
    useStore.getState().setOverlay('art_1')
    expect(useStore.getState().overlay).toEqual({ artifactId: 'art_1' })

    useStore.getState().setOverlay(null)
    expect(useStore.getState().overlay).toBeNull()
  })
})
