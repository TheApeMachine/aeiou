from __future__ import annotations

from typing import Any, Optional

from .models import TranscodeRequest


def _infer_defaults(style_profile: Optional[dict]) -> dict[str, Any]:
    naming = ["functions: snake_case", "classes: PascalCase"]
    testing = "pytest; arrange-act-assert"
    style_guides = ["google docstrings"]
    design_patterns = ["dependency_injection", "pure_functions_first"]

    if isinstance(style_profile, dict):
        naming = style_profile.get("naming_conventions", naming)
        testing = style_profile.get("testing_strategy", testing)
        style_guides = style_profile.get("style_guides", style_guides)
        design_patterns = style_profile.get("design_patterns", design_patterns)

    return {
        "naming_conventions": naming,
        "testing_strategy": testing,
        "style_guides": style_guides,
        "design_patterns": design_patterns,
    }


def generate_spec(req: TranscodeRequest) -> dict:
    goal = req.prompt.strip()

    inferred = [
        "follow personal style profile",
        "enforce explicit error handling policy",
        "prefer small, pure functions where possible",
    ]

    defaults = _infer_defaults(req.style_profile)

    spec: dict[str, Any] = {
        "goal": goal,
        "inputs": [],
        "outputs": [],
        "constraints_explicit": [],
        "constraints_inferred": inferred,
        "libraries_preferred": [],
        "libraries_forbidden": [],
        "style_guides": defaults["style_guides"],
        "naming_conventions": defaults["naming_conventions"],
        "design_patterns": defaults["design_patterns"],
        "testing_strategy": defaults["testing_strategy"],
        "edge_cases": [],
        "verbosity": req.verbosity,
        "open_questions": [],
    }

    return spec



