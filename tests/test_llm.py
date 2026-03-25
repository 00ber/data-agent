import pytest

from agent.llm import CodeStep, OpenAILLM


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
    async def test_generate_calls_openai_responses_parse_with_structured_output(self):
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

        result = await llm.generate(messages)

        assert result == parsed_step
        assert recorded_kwargs["model"] == "gpt-5.4"
        assert recorded_kwargs["input"] == messages
        assert recorded_kwargs["text_format"] is CodeStep
        assert recorded_kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_generate_rejects_missing_structured_code_step(self):
        class FakeResponses:
            async def parse(self, **kwargs):
                return type("FakeResponse", (), {"output_parsed": None})()

        fake_client = type("FakeClient", (), {"responses": FakeResponses()})()
        llm = OpenAILLM(model="gpt-5.4", client=fake_client)

        with pytest.raises(
            ValueError,
            match="LLM response did not contain a parsed code step.",
        ):
            await llm.generate([{"role": "system", "content": "You are helpful."}])
