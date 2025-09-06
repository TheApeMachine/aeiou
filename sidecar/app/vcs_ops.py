from __future__ import annotations

import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VCSDiff:
    """Represents a VCS diff with narration"""
    file_path: str
    additions: int
    deletions: int
    hunks: List[Dict[str, Any]]
    narration: str
    risk_level: str


@dataclass
class EphemeralBranch:
    """Represents an ephemeral branch for temporary edits"""
    branch_name: str
    base_branch: str
    created_at: datetime
    description: str
    files_modified: List[str]
    status: str  # 'active', 'committed', 'abandoned'


class VCSOperations:
    """VCS operations for ephemeral branches and diff narration"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.ephemeral_branches: Dict[str, EphemeralBranch] = {}
        self._ensure_git_repo()

    def _ensure_git_repo(self):
        """Ensure we're in a git repository"""
        if not (self.repo_path / '.git').exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def create_ephemeral_branch(self, description: str, base_branch: str = "main") -> str:
        """Create an ephemeral branch for temporary edits"""
        # Generate unique branch name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"aeiou_ephemeral_{timestamp}"

        # Create and checkout branch
        self._run_git_command(["checkout", "-b", branch_name, base_branch])

        branch = EphemeralBranch(
            branch_name=branch_name,
            base_branch=base_branch,
            created_at=datetime.now(),
            description=description,
            files_modified=[],
            status="active"
        )

        self.ephemeral_branches[branch_name] = branch
        return branch_name

    def commit_ephemeral_changes(self, branch_name: str, message: str) -> bool:
        """Commit changes on ephemeral branch"""
        if branch_name not in self.ephemeral_branches:
            return False

        branch = self.ephemeral_branches[branch_name]

        try:
            # Stage all changes
            self._run_git_command(["add", "."])

            # Commit
            self._run_git_command(["commit", "-m", message])

            branch.status = "committed"
            return True

        except subprocess.CalledProcessError:
            return False

    def merge_ephemeral_branch(self, branch_name: str, target_branch: str = "main") -> bool:
        """Merge ephemeral branch into target branch"""
        if branch_name not in self.ephemeral_branches:
            return False

        try:
            # Switch to target branch
            self._run_git_command(["checkout", target_branch])

            # Merge
            self._run_git_command(["merge", branch_name])

            # Clean up ephemeral branch
            self.cleanup_ephemeral_branch(branch_name)
            return True

        except subprocess.CalledProcessError:
            return False

    def cleanup_ephemeral_branch(self, branch_name: str):
        """Clean up ephemeral branch"""
        try:
            # Delete branch
            self._run_git_command(["branch", "-D", branch_name])

            # Remove from tracking
            if branch_name in self.ephemeral_branches:
                del self.ephemeral_branches[branch_name]

        except subprocess.CalledProcessError:
            pass  # Branch might already be deleted

    def abandon_ephemeral_branch(self, branch_name: str):
        """Abandon ephemeral branch without merging"""
        if branch_name in self.ephemeral_branches:
            self.ephemeral_branches[branch_name].status = "abandoned"

        self.cleanup_ephemeral_branch(branch_name)

    def get_diffs_with_narration(self, from_ref: str = "HEAD~1", to_ref: str = "HEAD") -> List[VCSDiff]:
        """Get diffs with AI narration"""
        try:
            # Get diff stat
            diff_stat = self._run_git_command(["diff", "--stat", from_ref, to_ref])

            # Get detailed diff
            diff_output = self._run_git_command(["diff", from_ref, to_ref])

            diffs = self._parse_diff_output(diff_output)

            # Add narration to each diff
            for diff in diffs:
                diff.narration = self._generate_diff_narration(diff)
                diff.risk_level = self._assess_diff_risk(diff)

            return diffs

        except subprocess.CalledProcessError:
            return []

    def _parse_diff_output(self, diff_output: str) -> List[VCSDiff]:
        """Parse git diff output into VCSDiff objects"""
        diffs = []

        # Split by file
        file_sections = re.split(r'^diff --git', diff_output, flags=re.MULTILINE)

        for section in file_sections[1:]:  # Skip first empty section
            lines = section.strip().split('\n')

            if len(lines) < 3:
                continue

            # Extract file path
            file_match = re.search(r'b/(.+)', lines[0])
            if not file_match:
                continue

            file_path = file_match.group(1)

            # Parse hunks
            hunks = []
            additions = 0
            deletions = 0

            i = 1
            while i < len(lines):
                if lines[i].startswith('@@'):
                    # Parse hunk
                    hunk_match = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', lines[i])
                    if hunk_match:
                        hunk_start = int(hunk_match.group(1))
                        hunk_lines = []

                        i += 1
                        hunk_add = 0
                        hunk_del = 0

                        while i < len(lines) and not lines[i].startswith('@@'):
                            if lines[i].startswith('+'):
                                hunk_add += 1
                            elif lines[i].startswith('-'):
                                hunk_del += 1
                            hunk_lines.append(lines[i])
                            i += 1

                        hunks.append({
                            'start_line': hunk_start,
                            'additions': hunk_add,
                            'deletions': hunk_del,
                            'lines': hunk_lines
                        })

                        additions += hunk_add
                        deletions += hunk_del
                else:
                    i += 1

            diffs.append(VCSDiff(
                file_path=file_path,
                additions=additions,
                deletions=deletions,
                hunks=hunks,
                narration="",  # Will be filled by narration function
                risk_level="low"  # Will be assessed
            ))

        return diffs

    def _generate_diff_narration(self, diff: VCSDiff) -> str:
        """Generate human-readable narration for a diff"""
        narration_parts = []

        if diff.additions > 0:
            narration_parts.append(f"Added {diff.additions} lines")

        if diff.deletions > 0:
            narration_parts.append(f"Removed {diff.deletions} lines")

        if len(diff.hunks) > 1:
            narration_parts.append(f"Modified in {len(diff.hunks)} sections")
        elif len(diff.hunks) == 1:
            narration_parts.append("Modified in 1 section")

        # Analyze the content for more specific narration
        content_analysis = self._analyze_diff_content(diff)
        if content_analysis:
            narration_parts.append(content_analysis)

        return ". ".join(narration_parts)

    def _analyze_diff_content(self, diff: VCSDiff) -> str:
        """Analyze diff content for specific insights"""
        insights = []

        # Check for function additions/modifications
        func_pattern = r'(?:def|function|class)\s+\w+'
        has_functions = any(re.search(func_pattern, line) for hunk in diff.hunks for line in hunk['lines'])
        if has_functions:
            insights.append("Modified function definitions")

        # Check for imports
        import_pattern = r'(?:import|from)\s+\w+'
        has_imports = any(re.search(import_pattern, line) for hunk in diff.hunks for line in hunk['lines'])
        if has_imports:
            insights.append("Updated imports")

        # Check for comments
        comment_pattern = r'#|//|/\*|\*/'
        has_comments = any(re.search(comment_pattern, line) for hunk in diff.hunks for line in hunk['lines'])
        if has_comments:
            insights.append("Modified comments/documentation")

        return "; ".join(insights) if insights else ""

    def _assess_diff_risk(self, diff: VCSDiff) -> str:
        """Assess the risk level of a diff"""
        risk_score = 0

        # Large diffs are riskier
        total_changes = diff.additions + diff.deletions
        if total_changes > 100:
            risk_score += 3
        elif total_changes > 50:
            risk_score += 2
        elif total_changes > 20:
            risk_score += 1

        # Multiple hunks indicate scattered changes
        if len(diff.hunks) > 5:
            risk_score += 2
        elif len(diff.hunks) > 2:
            risk_score += 1

        # Function modifications are moderately risky
        func_changes = sum(1 for hunk in diff.hunks
                          for line in hunk['lines']
                          if re.search(r'(?:def|function|class)\s+\w+', line))
        risk_score += min(func_changes, 2)

        if risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"

    def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output"""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def get_ephemeral_branches(self) -> List[Dict[str, Any]]:
        """Get list of active ephemeral branches"""
        return [{
            'branch_name': branch.branch_name,
            'base_branch': branch.base_branch,
            'created_at': branch.created_at.isoformat(),
            'description': branch.description,
            'status': branch.status,
            'files_modified': len(branch.files_modified)
        } for branch in self.ephemeral_branches.values()]

    def squash_commits(self, branch_name: str, message: str) -> bool:
        """Squash commits on a branch"""
        try:
            # Interactive rebase to squash
            commit_count = int(self._run_git_command(["rev-list", "--count", f"{branch_name}~1..{branch_name}"]))

            if commit_count > 1:
                # Create squash script
                squash_script = f"""#!/bin/bash
echo "Squashing {commit_count} commits"
GIT_SEQUENCE_EDITOR=true git rebase -i HEAD~{commit_count}
git commit --amend -m "{message}"
"""
                script_path = self.repo_path / "squash_script.sh"
                with open(script_path, 'w') as f:
                    f.write(squash_script)

                os.chmod(script_path, 0o755)
                subprocess.run([str(script_path)], cwd=self.repo_path, check=True)
                script_path.unlink()

            return True

        except (subprocess.CalledProcessError, ValueError):
            return False


# Global VCS operations instance
vcs_ops = VCSOperations()