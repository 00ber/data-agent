from agent import (
    Agent,
    Environment,
    ExecutionSandbox,
    Memory,
    OpenAILLM,
    Tools,
    __all__,
    load_file,
    load_files,
    normalize_table_name,
)


class TestPackageExports:
    def test_exports_teaching_focused_public_api(self):
        assert Agent.__name__ == "Agent"
        assert Environment.__name__ == "Environment"
        assert ExecutionSandbox.__name__ == "ExecutionSandbox"
        assert Memory.__name__ == "Memory"
        assert OpenAILLM.__name__ == "OpenAILLM"
        assert Tools.__name__ == "Tools"
        assert callable(load_file)
        assert callable(load_files)
        assert callable(normalize_table_name)

    def test_all_exposes_only_teaching_focused_root_names(self):
        assert sorted(__all__) == sorted(
            [
                "Agent",
                "Environment",
                "ExecutionSandbox",
                "Memory",
                "OpenAILLM",
                "Tools",
                "load_file",
                "load_files",
                "normalize_table_name",
            ]
        )
