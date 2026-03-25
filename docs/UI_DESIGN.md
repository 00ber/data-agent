# UI Design Plan

## Context

The current frontend (`apps/web/frontend/`) is a standard AI chat UI — sidebar,
chat bubbles, tool call results tucked into accordions. It works, but it treats
analytics artifacts as secondary content inside a messaging interface.

This plan replaces it with an **artifacts-first** design where charts, tables,
and stats are the primary content. The conversation is the steering wheel, not
the display case.

## The Core Insight

Every AI chat UI is a chat app that happens to show results. For an analytics
agent, that's backwards. It should be an **analytics tool that happens to be
conversational**. The artifacts are the content. The conversation is the
steering wheel.

## Design Decisions (settled)

1. **No sidebar.** A compact data bar (one line) replaces the sidebar. Full
   width for analysis. No wasted horizontal space on table lists or session
   history.

2. **No chat bubbles.** User queries become section headers. Each analysis
   is a self-contained block, not a message exchange. The UI is a notebook,
   not a chatbot.

3. **Artifacts first.** Charts and tables are the largest elements —
   full-width, prominent. The answer text references the artifacts you've
   already seen, not the other way around.

4. **Progressive disclosure.** The agent's process (thinking, code, tool
   results) is expanded during streaming, then contracts to a one-line
   summary after completion. Re-expandable for inspection.

5. **Focus hierarchy.** The current analysis is fully expanded. Previous
   analyses compress to title + artifact thumbnails + first line of answer.
   Click to re-expand.

6. **Inspect anything.** Expand artifacts to full-screen. Re-expand process
   steps. View the data table behind any chart. Nothing is hidden.

The UI should feel like Notion for data analysis — clean, spacious,
artifact-forward — not like ChatGPT with charts bolted on.

## States & Layouts

### 1. Onboarding (no data loaded)

Full-screen, centered, dramatic. Nothing else visible — no empty sidebar,
no disabled input bar.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                                                             │
│                                                             │
│                     ◈  DataAgent                            │
│                                                             │
│               Explore your data with AI                     │
│                                                             │
│                                                             │
│     ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │
│     │               │ │               │ │               │  │
│     │  🛍           │ │  🏪           │ │  🌍           │  │
│     │  E-commerce   │ │  Superstore   │ │  World        │  │
│     │               │ │               │ │  Indicators   │  │
│     │  5 tables     │ │  2 tables     │ │  1 table      │  │
│     │  12K orders   │ │  10K orders   │ │  gapminder    │  │
│     │               │ │               │ │               │  │
│     └───────────────┘ └───────────────┘ └───────────────┘  │
│                                                             │
│                          — or —                              │
│                                                             │
│     ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│     │                                                   │  │
│     │     Drop CSV, XLSX, or Parquet files here          │  │
│     │                or click to browse                   │  │
│     │                                                   │  │
│     └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- Sample dataset cards have subtle hover animations (lift + shadow)
- Drop zone has a dashed border that pulses on drag-over
- Everything animates in with staggered spring animations on page load

### 2. Data Loaded (dataset overview + ready state)

The onboarding transitions smoothly. A data bar appears below the header —
compact, always visible, expandable.

```
┌─────────────────────────────────────────────────────────────┐
│  ◈ DataAgent                                [+ Upload] [⚙] │
├─────────────────────────────────────────────────────────────┤
│  sales 12,847 rows · customers 200 rows · products 50   [▾]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                                                             │
│                                                             │
│                 What would you like to explore?              │
│                                                             │
│     ✨ Revenue trends by quarter                            │
│     ✨ Top customers by lifetime value                      │
│     ✨ Product category performance comparison              │
│     ✨ Return rate analysis                                 │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Ask about your data...                              [Send] │
└─────────────────────────────────────────────────────────────┘
```

- **Data bar** replaces the sidebar. One line: table names + row counts.
  Click [▾] to expand into a full dataset panel (see state 7). Click again
  to collapse. Always accessible, never wastes space.
- **Suggestions** are centered, each on its own line. LLM-generated based
  on the loaded tables. Click one to start. They feel like starting points,
  not chat prompts.
- **[+ Upload]** in the header lets you add more files at any time.

### 3. Analysis in Progress (streaming)

The empty state transitions out. The analysis streams in as a single block:

```
┌─────────────────────────────────────────────────────────────┐
│  ◈ DataAgent                                [+ Upload] [⚙] │
├─────────────────────────────────────────────────────────────┤
│  sales 12,847 rows · customers 200 rows · products 50   [▾]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Revenue trends by quarter                           │   │
│  │                                                      │   │
│  │  ┌ Process ──────────────────────────────────────┐   │   │
│  │  │                                                │   │   │
│  │  │  ● Thinking                                    │   │   │
│  │  │  │ I'll group revenue by quarter and           │   │   │
│  │  │  │ category, then visualize the trend...       │   │   │
│  │  │  │                                             │   │   │
│  │  │  ● Code                                        │   │   │
│  │  │  │ quarterly = group_by(sales, "quarter",      │   │   │
│  │  │  │     "revenue", "sum")                       │   │   │
│  │  │  │ show_chart(quarterly, kind="line",          │   │   │
│  │  │  │     title="Revenue by Quarter")             │   │   │
│  │  │  │                                             │   │   │
│  │  │  ◉ Running...                              ◌◌◌ │   │   │
│  │  │                                                │   │   │
│  │  └────────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Ask about your data...                             [Stop]  │
└─────────────────────────────────────────────────────────────┘
```

