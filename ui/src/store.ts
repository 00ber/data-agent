import { create } from 'zustand'
import type { TableMeta, AnalysisBlock, ArtifactData, AgentEvent, TraceTurn } from './types'
import * as api from './api'

interface StoreState {
  // Session
  sessionId: string | null
  tables: TableMeta[]

  // Analysis
  analyses: AnalysisBlock[]
  currentAnalysisId: string | null
  streaming: boolean

  // UI
  view: 'onboarding' | 'analysis'
  dataPanelOpen: boolean
  overlay: { artifactId: string } | null
  suggestions: string[]

  // Actions
  createSession: () => Promise<void>
  loadDataset: (datasetId: string) => Promise<void>
  uploadFiles: (files: File[]) => Promise<void>
  ask: (message: string) => Promise<void>
  stopStreaming: () => void
  toggleCollapse: (analysisId: string) => void
  toggleDataPanel: () => void
  setOverlay: (artifactId: string | null) => void
}

// Internal: stored outside Zustand to avoid serialization issues
let _closeStream: (() => void) | null = null

function flushPendingArtifacts(block: AnalysisBlock): AnalysisBlock {
  if (block.pendingArtifactIds.length === 0) {
    return block
  }

  return {
    ...block,
    responseArtifactIds: block.pendingArtifactIds,
    pendingArtifactIds: [],
  }
}

function buildTurnId(): string {
  return crypto.randomUUID()
}

function buildEmptyTurn(thought: string): TraceTurn {
  return {
    id: buildTurnId(),
    thought,
    code: null,
    artifacts: [],
    result: null,
    error: null,
  }
}

function updateCurrentTurn(
  block: AnalysisBlock,
  update: (turn: TraceTurn) => TraceTurn,
): AnalysisBlock {
  if (block.turns.length === 0) {
    throw new Error('Cannot update a trace turn before a thinking event starts one.')
  }

  const turns = [...block.turns]
  const currentTurn = turns[turns.length - 1]
  turns[turns.length - 1] = update(currentTurn!)

  return {
    ...block,
    turns,
  }
}

function startTurn(block: AnalysisBlock, thought: string): AnalysisBlock {
  return {
    ...block,
    turns: [...block.turns, buildEmptyTurn(thought)],
  }
}

function appendArtifact(block: AnalysisBlock, artifact: ArtifactData): AnalysisBlock {
  const updatedBlock = updateCurrentTurn(block, (turn) => ({
    ...turn,
    artifacts: [...turn.artifacts, artifact],
  }))

  return {
    ...updatedBlock,
    artifacts: [...updatedBlock.artifacts, artifact],
    pendingArtifactIds: [...updatedBlock.pendingArtifactIds, artifact.id],
  }
}

function appendCode(block: AnalysisBlock, code: string): AnalysisBlock {
  return updateCurrentTurn(block, (turn) => ({ ...turn, code }))
}

function appendResult(block: AnalysisBlock, result: string): AnalysisBlock {
  const updatedBlock = flushPendingArtifacts(block)
  return updateCurrentTurn(updatedBlock, (turn) => ({ ...turn, result }))
}

function appendError(block: AnalysisBlock, error: string): AnalysisBlock {
  const updatedBlock = updateCurrentTurn(block, (turn) => ({ ...turn, error }))
  return {
    ...updatedBlock,
    pendingArtifactIds: [],
  }
}

function completeAnalysis(block: AnalysisBlock, answer: string): AnalysisBlock {
  const updatedBlock = flushPendingArtifacts(block)

  return {
    ...updatedBlock,
    answer,
    status: 'complete',
  }
}

export const useStore = create<StoreState>((set, get) => ({
  // Initial state
  sessionId: null,
  tables: [],
  analyses: [],
  currentAnalysisId: null,
  streaming: false,
  view: 'onboarding',
  dataPanelOpen: false,
  overlay: null,
  suggestions: [],

  // Actions
  createSession: async () => {
    const { session_id } = await api.createSession()
    set({ sessionId: session_id })
  },

  loadDataset: async (datasetId) => {
    let { sessionId } = get()
    if (!sessionId) {
      const { session_id } = await api.createSession()
      sessionId = session_id
      set({ sessionId })
    }
    await api.loadDataset(sessionId, datasetId)
    const { tables } = await api.getTables(sessionId)
    const { suggestions } = await api.getSuggestions(sessionId)
    set({ tables, suggestions, view: 'analysis' })
  },

  uploadFiles: async (files) => {
    let { sessionId } = get()
    if (!sessionId) {
      const { session_id } = await api.createSession()
      sessionId = session_id
      set({ sessionId })
    }
    await api.uploadFiles(sessionId, files)
    const { tables } = await api.getTables(sessionId)
    const { suggestions } = await api.getSuggestions(sessionId)
    set({ tables, suggestions, view: 'analysis' })
  },

  ask: async (message) => {
    const { sessionId, analyses } = get()
    if (!sessionId) return

    const id = crypto.randomUUID()
    const block: AnalysisBlock = {
      id,
      query: message,
      turns: [],
      artifacts: [],
      responseArtifactIds: [],
      pendingArtifactIds: [],
      answer: null,
      status: 'streaming',
      collapsed: false,
    }

    // Collapse previous blocks
    const collapsed = analyses.map((a) => ({ ...a, collapsed: true }))
    set({
      analyses: [...collapsed, block],
      currentAnalysisId: id,
      streaming: true,
      suggestions: [],
    })

    const onEvent = (event: AgentEvent) => {
      const { analyses } = get()
      const idx = analyses.findIndex((a) => a.id === id)
      if (idx === -1) return

      const current = analyses[idx]!
      let updated: AnalysisBlock

      switch (event.kind) {
        case 'thinking':
          updated = startTurn(current, String(event.data.text ?? ''))
          break
        case 'code':
          updated = appendCode(current, String(event.data.text ?? ''))
          break
        case 'artifact':
          updated = appendArtifact(current, event.data as unknown as ArtifactData)
          break
        case 'result':
          updated = appendResult(current, String(event.data.text ?? ''))
          break
        case 'error':
          updated = appendError(current, String(event.data.text ?? ''))
          break
        case 'answer':
          updated = completeAnalysis(current, String(event.data.text ?? ''))
          break
      }

      const newAnalyses = [...analyses]
      newAnalyses[idx] = updated
      set({ analyses: newAnalyses })

      if (event.kind === 'answer') {
        set({ streaming: false })
        _closeStream = null
        api.getSuggestions(sessionId).then(({ suggestions }) => {
          set({ suggestions })
        }).catch((err) => console.error('Failed to fetch suggestions:', err))
      }
    }

    const handle = api.streamMessage(sessionId, message, onEvent)
    _closeStream = handle.close
  },

  stopStreaming: () => {
    if (_closeStream) {
      _closeStream()
      _closeStream = null
    }
    const { analyses, currentAnalysisId } = get()
    set({
      streaming: false,
      analyses: analyses.map((a) =>
        a.id === currentAnalysisId ? { ...a, status: 'error' as const } : a,
      ),
    })
  },

  toggleCollapse: (analysisId) => {
    const { analyses } = get()
    set({
      analyses: analyses.map((a) =>
        a.id === analysisId ? { ...a, collapsed: !a.collapsed } : a,
      ),
    })
  },

  toggleDataPanel: () => {
    set((state) => ({ dataPanelOpen: !state.dataPanelOpen }))
  },

  setOverlay: (artifactId) => {
    set({ overlay: artifactId ? { artifactId } : null })
  },
}))
