from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PromptVersion:
    """Represents a version of a system prompt"""
    id: str
    name: str
    version: str
    content: str
    description: str
    created_at: str
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class ToolManifest:
    """Represents a tool manifest"""
    id: str
    name: str
    version: str
    tools: List[Dict[str, Any]]
    description: str
    created_at: str
    compatible_prompts: List[str]


class PromptRegistry:
    """Registry for managing system prompts and tool manifests"""

    def __init__(self):
        self.prompts: Dict[str, PromptVersion] = {}
        self.tool_manifests: Dict[str, ToolManifest] = {}
        self.project_profiles: Dict[str, Dict[str, str]] = {}
        self._load_builtin_prompts()

    def _load_builtin_prompts(self):
        """Load built-in system prompts"""
        builtin_prompts = [
            PromptVersion(
                id="code_assistant_v1",
                name="Code Assistant",
                version="1.0.0",
                content="""You are an expert software engineer helping with code improvements.
Focus on writing clean, maintainable, and efficient code.
Consider best practices, error handling, and documentation.""",
                description="General purpose code assistance",
                created_at="2024-01-01T00:00:00Z",
                tags=["general", "code"],
                metadata={"language": "universal"}
            ),
            PromptVersion(
                id="refactoring_expert_v1",
                name="Refactoring Expert",
                version="1.0.0",
                content="""You are a refactoring specialist focused on improving code structure.
Prioritize readability, maintainability, and performance.
Apply appropriate design patterns and clean code principles.""",
                description="Specialized in code refactoring",
                created_at="2024-01-01T00:00:00Z",
                tags=["refactoring", "structure"],
                metadata={"focus": "refactoring"}
            ),
            PromptVersion(
                id="testing_specialist_v1",
                name="Testing Specialist",
                version="1.0.0",
                content="""You are a testing expert focused on comprehensive test coverage.
Emphasize unit tests, integration tests, and edge cases.
Follow testing best practices and frameworks.""",
                description="Specialized in testing and test generation",
                created_at="2024-01-01T00:00:00Z",
                tags=["testing", "quality"],
                metadata={"focus": "testing"}
            )
        ]

        for prompt in builtin_prompts:
            self.prompts[prompt.id] = prompt

    def add_prompt(self, prompt: PromptVersion):
        """Add a new prompt version to the registry"""
        self.prompts[prompt.id] = prompt

    def get_prompt(self, prompt_id: str) -> Optional[PromptVersion]:
        """Get a prompt by ID"""
        return self.prompts.get(prompt_id)

    def list_prompts(self, tags: Optional[List[str]] = None) -> List[PromptVersion]:
        """List all prompts, optionally filtered by tags"""
        prompts = list(self.prompts.values())

        if tags:
            prompts = [p for p in prompts if any(tag in p.tags for tag in tags)]

        return sorted(prompts, key=lambda p: p.created_at, reverse=True)

    def add_tool_manifest(self, manifest: ToolManifest):
        """Add a tool manifest"""
        self.tool_manifests[manifest.id] = manifest

    def get_tool_manifest(self, manifest_id: str) -> Optional[ToolManifest]:
        """Get a tool manifest by ID"""
        return self.tool_manifests.get(manifest_id)

    def list_tool_manifests(self) -> List[ToolManifest]:
        """List all tool manifests"""
        return list(self.tool_manifests.values())

    def set_project_profile(self, project_path: str, profile: Dict[str, str]):
        """Set the active profile for a project"""
        self.project_profiles[project_path] = profile

    def get_project_profile(self, project_path: str) -> Dict[str, str]:
        """Get the active profile for a project"""
        return self.project_profiles.get(project_path, {
            "prompt_id": "code_assistant_v1",
            "tool_manifest_id": None
        })

    def get_active_prompt_for_project(self, project_path: str) -> Optional[PromptVersion]:
        """Get the active prompt for a project"""
        profile = self.get_project_profile(project_path)
        prompt_id = profile.get("prompt_id")
        return self.get_prompt(prompt_id) if prompt_id else None

    def get_active_tools_for_project(self, project_path: str) -> Optional[ToolManifest]:
        """Get the active tool manifest for a project"""
        profile = self.get_project_profile(project_path)
        manifest_id = profile.get("tool_manifest_id")
        return self.get_tool_manifest(manifest_id) if manifest_id else None

    def create_prompt_from_template(self, base_prompt_id: str, customizations: Dict[str, Any]) -> PromptVersion:
        """Create a new prompt version based on an existing one"""
        base_prompt = self.get_prompt(base_prompt_id)
        if not base_prompt:
            raise ValueError(f"Base prompt {base_prompt_id} not found")

        # Generate new ID
        new_id = f"{base_prompt_id}_custom_{int(datetime.now().timestamp())}"

        # Apply customizations
        new_content = base_prompt.content
        new_metadata = base_prompt.metadata.copy()
        new_tags = base_prompt.tags.copy()

        if "additional_instructions" in customizations:
            new_content += "\n\n" + customizations["additional_instructions"]

        if "metadata" in customizations:
            new_metadata.update(customizations["metadata"])

        if "tags" in customizations:
            new_tags.extend(customizations["tags"])

        return PromptVersion(
            id=new_id,
            name=f"{base_prompt.name} (Custom)",
            version=f"{base_prompt.version}-custom",
            content=new_content,
            description=f"Customized version of {base_prompt.name}",
            created_at=datetime.now().isoformat(),
            tags=new_tags,
            metadata=new_metadata
        )

    def audit_prompt_usage(self, project_path: str, prompt_id: str):
        """Record prompt usage for auditing"""
        # In a real implementation, this would log to a database
        print(f"Audited: Project {project_path} used prompt {prompt_id}")


# Global registry instance
prompt_registry = PromptRegistry()