# Engineering Ethos

These are rules, not suggestions. Follow them by default in every file you
write, edit, or refactor.

## Scope Discipline

- Follow the active task. Do not redesign architecture, add scope, or
  "improve" the system beyond what was asked.
- When implementation choices are unclear, ask — do not guess and gold-plate.

## Code Design

Write code that is easy to skim and hard to misunderstand.

### Screaming Architecture

- Module and file names must make domain intent obvious.
- A reader should know *why* a file exists before reading its implementation.
- Avoid vague names like `helpers.py`, `utils.py`, `common.py`.

### Boring Code

- Choose the most obvious implementation that works.
- Prefer explicit control flow over dense or clever expressions.
- Use named intermediate variables when they make intent clearer.
- Avoid abstractions that exist only to save a few repeated lines.

### One Level of Abstraction

- A function should do one job at one level.
- High-level functions should read like short paragraphs.
- Low-level details belong in helpers whose names explain the step.

### Small, Focused Units

- Functions should fit on one screen.
- If a function or class has more than one reason to change, split it.
- Avoid flag arguments that switch behavior.

## Naming

- Use names that reveal intent.
- Never use vague names: `data`, `info`, `handler`, `processor`, `utils`,
  `helpers`, `manager`, `stuff`, `item`.
- Booleans should read as questions: `is_valid`, `has_children`, `can_retry`.
- Functions should read as actions: `parse_header`, `send_notification`.

## Error Handling

- Fail early and loudly.
- Prefer specific exceptions over broad catches.
- Error messages must say what went wrong *and* what was expected.
- Do not use `None` or silent fallbacks to hide failures.
- Do not invent fallback behavior to smooth over an issue.
- If a fallback seems necessary, stop and ask before adding it.
- If the design explicitly requires a fallback, implement only that exact
  fallback and keep it visible in code and tests.

## Testing (TDD by Default)

Use Red → Green → Refactor.

1. **Red** — Write the next failing test for the behavior you want.
2. **Green** — Make the smallest change that passes.
3. **Refactor** — Improve the code while tests stay green.

Rules:

- Do not add production behavior without a failing test first.
- Tests are behavior-focused, not implementation-focused.
- One reason to fail per test.
- Use Arrange → Act → Assert with blank lines between phases.
- Prefer direct setup and simple fakes over heavy mocking.

## Refactoring

- Refactor only while green.
- Remove ceremony that does not buy clarity.
- Extract shared code only after duplication is real (rule of three).
- If an abstraction makes code harder to skim, delete it.
