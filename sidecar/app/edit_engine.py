from __future__ import annotations

import difflib
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EditOperation:
    """Represents a single edit operation"""
    operation_type: str  # 'insert', 'replace', 'delete'
    file_path: str
    start_line: int
    end_line: int
    old_content: str
    new_content: str
    description: str = ""


@dataclass
class EditResult:
    """Result of an edit operation"""
    success: bool
    operations: List[EditOperation]
    error_message: Optional[str] = None
    diff: Optional[str] = None


class AtomicEditEngine:
    """Atomic edit engine with AST-guided edits and fuzzy fallback"""

    def __init__(self):
        self.undo_stack: List[List[EditOperation]] = []
        self.redo_stack: List[List[EditOperation]] = []

    def apply_edits(self, operations: List[EditOperation]) -> EditResult:
        """Apply a list of edit operations atomically"""
        try:
            # Validate all operations first
            for op in operations:
                if not self._validate_operation(op):
                    return EditResult(
                        success=False,
                        operations=[],
                        error_message=f"Invalid operation: {op.description}"
                    )

            # Apply all operations
            applied_ops = []
            for op in operations:
                if self._apply_single_operation(op):
                    applied_ops.append(op)
                else:
                    # Rollback on failure
                    self._rollback_operations(applied_ops)
                    return EditResult(
                        success=False,
                        operations=applied_ops,
                        error_message=f"Failed to apply operation: {op.description}"
                    )

            # Generate diff
            diff = self._generate_diff(applied_ops)

            # Store for undo
            self.undo_stack.append(applied_ops)
            self.redo_stack.clear()  # Clear redo stack on new operation

            return EditResult(
                success=True,
                operations=applied_ops,
                diff=diff
            )

        except Exception as e:
            return EditResult(
                success=False,
                operations=[],
                error_message=f"Edit failed: {str(e)}"
            )

    def _validate_operation(self, operation: EditOperation) -> bool:
        """Validate an edit operation"""
        if not Path(operation.file_path).exists():
            return False

        # Check line numbers are valid
        try:
            with open(operation.file_path, 'r') as f:
                lines = f.readlines()
                total_lines = len(lines)

            if operation.start_line < 1 or operation.start_line > total_lines + 1:
                return False

            if operation.end_line < operation.start_line - 1 or operation.end_line > total_lines:
                return False

        except (IOError, OSError):
            return False

        return True

    def _apply_single_operation(self, operation: EditOperation) -> bool:
        """Apply a single edit operation"""
        try:
            with open(operation.file_path, 'r') as f:
                lines = f.readlines()

            if operation.operation_type == 'insert':
                # Insert new content at start_line
                lines.insert(operation.start_line - 1, operation.new_content + '\n')
            elif operation.operation_type == 'replace':
                # Replace lines from start_line to end_line
                new_lines = operation.new_content.split('\n')
                lines[operation.start_line - 1:operation.end_line] = [line + '\n' for line in new_lines]
            elif operation.operation_type == 'delete':
                # Delete lines from start_line to end_line
                del lines[operation.start_line - 1:operation.end_line]

            with open(operation.file_path, 'w') as f:
                f.writelines(lines)

            return True

        except (IOError, OSError):
            return False

    def _rollback_operations(self, operations: List[EditOperation]):
        """Rollback a list of operations"""
        # Reverse the operations and apply them
        reversed_ops = []
        for op in reversed(operations):
            if op.operation_type == 'insert':
                reversed_ops.append(EditOperation(
                    operation_type='delete',
                    file_path=op.file_path,
                    start_line=op.start_line,
                    end_line=op.start_line,
                    old_content='',
                    new_content='',
                    description=f"Rollback insert: {op.description}"
                ))
            elif op.operation_type == 'replace':
                reversed_ops.append(EditOperation(
                    operation_type='replace',
                    file_path=op.file_path,
                    start_line=op.start_line,
                    end_line=op.start_line + len(op.new_content.split('\n')) - 1,
                    old_content=op.new_content,
                    new_content=op.old_content,
                    description=f"Rollback replace: {op.description}"
                ))
            elif op.operation_type == 'delete':
                reversed_ops.append(EditOperation(
                    operation_type='insert',
                    file_path=op.file_path,
                    start_line=op.start_line,
                    end_line=op.start_line - 1,
                    old_content='',
                    new_content=op.old_content,
                    description=f"Rollback delete: {op.description}"
                ))

        for op in reversed_ops:
            self._apply_single_operation(op)

    def undo_last_operation(self) -> bool:
        """Undo the last operation"""
        if not self.undo_stack:
            return False

        operations = self.undo_stack.pop()
        self._rollback_operations(operations)
        self.redo_stack.append(operations)
        return True

    def redo_last_operation(self) -> bool:
        """Redo the last undone operation"""
        if not self.redo_stack:
            return False

        operations = self.redo_stack.pop()
        for op in operations:
            self._apply_single_operation(op)
        self.undo_stack.append(operations)
        return True

    def _generate_diff(self, operations: List[EditOperation]) -> str:
        """Generate a unified diff for the operations"""
        diffs = []

        for op in operations:
            try:
                with open(op.file_path, 'r') as f:
                    current_content = f.read()

                # Create diff
                diff = list(difflib.unified_diff(
                    op.old_content.splitlines(keepends=True),
                    op.new_content.splitlines(keepends=True),
                    fromfile=f"a/{op.file_path}",
                    tofile=f"b/{op.file_path}",
                    lineterm=""
                ))

                if diff:
                    diffs.extend(diff)
                    diffs.append("")  # Add blank line between files

            except (IOError, OSError):
                continue

        return '\n'.join(diffs)

    def create_ast_guided_edit(self, file_path: str, target_symbol: str,
                              new_content: str, language: str = 'python') -> Optional[EditOperation]:
        """Create an AST-guided edit operation"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            lines = content.split('\n')

            # Find the target symbol (simplified - would use actual AST parsing)
            for i, line in enumerate(lines):
                if target_symbol in line and ('def ' in line or 'class ' in line):
                    # Found the symbol, create replace operation
                    return EditOperation(
                        operation_type='replace',
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=i + 1,
                        old_content=line,
                        new_content=new_content,
                        description=f"AST-guided edit of {target_symbol}"
                    )

        except (IOError, OSError):
            pass

        return None

    def create_fuzzy_patch_edit(self, file_path: str, search_pattern: str,
                               replacement: str) -> Optional[EditOperation]:
        """Create a fuzzy patch edit operation using regex"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Find the pattern
            match = re.search(search_pattern, content, re.MULTILINE | re.DOTALL)
            if match:
                start_pos = match.start()
                end_pos = match.end()

                # Convert positions to line numbers
                lines_before = content[:start_pos].count('\n') + 1
                lines_in_match = content[start_pos:end_pos].count('\n') + 1

                return EditOperation(
                    operation_type='replace',
                    file_path=file_path,
                    start_line=lines_before,
                    end_line=lines_before + lines_in_match - 1,
                    old_content=match.group(),
                    new_content=replacement,
                    description=f"Fuzzy patch: {search_pattern[:50]}..."
                )

        except (IOError, OSError):
            pass

        return None

    def get_edit_history(self) -> List[Dict[str, Any]]:
        """Get edit history for replay"""
        history = []

        for i, operations in enumerate(self.undo_stack):
            history.append({
                'id': i,
                'operations': len(operations),
                'description': operations[0].description if operations else "Unknown",
                'timestamp': None  # Would need to add timestamps
            })

        return history


# Global edit engine instance
edit_engine = AtomicEditEngine()