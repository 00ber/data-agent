import pandas as pd

from agent.tools import Tools
from agent.session import Session
from agent.prompts import describe_tool, describe_tables, build_prompt


class TestDescribeTool:
    def test_includes_function_name(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "filter" in result

    def test_includes_parameters(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "column" in result
        assert "op" in result

    def test_includes_docstring(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "Filter rows" in result

    def test_skips_self_parameter(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        result = describe_tool(tools.filter)

        assert "self" not in result


class TestDescribeTables:
    def test_includes_table_name(self):
        tables = {"sales": pd.DataFrame({"a": [1, 2, 3]})}

        result = describe_tables(tables)

        assert "sales" in result

    def test_includes_row_count(self):
        tables = {"sales": pd.DataFrame({"a": [1, 2, 3]})}

        result = describe_tables(tables)

        assert "3" in result

    def test_includes_column_info(self):
        tables = {"orders": pd.DataFrame({"revenue": [1.0], "category": ["A"]})}

        result = describe_tables(tables)

        assert "revenue" in result
        assert "category" in result

    def test_multiple_tables(self):
        tables = {
            "orders": pd.DataFrame({"a": [1]}),
            "customers": pd.DataFrame({"b": [2]}),
        }

        result = describe_tables(tables)

        assert "orders" in result
        assert "customers" in result


class TestBuildPrompt:
    def test_includes_table_descriptions(self):
        tables = {"sales": pd.DataFrame({"revenue": [1.0]})}
        session = Session(tables=tables)
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        assert "sales" in prompt
        assert "revenue" in prompt

    def test_includes_tool_signatures(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        assert "filter" in prompt
        assert "group_by" in prompt
        assert "show_chart" in prompt
        assert "final_answer" in prompt

    def test_includes_system_instructions(self):
        session = Session()
        tools = Tools(session, emit=lambda e: None)

        prompt = build_prompt(session.tables, tools)

        # Should instruct the LLM about its role and how to use tools
        assert "code" in prompt.lower() or "python" in prompt.lower()
