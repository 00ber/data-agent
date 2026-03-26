import pytest
from pydantic import BaseModel

from agent.agent import CodeStep, FinalResponseBlock, FinalResponseReview
from agent.llm import OpenAILLM


class TestCodeStep:
    def test_stores_plan_and_code(self):
        step = CodeStep(plan="Inspect revenue by region", code="print(orders.head())")

        assert step.plan == "Inspect revenue by region"
        assert step.code == "print(orders.head())"


class TestOpenAILLM:
    def test_rejects_blank_model_name(self):
        with pytest.raises(ValueError, match="Model name must be a non-empty string."):
            OpenAILLM(model="   ", client=object())

    @pytest.mark.asyncio
    async def test_parse_calls_openai_responses_parse_with_structured_output(self):
        recorded_kwargs = {}
        parsed_step = CodeStep(plan="Plan", code="print(1)")

        class FakeResponses:
            async def parse(self, **kwargs):
                recorded_kwargs.update(kwargs)
                return type("FakeResponse", (), {"output_parsed": parsed_step})()

        fake_client = type(
            "FakeClient",
            (),
            {"responses": FakeResponses()},
        )()

        llm = OpenAILLM(model="gpt-5.4", temperature=0.2, client=fake_client)
        messages = [{"role": "system", "content": "You are helpful."}]

        result = await llm.parse(messages, CodeStep)

        assert result == parsed_step
        assert recorded_kwargs["model"] == "gpt-5.4"
        assert recorded_kwargs["input"] == messages
        assert recorded_kwargs["text_format"] is CodeStep
        assert recorded_kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_parse_supports_other_response_models(self):
        recorded_kwargs = {}

        parsed_decision = FinalResponseReview(
            status="approved",
            critique=None,
            blocks=[
                FinalResponseBlock(
                    type="markdown",
                    content="done",
                    artifact_id=None,
                )
            ],
        )

        class FakeResponses:
            async def parse(self, **kwargs):
                recorded_kwargs.update(kwargs)
                return type("FakeResponse", (), {"output_parsed": parsed_decision})()

        fake_client = type("FakeClient", (), {"responses": FakeResponses()})()
        llm = OpenAILLM(model="gpt-5.4", client=fake_client)
        messages = [{"role": "system", "content": "You are helpful."}]

        result = await llm.parse(messages, FinalResponseReview)

        assert result == parsed_decision
        assert recorded_kwargs["text_format"] is FinalResponseReview

    async def test_parse_rejects_missing_structured_response(self):
        class FakeResponses:
            async def parse(self, **kwargs):
                return type("FakeResponse", (), {"output_parsed": None})()

        fake_client = type("FakeClient", (), {"responses": FakeResponses()})()
        llm = OpenAILLM(model="gpt-5.4", client=fake_client)

        with pytest.raises(
            ValueError,
            match="LLM response did not contain a parsed CodeStep.",
        ):
            await llm.parse(
                [{"role": "system", "content": "You are helpful."}],
                CodeStep,
            )
