from agent import (
    Agent,
    Artifact,
    CodeStep,
    Environment,
    Event,
    EventKind,
    ExecutionContext,
    ExecutionResult,
    ExecutionSandbox,
    LLM,
    Memory,
    OpenAILLM,
    SandboxResult,
    StepRecord,
    Tools,
    load_file,
    load_files,
    normalize_table_name,
)
from agent import __all__


class TestPackageExports:
    def test_exports_clean_public_api(self):
        assert Agent.__name__ == "Agent"
        assert Artifact.__name__ == "Artifact"
        assert CodeStep.__name__ == "CodeStep"
        assert Environment.__name__ == "Environment"
        assert Event.__name__ == "Event"
        assert EventKind.__args__
        assert ExecutionContext.__name__ == "ExecutionContext"
        assert ExecutionResult.__name__ == "ExecutionResult"
        assert ExecutionSandbox.__name__ == "ExecutionSandbox"
        assert LLM.__name__ == "LLM"
        assert Memory.__name__ == "Memory"
        assert OpenAILLM.__name__ == "OpenAILLM"
        assert SandboxResult.__name__ == "SandboxResult"
        assert StepRecord.__name__ == "StepRecord"
        assert Tools.__name__ == "Tools"
        assert callable(load_file)
        assert callable(load_files)
        assert callable(normalize_table_name)

    def test_all_exposes_only_supported_root_names(self):
        assert sorted(__all__) == sorted(
            [
                "Agent",
                "Artifact",
                "CodeStep",
                "Environment",
                "Event",
                "EventKind",
                "ExecutionContext",
                "ExecutionResult",
                "ExecutionSandbox",
                "LLM",
                "Memory",
                "OpenAILLM",
                "SandboxResult",
                "StepRecord",
                "Tools",
                "load_file",
                "load_files",
                "normalize_table_name",
            ]
        )
        assert "build_system_prompt" not in __all__
        assert "SandboxStop" not in __all__
