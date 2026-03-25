import { create } from 'zustand'
import type { TableMeta, AnalysisBlock, ArtifactData, AgentEvent } from './types'
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
    await api.loadSampleDataset(sessionId, datasetId)
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
      steps: [],
      artifacts: [],
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

      if (event.kind === 'artifact') {
        updated = {
          ...current,
          steps: [...current.steps, { kind: 'artifact', text: (event.data.title as string) || '' }],
          artifacts: [...current.artifacts, event.data as unknown as ArtifactData],
        }
      } else if (event.kind === 'answer') {
        updated = {
          ...current,
          answer: event.data.text as string,
          status: 'complete',
        }
      } else {
        updated = {
          ...current,
          steps: [...current.steps, { kind: event.kind, text: (event.data.text as string) || '' }],
        }
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

    const handle = api.streamAsk(sessionId, message, onEvent)
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
