from agent.agent import CodeStep
from agent.events import Event
from agent.environment import (
    AnalysisHandoff,
    Artifact,
    Environment,
    ExecutionResult,
)
from agent.memory import Memory
from agent.prompts import (
    build_conversation_messages,
    build_finalization_messages,
    build_step_messages,
    build_system_prompt,
    describe_tool,
    describe_tools,
)
from agent.response import FinalResponse, FinalResponseReview, ResponseSection
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
        assert "publish_chart(" in result

    def test_uses_registered_action_order(self):
        tools = Tools()

        result = describe_tools(tools)

        assert result.index("filter(") < result.index("group_by(")
        assert result.index("group_by(") < result.index("sort(")
        assert result.index("sort(") < result.index("join(")
        assert result.index("join(") < result.index("schema(")
        assert result.index("schema(") < result.index("head(")
        assert result.index("head(") < result.index("sample(")
        assert result.index("sample(") < result.index("publish_chart(")
        assert result.index("publish_chart(") < result.index("publish_table(")
        assert result.index("publish_table(") < result.index("publish_stat(")


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
        assert "schema(" in prompt
        assert "publish_table(" in prompt

    def test_includes_conclude_analysis_in_available_actions_section(self, orders_df):
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
        assert "conclude_analysis(" in prompt
        assert "must call conclude_analysis" in prompt.lower()
        assert "## Final Answer" not in prompt
        assert actions_section.index("publish_stat(") < actions_section.index(
            "conclude_analysis("
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
        assert "publish_chart(), publish_table(), and publish_stat()" in prompt
        assert "schema(), head(), and sample()" in prompt
        assert "one meaningful operation per step" in prompt.lower()

    def test_requires_downstream_handoff_notes(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )

        prompt = build_system_prompt(environment, Tools())

        assert "stand-alone downstream handoff" in prompt.lower()
        assert "not polished ui copy" in prompt.lower()
        assert "@artifact_" in prompt
        assert "relationship or likelihood" in prompt.lower()
        assert "normalized comparison" in prompt.lower()
        assert "artifact_ids" in prompt


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
        memory.record_assistant_response(
            FinalResponse(
                sections=[
                    ResponseSection(
                        kind="markdown",
                        markdown="Hi",
                        artifact_id=None,
                    )
                ]
            )
        )

        messages = build_conversation_messages("System prompt", memory)

        assert messages == [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]


class TestBuildStepMessages:
    def test_error_feedback_requests_fix(self):
        result = ExecutionResult(
            events=[],
            output="ZeroDivisionError: division by zero",
            is_error=True,
            analysis_handoff=None,
            step_summary=None,
        )
        code_step = CodeStep(plan="Try bad code", code="1 / 0")

        messages = build_step_messages(code_step, result)
        feedback = messages[1]["content"]

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
            analysis_handoff=None,
            step_summary="Step summary:\n- published artifact artifact_1: table 'Preview'",
        )
        code_step = CodeStep(plan="Publish preview", code="publish_table(...)")

        messages = build_step_messages(code_step, result)
        feedback = messages[1]["content"]

        assert "artifact(s) visible to the user" in feedback
        assert "call conclude_analysis()" in feedback
        assert "stand-alone handoff" in feedback.lower()

    def test_success_feedback_without_artifacts(self):
        result = ExecutionResult(
            events=[],
            output="OK",
            is_error=False,
            analysis_handoff=None,
            step_summary=(
                "Step summary:\n"
                "- dataframe joined: 10 rows; "
                "columns=['region_x', 'region_y', 'total']; "
                "dtypes={'region_x': 'object', 'region_y': 'object', 'total': 'float64'}"
            ),
        )
        code_step = CodeStep(plan="Inspect join", code="joined = join(...)")

        messages = build_step_messages(code_step, result)
        feedback = messages[1]["content"]

        assert "Step succeeded." in feedback
        assert "call conclude_analysis()" in feedback
        assert "joined" in feedback
        assert "region_y" in feedback

    def test_includes_step_summary_in_assistant_message(self):
        result = ExecutionResult(
            events=[],
            output="5",
            is_error=False,
            analysis_handoff=None,
            step_summary=(
                "Step summary:\n"
                "- dataframe joined: 12 rows; "
                "columns=['segment', 'region_y', 'total']; "
                "dtypes={'segment': 'object', 'region_y': 'object', 'total': 'float64'}\n"
                "- text output: 5"
            ),
        )
        code_step = CodeStep(plan="Inspect the join", code="print(5)")

        messages = build_step_messages(code_step, result)

        assert "Step summary:" in messages[0]["content"]
        assert "joined" in messages[0]["content"]
        assert "region_y" in messages[0]["content"]
        assert "5" in messages[0]["content"]


class TestBuildFinalizationMessages:
    def test_includes_question_handoff_and_artifact_preview(self, orders_df):
        environment = Environment(
            inputs={"orders": orders_df},
            sandbox=ExecutionSandbox(),
        )
        environment.artifacts.append(
            Artifact(
                id="artifact_1",
                kind="table",
                title="Revenue by region",
                data={
                    "columns": ["region", "revenue"],
                    "rows": [["West", 100], ["East", 90]],
                    "shape": [2, 2],
                },
            )
        )
        handoff = AnalysisHandoff(
            notes="The table @artifact_1 shows West ahead of East.",
            artifact_ids=["artifact_1"],
        )

        messages = build_finalization_messages(
            "Which region leads revenue?",
            handoff,
            environment,
        )

        assert messages[0]["role"] == "system"
        assert "final response review" in messages[0]["content"].lower()
        assert "Which region leads revenue?" in messages[1]["content"]
        assert "The table @artifact_1 shows West ahead of East." in messages[1]["content"]
        assert "Revenue by region" in messages[1]["content"]
        assert "West" in messages[1]["content"]
        assert "East" in messages[1]["content"]

    def test_final_response_review_model_stores_review_fields(self):
        review = FinalResponseReview(
            status="approved",
            critique=None,
            response=FinalResponse(
                sections=[
                    ResponseSection(
                        kind="markdown",
                        markdown="done",
                        artifact_id=None,
                    )
                ]
            ),
        )

        assert review.status == "approved"
        assert review.critique is None
        assert review.response == FinalResponse(
            sections=[
                ResponseSection(
                    kind="markdown",
                    markdown="done",
                    artifact_id=None,
                )
            ]
        )
