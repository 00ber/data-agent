import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the api module before importing store
vi.mock('../api', () => ({
  listDatasets: vi.fn(),
  createSession: vi.fn(),
  loadDataset: vi.fn(),
  uploadFiles: vi.fn(),
  getTables: vi.fn(),
  getSuggestions: vi.fn(),
  streamMessage: vi.fn(),
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
    mockedApi.loadDataset.mockResolvedValueOnce({
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
    mockedApi.loadDataset.mockResolvedValueOnce({ tables: [] })
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

    mockedApi.streamMessage.mockReturnValueOnce({ close: vi.fn() })

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
        turns: [],
        artifacts: [],
        answerBlocks: [
          { type: 'markdown', content: 'Answer' },
        ],
        status: 'complete',
        collapsed: false,
      }],
    })

    mockedApi.streamMessage.mockReturnValueOnce({ close: vi.fn() })

    await useStore.getState().ask('New question')

    const state = useStore.getState()
    expect(state.analyses).toHaveLength(2)
    expect(state.analyses[0]!.collapsed).toBe(true)
    expect(state.analyses[1]!.collapsed).toBe(false)
  })

  it('does nothing if no session', async () => {
    await useStore.getState().ask('test')

    expect(useStore.getState().analyses).toHaveLength(0)
    expect(mockedApi.streamMessage).not.toHaveBeenCalled()
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
        turns: [],
        artifacts: [],
        answerBlocks: null,
        status: 'streaming',
        collapsed: false,
      }],
    })

    // Simulate that _closeStream is set
    mockedApi.streamMessage.mockReturnValueOnce({ close: closeFn })
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
        turns: [],
        artifacts: [],
        answerBlocks: [
          { type: 'markdown', content: 'done' },
        ],
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

describe('artifact handling', () => {
  it('keeps artifact payloads on trace steps and stores structured final answer blocks', async () => {
    useStore.setState({ sessionId: 'sess_1' })

    mockedApi.getSuggestions.mockResolvedValueOnce({ suggestions: ['Follow-up'] })
    mockedApi.streamMessage.mockImplementation((_sessionId, _message, onEvent) => {
      onEvent({ kind: 'thinking', data: { text: 'Group revenue by segment.' } })
      onEvent({ kind: 'code', data: { text: 'grouped = group_by(...)' } })
      onEvent({
        kind: 'artifact',
        data: {
          id: 'art_1',
          kind: 'table',
          title: 'Grouped revenue',
          data: {
            columns: ['segment', 'total'],
            rows: [['Consumer', 1000]],
            shape: [1, 2],
          },
        },
      })
      onEvent({ kind: 'result', data: { text: 'Displayed table' } })
      onEvent({
        kind: 'answer',
        data: {
          blocks: [
            { type: 'markdown', content: 'Consumer leads.' },
            { type: 'artifact', artifact_id: 'art_1' },
          ],
        },
      })

      return { close: vi.fn() }
    })

    await useStore.getState().ask('Which segment leads?')

    const analysis = useStore.getState().analyses[0]!
    expect(analysis.turns[0]!.artifacts[0]!.id).toBe('art_1')
    expect(analysis.turns[0]!.result).toBe('Displayed table')
    expect(analysis.answerBlocks).toEqual([
      { type: 'markdown', content: 'Consumer leads.' },
      { type: 'artifact', artifact_id: 'art_1' },
    ])
  })

  it('groups one reasoning loop into one turn with thought, code, artifacts, and error', async () => {
    useStore.setState({ sessionId: 'sess_1' })

    mockedApi.streamMessage.mockImplementation((_sessionId, _message, onEvent) => {
      onEvent({ kind: 'thinking', data: { text: 'Try a grouped return-rate calculation.' } })
      onEvent({ kind: 'code', data: { text: 'joined = join(...)' } })
      onEvent({
        kind: 'artifact',
        data: {
          id: 'art_1',
          kind: 'table',
          title: 'Grouped totals',
          data: {
            columns: ['category', 'orders'],
            rows: [['Furniture', 10]],
            shape: [1, 2],
          },
        },
      })
      onEvent({ kind: 'error', data: { text: 'TypeError: unhashable type: list' } })

      return { close: vi.fn() }
    })

    await useStore.getState().ask('How do returns vary?')

    const analysis = useStore.getState().analyses[0]!
    expect(analysis.turns).toHaveLength(1)
    expect(analysis.turns[0]).toMatchObject({
      thought: 'Try a grouped return-rate calculation.',
      code: 'joined = join(...)',
      result: null,
      error: 'TypeError: unhashable type: list',
    })
    expect(analysis.turns[0]!.artifacts).toHaveLength(1)
    expect(analysis.answerBlocks).toBeNull()
  })
})
