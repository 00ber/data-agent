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
  answerBlocks: [
    {
      type: 'markdown',
      content: 'Consumer leads revenue.',
    },
    {
      type: 'artifact',
      artifact_id: 'artifact-1',
    },
  ],
  status: 'complete',
  collapsed: false,
}

const emptyStreamingBlock: AnalysisBlockType = {
  id: 'analysis-streaming',
  query: 'Which region leads revenue?',
  turns: [],
  artifacts: [],
  answerBlocks: null,
  status: 'streaming',
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

  it('keeps the trace collapsed behind a summary bar after a run completes', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.getByText('Trace')).toBeTruthy()
    expect(
      screen.queryByText('grouped = group_by("orders", "segment", "total", "sum")'),
    ).toBeNull()
  })

  it('expands response artifacts by default and still lets trace artifacts toggle open', () => {
    render(<AnalysisBlock block={completedBlock} />)

    const initialConsumerCells = screen.getAllByText('Consumer').length

    fireEvent.click(screen.getByRole('button', { name: /trace/i }))
    fireEvent.click(screen.getByRole('button', { name: /trace thought 1/i }))
    fireEvent.click(screen.getByRole('button', { name: /revenue by segment/i }))

    expect(screen.getAllByText('Consumer').length).toBeGreaterThan(initialConsumerCells)
  })

  it('renders inline answer blocks and removes the old evidence header', () => {
    render(<AnalysisBlock block={completedBlock} />)

    expect(screen.queryByText('Final answer')).toBeNull()
    expect(screen.queryByText('Evidence')).toBeNull()
    expect(screen.getByText('Consumer leads revenue.')).toBeTruthy()
    expect(screen.getAllByText('Revenue by segment').length).toBeGreaterThan(0)
  })

  it('opens a row-based trace without selecting the first thought by default', () => {
    render(<AnalysisBlock block={completedBlock} />)

    fireEvent.click(screen.getByRole('button', { name: /trace/i }))

    expect(screen.getByRole('button', { name: /trace thought 1/i })).toBeTruthy()
    expect(screen.queryByText('Thought')).toBeNull()
    expect(screen.queryByText('Result')).toBeNull()
    expect(
      screen.queryByText('grouped = group_by("orders", "segment", "total", "sum")'),
    ).toBeNull()
  })

  it('keeps expanded-thought code collapsed until explicitly opened', () => {
    render(<AnalysisBlock block={completedBlock} />)

    fireEvent.click(screen.getByRole('button', { name: /trace/i }))
    fireEvent.click(screen.getByRole('button', { name: /trace thought 1/i }))

    expect(
      screen.queryByText('grouped = group_by("orders", "segment", "total", "sum")'),
    ).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /show code/i }))

    expect(
      screen.getByText('grouped = group_by("orders", "segment", "total", "sum")'),
    ).toBeTruthy()
  })

  it('can transition from no turns to a live turn without tripping React hook state', () => {
    const { rerender } = render(<AnalysisBlock block={emptyStreamingBlock} />)

    rerender(
      <AnalysisBlock
        block={{
          ...emptyStreamingBlock,
          turns: [
            {
              id: 'turn-live',
              thought: 'Compare revenue by region.',
              code: 'grouped = group_by("orders", "region", "total", "sum")',
              artifacts: [],
              result: null,
              error: null,
            },
          ],
        }}
      />,
    )

    expect(screen.getAllByText('Compare revenue by region.').length).toBeGreaterThan(0)
    expect(screen.getByText('Trace')).toBeTruthy()
  })
})
