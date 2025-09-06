from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import os
from pathlib import Path

from .models import TaskSpec
from .rag_system import rag_enrichment


class SpecGenerator:
    """Generate TaskSpecs from clustered signals and analysis data"""

    def __init__(self):
        self.style_profile = self._load_style_profile()

    def _load_style_profile(self) -> Dict[str, Any]:
        """Load user style profile from local JSON file"""
        profile_path = Path.home() / ".aeiou" / "style_profile.json"
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._get_default_style_profile()

    def _get_default_style_profile(self) -> Dict[str, Any]:
        """Get default style profile"""
        return {
            "naming_conventions": ["functions: snake_case", "classes: PascalCase"],
            "testing_strategy": "pytest; arrange-act-assert",
            "style_guides": ["google docstrings"],
            "design_patterns": ["dependency_injection", "pure_functions_first"],
            "libraries_preferred": [],
            "libraries_forbidden": []
        }

    def cluster_signals_to_taskspec(self, analysis_data: Dict[str, Any]) -> TaskSpec:
        """Convert analysis data into a TaskSpec"""

        # Extract basic information
        filepath = analysis_data.get("filepath", "")
        filename = os.path.basename(filepath) if filepath else "unknown"

        # Determine goal based on analysis
        goal = self._infer_goal_from_analysis(analysis_data, filename)

        # Parse explicit constraints from any available prompt
        prompt = analysis_data.get("prompt", "")
        parsed_constraints = self.parse_explicit_constraints(prompt) if prompt else {
            'constraints_explicit': [],
            'libraries_forbidden': [],
            'libraries_preferred': []
        }

        # Build constraints from analysis
        constraints_explicit = parsed_constraints['constraints_explicit']
        constraints_inferred = []
        open_questions = []

        # Process duplication issues
        if analysis_data.get("duplication", 0) > 3:
            constraints_inferred.append("Address code duplication")
            open_questions.append("Which duplicated sections should be refactored into shared functions?")

        # Process complexity issues
        complexity = analysis_data.get("complexity", {})
        if complexity.get("complexity_score", 0) > 50:
            constraints_inferred.append("Reduce function complexity")
            open_questions.append("How can this complex function be broken down?")

        # Process test gaps
        test_gap = analysis_data.get("test_gap", {})
        if test_gap.get("test_coverage_ratio", 1.0) < 0.5:
            constraints_inferred.append("Improve test coverage")
            open_questions.append("Which functions need test cases?")

        # Process TODO items
        todos_dead_code = analysis_data.get("todos_dead_code", {})
        if todos_dead_code.get("todos", 0) > 2:
            constraints_inferred.append("Address outstanding TODO items")
            open_questions.append("Which TODO items should be prioritized?")

        # Merge style profile
        style_profile = self.style_profile
        constraints_inferred.extend([
            f"Follow {guide}" for guide in style_profile.get("style_guides", [])
        ])

        # Merge parsed libraries with style profile
        all_preferred = list(set(
            parsed_constraints['libraries_preferred'] +
            style_profile.get("libraries_preferred", [])
        ))
        all_forbidden = list(set(
            parsed_constraints['libraries_forbidden'] +
            style_profile.get("libraries_forbidden", [])
        ))

        # Calculate risk and priority
        risk_level = self._calculate_risk(analysis_data)
        priority = self._calculate_priority(analysis_data)

        # Create initial TaskSpec
        taskspec = TaskSpec(
            goal=goal,
            inputs=[filepath] if filepath else [],
            outputs=[],
            constraints_explicit=constraints_explicit,
            constraints_inferred=constraints_inferred,
            libraries_preferred=all_preferred,
            libraries_forbidden=all_forbidden,
            style_guides=style_profile.get("style_guides", []),
            naming_conventions=style_profile.get("naming_conventions", []),
            design_patterns=style_profile.get("design_patterns", []),
            testing_strategy=style_profile.get("testing_strategy", ""),
            edge_cases=[],
            verbosity="normal",
            open_questions=open_questions,
            risk=risk_level,
            priority=priority,
            estimated_cost=self._estimate_cost(analysis_data)
        )

        # Enrich with RAG-retrieved information
        enriched_taskspec = rag_enrichment.enrich_taskspec(taskspec.dict(), "current_project")

        return TaskSpec(**enriched_taskspec)

    def _infer_goal_from_analysis(self, analysis_data: Dict[str, Any], filename: str) -> str:
        """Infer the main goal from analysis data"""
        issues = []

        if analysis_data.get("duplication", 0) > 3:
            issues.append("refactor duplicated code")
        if analysis_data.get("complexity", {}).get("complexity_score", 0) > 50:
            issues.append("simplify complex functions")
        if analysis_data.get("test_gap", {}).get("test_coverage_ratio", 1.0) < 0.5:
            issues.append("add missing tests")
        if analysis_data.get("todos_dead_code", {}).get("todos", 0) > 2:
            issues.append("address TODO items")

        if issues:
            return f"Improve code quality in {filename}: {', '.join(issues)}"
        else:
            return f"Maintain code quality in {filename}"

    def _calculate_risk(self, analysis_data: Dict[str, Any]) -> str:
        """Calculate risk level based on analysis"""
        risk_score = 0

        # High complexity increases risk
        if analysis_data.get("complexity", {}).get("complexity_score", 0) > 100:
            risk_score += 3
        elif analysis_data.get("complexity", {}).get("complexity_score", 0) > 50:
            risk_score += 2

        # Low test coverage increases risk
        test_ratio = analysis_data.get("test_gap", {}).get("test_coverage_ratio", 1.0)
        if test_ratio < 0.3:
            risk_score += 3
        elif test_ratio < 0.5:
            risk_score += 2

        # Many TODOs indicate technical debt
        if analysis_data.get("todos_dead_code", {}).get("todos", 0) > 5:
            risk_score += 2

        if risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"

    def _calculate_priority(self, analysis_data: Dict[str, Any]) -> str:
        """Calculate priority based on analysis"""
        priority_score = 0

        # Critical issues get high priority
        if analysis_data.get("duplication", 0) > 10:
            priority_score += 3
        if analysis_data.get("complexity", {}).get("complexity_score", 0) > 100:
            priority_score += 3
        if analysis_data.get("test_gap", {}).get("test_coverage_ratio", 1.0) < 0.2:
            priority_score += 3

        # Medium priority issues
        if analysis_data.get("duplication", 0) > 5:
            priority_score += 2
        if analysis_data.get("complexity", {}).get("complexity_score", 0) > 50:
            priority_score += 2

        if priority_score >= 6:
            return "high"
        elif priority_score >= 3:
            return "medium"
        else:
            return "low"

    def _estimate_cost(self, analysis_data: Dict[str, Any]) -> str:
        """Estimate implementation cost"""
        cost_score = 0

        # Complexity affects cost
        complexity_score = analysis_data.get("complexity", {}).get("complexity_score", 0)
        cost_score += complexity_score // 10

        # Duplication affects cost
        cost_score += analysis_data.get("duplication", 0) // 2

        # Test gaps affect cost
        test_ratio = analysis_data.get("test_gap", {}).get("test_coverage_ratio", 1.0)
        if test_ratio < 0.5:
            cost_score += 2

        if cost_score > 10:
            return "high"
        elif cost_score > 5:
            return "medium"
        else:
            return "low"

    def generate_clarifying_questions(self, taskspec: TaskSpec) -> List[str]:
        """Generate clarifying questions for underspecified constraints"""
        questions = []

        # Check for missing inputs/outputs
        if not taskspec.inputs:
            questions.append("What are the main inputs this code should handle?")

        if not taskspec.outputs:
            questions.append("What outputs should this code produce?")

        # Check for vague goals
        if len(taskspec.goal.split()) < 5:
            questions.append("Can you provide more details about what this code should accomplish?")

        # Check for missing testing strategy
        if not taskspec.testing_strategy or taskspec.testing_strategy == "":
            questions.append("What testing approach should be used (unit tests, integration tests, etc.)?")

        # Check for empty constraints
        if not taskspec.constraints_explicit:
            questions.append("Are there any specific requirements or constraints I should follow?")

        # Check for missing edge cases
        if not taskspec.edge_cases:
            questions.append("What edge cases or error conditions should be considered?")

        # Check for library preferences
        if not taskspec.libraries_preferred and not taskspec.libraries_forbidden:
            questions.append("Are there any preferred or forbidden libraries/frameworks?")

        return questions

    def enhance_taskspec_with_answers(self, taskspec: TaskSpec, answers: Dict[str, str]) -> TaskSpec:
        """Enhance TaskSpec with answers to clarifying questions"""
        enhanced = taskspec.copy()

        # Process answers and update TaskSpec accordingly
        for question, answer in answers.items():
            if "inputs" in question.lower():
                enhanced.inputs = [item.strip() for item in answer.split(",")]
            elif "outputs" in question.lower():
                enhanced.outputs = [item.strip() for item in answer.split(",")]
            elif "testing" in question.lower():
                enhanced.testing_strategy = answer
            elif "requirements" in question.lower() or "constraints" in question.lower():
                enhanced.constraints_explicit.append(answer)
            elif "edge cases" in question.lower():
                enhanced.edge_cases = [item.strip() for item in answer.split(",")]
            elif "libraries" in question.lower():
                if "preferred" in question.lower():
                    enhanced.libraries_preferred = [item.strip() for item in answer.split(",")]
                elif "forbidden" in question.lower():
                    enhanced.libraries_forbidden = [item.strip() for item in answer.split(",")]

        return enhanced

    def parse_explicit_constraints(self, prompt: str) -> Dict[str, List[str]]:
        """Parse explicit constraints from natural language prompt"""
        constraints_explicit = []
        libraries_forbidden = []
        libraries_preferred = []

        # Convert to lowercase for easier matching
        lower_prompt = prompt.lower()

        # Parse "avoid/forbid" patterns
        import re
        avoid_patterns = [
            r'avoid\s+(?:using\s+)?([^\s,.]+)',
            r'don\'t\s+use\s+([^\s,.]+)',
            r'forbid\s+([^\s,.]+)',
            r'no\s+([^\s,.]+)',
            r'without\s+([^\s,.]+)'
        ]

        for pattern in avoid_patterns:
            matches = re.findall(pattern, lower_prompt)
            for match in matches:
                if match not in ['the', 'a', 'an', 'to', 'and', 'or']:
                    libraries_forbidden.append(match.strip())

        # Parse "prefer/use" patterns
        prefer_patterns = [
            r'(?:prefer|use)\s+(?:the\s+)?([^\s,.]+)',
            r'(?:must|should)\s+use\s+([^\s,.]+)',
            r'with\s+([^\s,.]+)',
            r'using\s+([^\s,.]+)'
        ]

        for pattern in prefer_patterns:
            matches = re.findall(pattern, lower_prompt)
            for match in matches:
                if match not in ['the', 'a', 'an', 'to', 'and', 'or']:
                    libraries_preferred.append(match.strip())

        # Parse other explicit constraints
        if 'no dependencies' in lower_prompt or 'no external deps' in lower_prompt:
            constraints_explicit.append('Minimize external dependencies')

        if 'performance' in lower_prompt:
            constraints_explicit.append('Optimize for performance')

        if 'security' in lower_prompt or 'secure' in lower_prompt:
            constraints_explicit.append('Follow security best practices')

        if 'async' in lower_prompt or 'asynchronous' in lower_prompt:
            constraints_explicit.append('Use asynchronous programming')

        if 'type' in lower_prompt and 'hint' in lower_prompt:
            constraints_explicit.append('Use type hints')

        if 'test' in lower_prompt:
            constraints_explicit.append('Include comprehensive tests')

        return {
            'constraints_explicit': constraints_explicit,
            'libraries_forbidden': libraries_forbidden,
            'libraries_preferred': libraries_preferred
        }