Streaming behavior:
- Thinking text appears with a typewriter effect
- Code block slides in after thinking
- Each tool result ticks in with a checkmark animation
  (`✓ Filtered: 1,234 rows`)
- The current step pulses (◉) while running
- Multi-step loops show multiple thinking → code → result cycles
- The Send button becomes Stop during streaming

### 4. Analysis Complete

Artifacts materialize. The process contracts. The answer appears.

```
┌─────────────────────────────────────────────────────────────┐
│  ◈ DataAgent                                [+ Upload] [⚙] │
├─────────────────────────────────────────────────────────────┤
│  sales 12,847 rows · customers 200 rows · products 50   [▾]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Revenue trends by quarter                           │   │
│  │                                                      │   │
│  │  ▸ 2 steps · 3 tool calls · 2 artifacts              │   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │                                                │  │   │
│  │  │          📈 Revenue by Quarter                 │  │   │
│  │  │                                                │  │   │
│  │  │    $2.5M ─                            ╱──●     │  │   │
│  │  │    $2.0M ─                     ●───╱           │  │   │
│  │  │    $1.5M ─              ●───╱                   │  │   │
│  │  │    $1.0M ─   ●───●───╱                         │  │   │
│  │  │              Q1  Q2  Q3  Q4                     │  │   │
│  │  │                                                │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌───────────────────────────────┐  │   │
│  │  │            │  │ Quarter │ Revenue │  Change   │  │   │
│  │  │   $8.2M    │  │ Q1      │ $1.0M   │    —      │  │   │
│  │  │            │  │ Q2      │ $1.2M   │  +20%     │  │   │
│  │  │   total    │  │ Q3      │ $2.1M   │  +75%     │  │   │
│  │  │  revenue   │  │ Q4      │ $2.3M   │  +10%     │  │   │
│  │  └────────────┘  └───────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Revenue grew steadily across 2024, with a major     │   │
│  │  acceleration in Q3 (+75%). Q4 continued growth at   │   │
│  │  a more modest +10%, reaching $2.3M. Total annual    │   │
│  │  revenue was $8.2M.                                  │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ✨ Break down by category · Compare year-over-year · ...   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Ask about your data...                              [Send] │
└─────────────────────────────────────────────────────────────┘
```

- **Process contracts** to a single summary line: "2 steps · 3 tool calls ·
  2 artifacts". Click ▸ to re-expand and inspect thinking/code/results.
- **Artifacts are LARGE.** Full-width chart. Stat card + table side by side
  below. They dominate the block.
- **Answer text** is below the artifacts — it references what you've already
  seen.
- **Follow-up suggestions** appear between the block and the input bar.

### 5. Multi-turn (previous analyses compress)

As you ask more questions, older blocks compress to keep focus on the latest:

```
│                                                             │
│  ┌─ Revenue trends by quarter ──────────────────────────┐   │
│  │  ▸ 2 steps · 2 artifacts                             │   │
│  │  [📈 chart thumbnail] [📋 table thumbnail] [$8.2M]   │   │
│  │  Revenue grew steadily across 2024, with major...     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Break down by category (current, expanded) ─────────┐   │
│  │                                                      │   │
│  │  ▸ 3 steps · 4 tool calls · 3 artifacts              │   │
│  │                                                      │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │        Revenue by Category & Quarter           │  │   │
│  │  │   [stacked bar chart]                          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ...                                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
```

Compressed blocks show: title, process summary, artifact thumbnails, and
the first line of the answer. Click anywhere to re-expand. The latest block
is always fully expanded.

This creates a natural focus hierarchy: current analysis is prominent, past
analyses are scannable but not overwhelming.

### 6. Artifact Interactions

Each artifact has hover actions that appear smoothly:

```
┌────────────────────────────────────────────────────┐
│          📈 Revenue by Quarter              ⤢ ⬇ 📋 │
│                                                    │
│   (chart)                                          │
│                                                    │
└────────────────────────────────────────────────────┘
```

- **⤢** = Expand to full-screen overlay (detailed inspection)
- **⬇** = Download (PNG for charts, CSV for tables)
- **📋** = View underlying data (for charts: show the table behind it)

Actions appear on hover in the top-right corner. Subtle, not cluttering.

**Full-screen overlay:** Click ⤢ and the artifact smoothly scales to fill
the screen with a backdrop blur. Shows the artifact at full resolution with
its underlying data table below. Dismiss with Escape or clicking outside.

### 7. Data Panel (expandable data bar)

Click [▾] on the data bar to expand:

