import pandas as pd
import pytest
from pydantic import BaseModel

from agent.agent import Agent, CodeStep
from agent.environment import Environment
from agent.memory import Memory
from agent.response import FinalResponse, FinalResponseReview, ResponseSection
from agent.sandbox import ExecutionSandbox
from agent.tools import Tools


class FakeLLM:
    def __init__(self, responses: list[tuple[type[BaseModel], BaseModel]]) -> None:
        self._responses = iter(responses)
        self.calls: list[tuple[type[BaseModel], list[dict[str, str]]]] = []

    async def parse(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        self.calls.append((response_model, [message.copy() for message in messages]))
        expected_model, response = next(self._responses)
        assert response_model is expected_model
        return response


def markdown_response(text: str) -> FinalResponse:
    return FinalResponse(
        sections=[
            ResponseSection(
                kind="markdown",
                markdown=text,
                artifact_id=None,
            )
        ]
    )


def make_agent(
    llm: FakeLLM,
    *,
    inputs: dict[str, pd.DataFrame] | None = None,
    memory: Memory | None = None,
    environment: Environment | None = None,
    max_steps: int = 10,
) -> Agent:
    if environment is None:
        environment = Environment(
            inputs=inputs or {},
            sandbox=ExecutionSandbox(),
        )

    return Agent(
        llm=llm,
        memory=memory or Memory(),
        environment=environment,
        tools=Tools(),
        max_steps=max_steps,
    )


class TestAgent:
    def test_rejects_non_positive_max_steps(self):
        llm = FakeLLM([])

        with pytest.raises(ValueError, match="Max steps must be a positive integer."):
            make_agent(llm, max_steps=0)

    @pytest.mark.asyncio
    async def test_run_emits_thinking_code_and_answer_events(self):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Answer directly",
                        code='conclude_analysis("Done.")',
                    ),
                )
                ,
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("done"),
                    ),
                ),
            ]
        )
        agent = make_agent(llm)

        events = [event async for event in agent.run("What happened?")]

        assert [event.kind for event in events] == ["thinking", "code", "reviewing", "answer"]
        assert events[0].data == {"text": "Answer directly"}
        assert events[1].data == {
            "text": 'conclude_analysis("Done.")'
        }
        assert events[2].data == {"text": "Finalizing response from the analysis handoff."}
        assert events[3].data == {
            "blocks": [{"type": "markdown", "content": "done"}]
        }

    @pytest.mark.asyncio
    async def test_run_emits_artifacts_before_terminal_answer(self, orders_df):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Group by category and finish",
                        code=(
                            'grouped = group_by("orders", "category", "revenue", "sum")\n'
                            'summary_table = publish_table(grouped, title="Revenue by category")\n'
                            'conclude_analysis("The table @"+summary_table+" shows category revenue.", [summary_table])'
                        ),
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("done"),
                    ),
                ),
            ]
        )
        agent = make_agent(llm, inputs={"orders": orders_df})

        events = [event async for event in agent.run("Summarize revenue by category.")]

        assert [event.kind for event in events] == ["thinking", "code", "artifact", "reviewing", "answer"]
        assert events[2].data["kind"] == "table"
        assert events[3].data == {"text": "Finalizing response from the analysis handoff."}
        assert events[4].data == {
            "blocks": [{"type": "markdown", "content": "done"}]
        }

    @pytest.mark.asyncio
    async def test_run_includes_observations_in_the_next_llm_call(self, orders_df):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Join the data first",
                        code='joined = join("orders", "orders", on="order_id")',
                    ),
                ),
                (
                    CodeStep,
                    CodeStep(
                        plan="Finish with the observed schema",
                        code='conclude_analysis("Done.")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("done"),
                    ),
                ),
            ]
        )
        agent = make_agent(llm, inputs={"orders": orders_df})

        _ = [event async for event in agent.run("Inspect the joined schema.")]

        second_call = llm.calls[1][1]
        assert any(
            message["role"] == "assistant"
            and "Step summary:" in message["content"]
            and "joined" in message["content"]
            and "region_x" in message["content"]
            and "region_y" in message["content"]
            for message in second_call
        )

    @pytest.mark.asyncio
    async def test_run_retries_after_error_with_step_feedback(self):
        llm = FakeLLM(
            [
                (CodeStep, CodeStep(plan="Try bad code", code="1 / 0")),
                (
                    CodeStep,
                    CodeStep(
                        plan="Fix it",
                        code='conclude_analysis("Fixed.")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("fixed"),
                    ),
                ),
            ]
        )
        agent = make_agent(llm)

        events = [event async for event in agent.run("Fix the issue.")]

        assert [event.kind for event in events] == [
            "thinking",
            "code",
            "error",
            "thinking",
            "code",
            "reviewing",
            "answer",
        ]
        assert len(llm.calls) == 3

        second_call = llm.calls[1][1]
        assert any(
            message["role"] == "assistant"
            and "Plan: Try bad code" in message["content"]
            and "Code: 1 / 0" in message["content"]
            for message in second_call
        )
        assert any(
            message["role"] == "user"
            and "ZeroDivisionError" in message["content"]
            and "Fix the issue and try again." in message["content"]
            for message in second_call
        )

    @pytest.mark.asyncio
    async def test_run_stops_at_max_steps_and_emits_error(self):
        llm = FakeLLM(
            [
                (CodeStep, CodeStep(plan="Step 1", code="print('one')")),
                (CodeStep, CodeStep(plan="Step 2", code="print('two')")),
                (CodeStep, CodeStep(plan="Step 3", code="print('three')")),
            ]
        )
        agent = make_agent(llm, max_steps=2)

        events = [event async for event in agent.run("Keep going.")]

        assert [event.kind for event in events] == [
            "thinking",
            "code",
            "result",
            "thinking",
            "code",
            "result",
            "error",
        ]
        assert events[-1].data == {
            "text": "Reached maximum steps without a final answer."
        }
        assert len(llm.calls) == 2

    @pytest.mark.asyncio
    async def test_run_records_conversation_memory(self):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Inspect and answer",
                        code='conclude_analysis("West wins.")',
                    ),
                )
                ,
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("West wins"),
                    ),
                ),
            ]
        )
        memory = Memory()
        agent = make_agent(llm, memory=memory)

        _ = [event async for event in agent.run("Who wins?")]

        assert memory.conversation_messages() == [
            {"role": "user", "content": "Who wins?"},
            {"role": "assistant", "content": "West wins"},
        ]

    @pytest.mark.asyncio
    async def test_reuses_memory_and_environment_across_turns(self):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Store a value",
                        code='saved_total = 7\nconclude_analysis("Saved total.")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("Saved total."),
                    ),
                ),
                (
                    CodeStep,
                    CodeStep(
                        plan="Use prior workspace",
                        code='conclude_analysis("The saved total is " + str(saved_total) + ".")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("7"),
                    ),
                ),
            ]
        )
        memory = Memory()
        environment = Environment(inputs={}, sandbox=ExecutionSandbox())
        agent = make_agent(llm, memory=memory, environment=environment)

        first_events = [event async for event in agent.run("Store the total.")]
        second_events = [event async for event in agent.run("What total did you store?")]

        assert first_events[-1].data == {
            "blocks": [{"type": "markdown", "content": "Saved total."}]
        }
        assert second_events[-1].data == {
            "blocks": [{"type": "markdown", "content": "7"}]
        }
        assert environment.workspace["saved_total"] == 7

        second_call = llm.calls[2][1]
        assert {"role": "user", "content": "Store the total."} in second_call
        assert {"role": "assistant", "content": "Saved total."} in second_call
        assert {"role": "user", "content": "What total did you store?"} in second_call

    @pytest.mark.asyncio
    async def test_run_continues_same_loop_when_final_response_review_requests_more_analysis(
        self,
    ):
        llm = FakeLLM(
            [
                (
                    CodeStep,
                    CodeStep(
                        plan="Draft a weak handoff",
                        code='conclude_analysis("The table shows revenue.")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="needs_more_analysis",
                        critique="State which region leads revenue and by how much.",
                        response=None,
                    ),
                ),
                (
                    CodeStep,
                    CodeStep(
                        plan="Add the missing comparison",
                        code='conclude_analysis("West leads revenue by a meaningful margin.")',
                    ),
                ),
                (
                    FinalResponseReview,
                    FinalResponseReview(
                        status="approved",
                        critique=None,
                        response=markdown_response("West leads revenue."),
                    ),
                ),
            ]
        )
        agent = make_agent(llm)

        events = [event async for event in agent.run("Which region leads revenue?")]

        assert [event.kind for event in events] == [
            "thinking",
            "code",
            "reviewing",
            "thinking",
            "code",
            "reviewing",
            "answer",
        ]
        assert len(llm.calls) == 4

        third_call = llm.calls[2][1]
        assert any(
            message["role"] == "user"
            and "State which region leads revenue and by how much." in message["content"]
            for message in third_call
        )
