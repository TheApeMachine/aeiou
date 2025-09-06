import pytest
from pathlib import Path
import json
from jsonschema import validate as jsonschema_validate, ValidationError

from app.spec_generator import SpecGenerator
from app.models import TaskSpec


def test_style_profile_loading():
    """Test loading style profile from JSON"""
    generator = SpecGenerator()

    # Should load default profile if file doesn't exist
    profile = generator.style_profile
    assert isinstance(profile, dict)
    assert "naming_conventions" in profile
    assert "testing_strategy" in profile


def test_cluster_signals_to_taskspec():
    """Test converting analysis data to TaskSpec"""
    generator = SpecGenerator()

    analysis_data = {
        "filepath": "/path/to/file.py",
        "duplication": 2,
        "complexity": {"complexity_score": 30, "lines": 50},
        "test_gap": {"test_coverage_ratio": 0.8, "functions": 5, "test_functions": 4},
        "todos_dead_code": {"todos": 1, "dead_code_indicators": 2}
    }

    taskspec = generator.cluster_signals_to_taskspec(analysis_data)

    assert isinstance(taskspec, TaskSpec)
    assert taskspec.goal is not None
    assert len(taskspec.inputs) > 0
    assert taskspec.risk in ["low", "medium", "high"]
    assert taskspec.priority in ["low", "medium", "high"]
    assert taskspec.estimated_cost in ["low", "medium", "high"]


def test_parse_explicit_constraints():
    """Test parsing constraints from natural language"""
    generator = SpecGenerator()

    # Test avoiding libraries
    prompt = "Create a function that avoids using numpy and prefers pandas"
    parsed = generator.parse_explicit_constraints(prompt)

    assert "numpy" in parsed["libraries_forbidden"]
    assert "pandas" in parsed["libraries_preferred"]

    # Test other constraints
    prompt = "Write secure async code with type hints and no external dependencies"
    parsed = generator.parse_explicit_constraints(prompt)

    assert any("security" in c.lower() for c in parsed["constraints_explicit"])
    assert any("async" in c.lower() for c in parsed["constraints_explicit"])
    assert any("type hint" in c.lower() for c in parsed["constraints_explicit"])
    assert any("dependencies" in c.lower() for c in parsed["constraints_explicit"])


def test_generate_clarifying_questions():
    """Test generating clarifying questions for incomplete TaskSpecs"""
    generator = SpecGenerator()

    # TaskSpec with missing information
    taskspec = TaskSpec(
        goal="Create a function",
        constraints_explicit=[],
        constraints_inferred=[],
        verbosity="normal"
    )

    questions = generator.generate_clarifying_questions(taskspec)

    assert len(questions) > 0
    assert any("inputs" in q.lower() for q in questions)
    assert any("outputs" in q.lower() for q in questions)
    assert any("testing" in q.lower() for q in questions)


def test_enhance_taskspec_with_answers():
    """Test enhancing TaskSpec with user answers"""
    generator = SpecGenerator()

    taskspec = TaskSpec(
        goal="Create a function",
        inputs=[],
        outputs=[],
        constraints_explicit=[],
        constraints_inferred=[],
        verbosity="normal"
    )

    answers = {
        "What are the main inputs this code should handle?": "user data, configuration",
        "What outputs should this code produce?": "result object, error message",
        "What testing approach should be used?": "unit tests with pytest"
    }

    enhanced = generator.enhance_taskspec_with_answers(taskspec, answers)

    assert len(enhanced.inputs) == 2
    assert len(enhanced.outputs) == 2
    assert enhanced.testing_strategy == "unit tests with pytest"


def test_json_schema_validation():
    """Test that generated TaskSpecs validate against JSON schema"""
    generator = SpecGenerator()

    analysis_data = {
        "filepath": "/test/file.py",
        "duplication": 0,
        "complexity": {"complexity_score": 10, "lines": 20},
        "test_gap": {"test_coverage_ratio": 1.0, "functions": 2, "test_functions": 2},
        "todos_dead_code": {"todos": 0, "dead_code_indicators": 0}
    }

    taskspec = generator.cluster_signals_to_taskspec(analysis_data)

    # Load schema
    schema_path = Path(__file__).parent.parent / "schemas" / "canonical_spec.schema.json"
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    # Should not raise ValidationError
    jsonschema_validate(instance=taskspec.dict(), schema=schema)


def test_risk_priority_calculation():
    """Test risk and priority calculation"""
    generator = SpecGenerator()

    # High risk scenario
    analysis_data = {
        "filepath": "/test/file.py",
        "duplication": 10,
        "complexity": {"complexity_score": 150, "lines": 200},
        "test_gap": {"test_coverage_ratio": 0.1, "functions": 10, "test_functions": 1},
        "todos_dead_code": {"todos": 10, "dead_code_indicators": 5}
    }

    taskspec = generator.cluster_signals_to_taskspec(analysis_data)

    assert taskspec.risk == "high"
    assert taskspec.priority in ["high", "medium"]  # Could be either based on exact calculation