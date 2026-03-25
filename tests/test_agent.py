import pandas as pd
import pytest

from agent.agent import run, CodeStep
from agent.events import Event, FinalAnswer
from agent.session import Session


def make_fake_llm(responses: list[CodeStep]):
    """Create a fake LLM callable that returns predetermined responses."""
    iterator = iter(responses)

    async def fake_llm(messages, **kwargs):
        return next(iterator)

    return fake_llm


class TestCodeStep:
    def test_has_plan_and_code(self):
        step = CodeStep(plan="Analyze revenue", code="print(1)")

        assert step.plan == "Analyze revenue"
        assert step.code == "print(1)"


class TestRunSingleStep:
    @pytest.mark.asyncio
    async def test_yields_thinking_event(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Thinking...", code="final_answer('done')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 1
        assert thinking_events[0].data["text"] == "Thinking..."

    @pytest.mark.asyncio
    async def test_yields_code_event(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        code_events = [e for e in events if e.kind == "code"]
        assert len(code_events) == 1
        assert "final_answer" in code_events[0].data["text"]

    @pytest.mark.asyncio
    async def test_yields_answer_event_on_final_answer(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('Revenue is $100')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        answer_events = [e for e in events if e.kind == "answer"]
        assert len(answer_events) == 1
        assert answer_events[0].data["text"] == "Revenue is $100"

    @pytest.mark.asyncio
    async def test_terminates_on_final_answer(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
            CodeStep(plan="Should not run", code="print('bad')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 1  # Only first step ran


class TestRunMultiStep:
    @pytest.mark.asyncio
    async def test_error_feeds_back_to_next_step(self):
        session = Session(tables={"sales": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Try bad code", code="1 / 0"),
            CodeStep(plan="Fix it", code="final_answer('fixed')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        error_events = [e for e in events if e.kind == "error"]
        assert len(error_events) == 1
        assert "ZeroDivisionError" in error_events[0].data["text"]

        answer_events = [e for e in events if e.kind == "answer"]
        assert len(answer_events) == 1

    @pytest.mark.asyncio
    async def test_max_steps_respected(self):
        session = Session()
        session.config.max_steps = 2
        session.tables["x"] = pd.DataFrame({"a": [1]})
        # LLM never calls final_answer
        fake_llm = make_fake_llm([
            CodeStep(plan="Step 1", code="print('one')"),
            CodeStep(plan="Step 2", code="print('two')"),
            CodeStep(plan="Step 3", code="print('three')"),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        thinking_events = [e for e in events if e.kind == "thinking"]
        assert len(thinking_events) == 2  # Stopped at max_steps


class TestRunArtifacts:
    @pytest.mark.asyncio
    async def test_tool_artifacts_emitted_as_events(self):
        session = Session(tables={"sales": pd.DataFrame({
            "category": ["A", "B", "A"],
            "revenue": [100, 200, 300],
        })})
        fake_llm = make_fake_llm([
            CodeStep(
                plan="Group and answer",
                code='grouped = group_by(sales, "category", "revenue", "sum")\nfinal_answer("done")',
            ),
        ])

        events = [e async for e in run(session, "test", llm=fake_llm)]

        artifact_events = [e for e in events if e.kind == "artifact"]
        assert len(artifact_events) >= 1
        assert artifact_events[0].data["kind"] == "table"


class TestRunHistory:
    @pytest.mark.asyncio
    async def test_history_accumulates(self):
        session = Session(tables={"x": pd.DataFrame({"a": [1]})})
        fake_llm = make_fake_llm([
            CodeStep(plan="Plan", code="final_answer('done')"),
        ])

        _ = [e async for e in run(session, "What is x?", llm=fake_llm)]

        assert len(session.history) >= 2  # At least user message + assistant
        assert session.history[0]["role"] == "user"
        assert "What is x?" in session.history[0]["content"]