```
├─────────────────────────────────────────────────────────────┤
│  sales 12,847 rows · customers 200 rows · products 50   [▴]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ sales ─────────────────────────────────────────────┐   │
│  │  12,847 rows · 14 columns                           │   │
│  │                                                      │   │
│  │  date (datetime) · customer_id (int) · product_id   │   │
│  │  (int) · category (str) · revenue (float) ·         │   │
│  │  quantity (int) · quarter (str) · region (str) · ... │   │
│  │                                                      │   │
│  │  Joins: customer_id → customers.id                   │   │
│  │         product_id → products.id                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ customers ──────────┐  ┌─ products ─────────────────┐  │
│  │  200 rows · 6 cols   │  │  50 rows · 8 cols          │  │
│  │  id · name · email   │  │  id · name · category ·    │  │
│  │  region · segment ·  │  │  price · cost · ...        │  │
│  │  signup_date          │  │                            │  │
│  └──────────────────────┘  └────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
```

Slides down with a spring animation. Shows all tables with schemas, column
types, and detected relationships. Collapses back to the one-line summary.
The data is always one click away but never in the way.

## Design Principles Summary

| Principle | Implementation |
|---|---|
| Artifacts first | Charts and tables are the largest elements, full-width, prominent |
| No sidebar | Data bar (1 line) replaces sidebar. Full width for analysis |
| Progressive disclosure | Process: expanded while streaming, contracts to summary after. Re-expandable |
| Not a chatbot | No chat bubbles. User query is a section header. Blocks, not messages |
| Focus hierarchy | Current analysis expanded, previous compressed to thumbnails |
| Inspect anything | Expand artifacts to full-screen. Re-expand process. View data behind charts |
| Smooth transitions | Spring animations. Streaming text. Artifact materialize effect |

## Event → UI Mapping

The agent emits events (see `docs/AGENT_REDESIGN.md`). The UI maps them:

```
Event("thinking", ...)  →  Process section: thinking step with typewriter text
Event("code", ...)      →  Process section: code block slides in
Event("artifact", ...)  →  If streaming: appears in process section as tool result
                           When complete: materializes as full-size artifact in block
Event("result", ...)    →  Process section: checkmark + summary line
Event("answer", ...)    →  Answer text below artifacts. Process contracts.
Event("error", ...)     →  Error message in process section (red, with context)
```

## Component Breakdown

```
App
├── Onboarding
│   ├── DatasetCards (sample datasets)
│   └── DropZone (file upload)
│
├── Header
│   ├── Logo
│   ├── UploadButton
│   └── SettingsButton
│
├── DataBar (compact, expandable)
│   ├── TableSummaries (name + row count, inline)
│   └── DataPanel (expanded: schemas, types, relationships)
│
├── AnalysisStream (main content area, scrollable)
│   ├── AnalysisBlock (one per user query)
│   │   ├── QueryHeader (user's question as section title)
│   │   ├── ProcessSection (expandable/collapsible)
│   │   │   ├── ThinkingStep
│   │   │   ├── CodeStep
│   │   │   └── ResultStep (per tool call)
│   │   ├── ArtifactGrid
│   │   │   ├── ChartArtifact (full-width)
│   │   │   ├── TableArtifact
│   │   │   └── StatArtifact
│   │   └── AnswerText (markdown rendered)
│   └── Suggestions (follow-up prompts)
│
├── InputBar (fixed bottom)
│   ├── TextInput
│   └── SendButton / StopButton
│
└── ArtifactOverlay (full-screen, on demand)
    ├── ArtifactFull (chart/table at full resolution)
    └── UnderlyingData (table behind chart)
```

## Animation Specs

**Page load (onboarding):** Staggered spring animations. Logo → tagline →
dataset cards (left to right) → drop zone. Each element fades in + slides
up. ~50ms stagger between elements.

**Data loaded transition:** Onboarding elements scale down + fade. Header
slides in from top. Data bar slides in below header. Suggestions fade in
centered. Input bar slides up from bottom.

**Streaming:** Thinking text uses typewriter effect (character by character).
Code block slides in from left after thinking completes. Tool results tick
in with checkmark animation. Current step indicator pulses.

**Analysis complete:** Process section smoothly collapses to summary line.
Artifacts materialize (scale from 0.95 → 1.0, opacity 0 → 1). Answer text
fades in below artifacts. Suggestions appear below the block.

**Multi-turn compression:** Previous block smoothly shrinks — artifacts
become thumbnails, text truncates, padding reduces. Uses layout animation
(not abrupt reflow).

**Artifact overlay:** Artifact scales up from its position to fill screen.
Backdrop blur fades in. Dismiss reverses the animation back to origin.

**Data panel:** Slides down from data bar with spring easing. Content fades
in staggered. Collapse reverses.

## What This Plan Does NOT Cover

- **Specific CSS / design tokens** — colors, typography, spacing. Decide
  during implementation.
- **Mobile / responsive layout** — desktop-first, adapt later.
- **Session management UI** — single session for now. Multi-session is a
  production concern.
- **Settings panel** — model selection, temperature, etc. Build when needed.
- **Error states beyond agent errors** — network failures, upload failures.
  Handle during implementation.
