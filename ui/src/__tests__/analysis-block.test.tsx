import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import AnalysisBlock from '../components/AnalysisBlock'
import { useStore } from '../store'
import type { AnalysisBlock as AnalysisBlockType } from '../types'

const completedBlock: AnalysisBlockType = {
  id: 'analysis-1',
  query: 'Which customer segments generate the highest revenue?',
  turns: [
    {
      id: 'turn-1',
      thought: 'Inspect revenue by segment and region.',
      code: 'grouped = group_by("orders", "segment", "total", "sum")',
      artifacts: [
        {
          id: 'artifact-1',
          kind: 'table',
          title: 'Revenue by segment',
          data: {
            columns: ['segment', 'total'],
            rows: [['Consumer', 1000], ['SMB', 500]],
            shape: [2, 2],
          },
        },
      ],
      result: 'Done',
      error: null,
    },
  ],
  artifacts: [
    {
      id: 'artifact-1',
      kind: 'table',
      title: 'Revenue by segment',
      data: {
        columns: ['segment', 'total'],
        rows: [['Consumer', 1000], ['SMB', 500]],
        shape: [2, 2],
      },
    },
  ],
  responseArtifactIds: ['artifact-1'],
  pendingArtifactIds: [],
  answer: 'Consumer leads revenue.',
  status: 'complete',
  collapsed: false,
}


describe('AnalysisBlock', () => {
  beforeEach(() => {
    useStore.setState({
      sessionId: null,
      tables: [],
      analyses: [],
      currentAnalysisId: null,
      streaming: false,
      view: 'analysis',
      dataPanelOpen: false,
      overlay: null,
      suggestions: [],
    })
  })

  it('keeps the process trace visible after a run completes', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.getByText('Reasoning trace')).toBeTruthy()
    expect(screen.getAllByText('Inspect revenue by segment and region.').length).toBeGreaterThan(0)
    expect(
      screen.getByText('grouped = group_by("orders", "segment", "total", "sum")'),
    ).toBeTruthy()
  })

  it('expands response artifacts by default and still lets trace artifacts toggle open', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.getByText('Consumer')).toBeTruthy()

    fireEvent.click(screen.getAllByRole('button', { name: /revenue by segment/i })[1]!)

    expect(screen.getAllByText('Consumer').length).toBeGreaterThan(0)
  })

  it('shows response artifacts near the final answer and not as a global artifact dump', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.getByText('Evidence')).toBeTruthy()
    expect(screen.getByText(/^Artifacts$/)).toBeTruthy()
  })

  it('renders grouped reasoning turns instead of a flat event list', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.getByText('Turn 1')).toBeTruthy()
    expect(screen.getByText('Thought')).toBeTruthy()
    expect(screen.getByText('Code')).toBeTruthy()
    expect(screen.getByText('Result')).toBeTruthy()
  })
})
