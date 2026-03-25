from agent.events import Event
from agent.environment import Environment, ExecutionResult
from agent.memory import Memory
from agent.prompts import (
    build_conversation_messages,
    build_step_feedback,
    build_system_prompt,
    describe_tool,
    describe_tools,
)
from agent.sandbox import ExecutionSandbox
from agent.tools import Tools


class TestDescribeTool:
    def test_includes_function_name(self):
        tools = Tools()

        result = describe_tool(tools.filter)

        assert "filter(" in result

    def test_includes_user_parameters_only(self):
        tools = Tools()

        result = describe_tool(tools.filter)

        assert "table" in result
        assert "column" in result
        assert "op" in result
        assert "value" in result
        assert "self" not in result
        assert "execution_context" not in result

    def test_includes_structured_docstring(self):
        tools = Tools()

        result = describe_tool(tools.group_by)

        assert "Purpose:" in result
        assert "Parameters:" in result
        assert "Returns:" in result
        assert "Emits:" in result
        assert "Example:" in result


class TestDescribeTools:
    def test_includes_public_tool_methods(self):
        tools = Tools()

        result = describe_tools(tools)

        assert "filter(" in result
        assert "group_by(" in result
        assert "show_chart(" in result

    def test_uses_registered_action_order(self):
        tools = Tools()

        result = describe_tools(tools)

        assert result.index("filter(") < result.index("group_by(")
        assert result.index("group_by(") < result.index("sort(")
        assert result.index("sort(") < result.index("join(")
        assert result.index("join(") < result.index("show_chart(")
        assert result.index("show_chart(") < result.index("show_table(")
        assert result.index("show_table(") < result.index("show_stat(")


class TestBuildSystemPrompt:
    def test_includes_environment_description(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())

        assert "orders" in prompt
        assert "revenue" in prompt
        assert "## Input Tables" in prompt
        assert "unique names exactly as listed below" in prompt

    def test_includes_tool_descriptions(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())

        assert "filter(" in prompt
        assert "group_by(" in prompt
        assert "show_table(" in prompt

    def test_includes_final_answer_in_available_actions_section(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())
        actions_section = prompt.split("## Available Actions", maxsplit=1)[1].split(
            "## Runtime",
            maxsplit=1,
        )[0]

        assert "## Available Actions" in prompt
        assert "final_answer(" in prompt
        assert "must call final_answer" in prompt.lower()
        assert "## Final Answer" not in prompt
        assert actions_section.index("show_stat(") < actions_section.index(
            "final_answer("
        )

    def test_includes_workspace_guidance(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())

        assert "workspace" in prompt.lower()
        assert "persist across steps" in prompt.lower()
        assert "input tables are immutable" in prompt.lower()
        assert "_x and _y" in prompt
        assert "libraries in scope" in prompt.lower()

    def test_requires_concrete_final_answers(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())

        assert "states the findings directly" in prompt.lower()
        assert "do not just say" in prompt.lower()


class TestBuildConversationMessages:
    def test_prepends_system_prompt(self):
        memory = Memory()
        memory.record_user_turn("What drives revenue?")

        messages = build_conversation_messages("System prompt", memory)

        assert messages[0] == {"role": "system", "content": "System prompt"}
        assert messages[1] == {"role": "user", "content": "What drives revenue?"}

    def test_uses_memory_conversation_messages(self):
        memory = Memory()
        memory.record_user_turn("Hello")
        memory.record_final_answer("Hi")

        messages = build_conversation_messages("System prompt", memory)

        assert messages == [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]


class TestBuildStepFeedback:
    def test_error_feedback_requests_fix(self):
        result = ExecutionResult(
            events=[],
            output="ZeroDivisionError: division by zero",
            is_error=True,
            final_answer=None,
        )

        feedback = build_step_feedback(result)

        assert "Error:" in feedback
        assert "Fix the issue and try again." in feedback
        assert "change the code or approach" in feedback.lower()

    def test_artifact_feedback_mentions_visible_artifacts(self):
        result = ExecutionResult(
            events=[
                Event("artifact", {"id": "artifact_1"}),
                Event("result", {"text": "OK"}),
            ],
            output="OK",
            is_error=False,
            final_answer=None,
        )

        feedback = build_step_feedback(result)

        assert "artifact(s) visible to the user" in feedback
        assert "call final_answer()" in feedback
        assert "summarize the actual findings" in feedback.lower()

    def test_success_feedback_without_artifacts(self):
        result = ExecutionResult(
            events=[],
            output="OK",
            is_error=False,
            final_answer=None,
        )

        feedback = build_step_feedback(result)

        assert "Step succeeded." in feedback
        assert "call final_answer()" in feedback
