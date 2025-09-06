from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class FileNode:
    """Represents a file in the project graph"""
    path: str
    language: str
    size: int
    last_modified: str
    symbols: List[Dict[str, Any]] = None
    imports: List[str] = None
    exports: List[str] = None

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = []
        if self.imports is None:
            self.imports = []
        if self.exports is None:
            self.exports = []


@dataclass
class SymbolNode:
    """Represents a symbol (function, class, etc.) in the project"""
    id: str
    name: str
    kind: str
    file_path: str
    line: int
    column: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    references: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.references is None:
            self.references = []


@dataclass
class DependencyEdge:
    """Represents a dependency relationship"""
    from_file: str
    to_file: str
    dependency_type: str  # 'import', 'inherit', 'call', etc.
    symbol_name: Optional[str] = None
    line: Optional[int] = None


class ProjectGraphBuilder:
    """Builds project graph from LSP/Tree-sitter analysis"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.files: Dict[str, FileNode] = {}
        self.symbols: Dict[str, SymbolNode] = {}
        self.dependencies: List[DependencyEdge] = []
        self.owners: Dict[str, str] = {}  # symbol_id -> owner

    def build_graph(self) -> Dict[str, Any]:
        """Build the complete project graph"""
        self._scan_files()
        self._extract_symbols()
        self._analyze_dependencies()
        self._determine_ownership()

        return {
            "files": self.files,
            "symbols": self.symbols,
            "dependencies": self.dependencies,
            "owners": self.owners,
            "metadata": {
                "project_root": str(self.project_root),
                "build_time": datetime.now().isoformat(),
                "total_files": len(self.files),
                "total_symbols": len(self.symbols),
                "total_dependencies": len(self.dependencies)
            }
        }

    def _scan_files(self):
        """Scan project files and create file nodes"""
        extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.lua': 'lua'
        }

        for root, dirs, files in os.walk(self.project_root):
            # Skip common directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', 'target', 'build'}]

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix

                if ext in extensions:
                    try:
                        stat = file_path.stat()
                        relative_path = file_path.relative_to(self.project_root)

                        self.files[str(relative_path)] = FileNode(
                            path=str(relative_path),
                            language=extensions[ext],
                            size=stat.st_size,
                            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                        )
                    except (OSError, ValueError):
                        continue

    def _extract_symbols(self):
        """Extract symbols from files using basic analysis"""
        for file_path, file_node in self.files.items():
            full_path = self.project_root / file_path

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                symbols = self._extract_symbols_from_content(content, lines, file_path, file_node.language)
                file_node.symbols = symbols

                # Store symbols globally
                for symbol in symbols:
                    symbol_id = f"{file_path}:{symbol['name']}:{symbol['line']}"
                    self.symbols[symbol_id] = SymbolNode(
                        id=symbol_id,
                        name=symbol['name'],
                        kind=symbol['kind'],
                        file_path=file_path,
                        line=symbol['line'],
                        column=symbol.get('column', 0),
                        signature=symbol.get('signature'),
                        docstring=symbol.get('docstring')
                    )

            except (IOError, UnicodeDecodeError):
                continue

    def _extract_symbols_from_content(self, content: str, lines: List[str], file_path: str, language: str) -> List[Dict[str, Any]]:
        """Extract symbols from file content"""
        symbols = []

        if language == 'python':
            symbols.extend(self._extract_python_symbols(lines))
        elif language in ['javascript', 'typescript']:
            symbols.extend(self._extract_js_symbols(lines))
        # Add more language-specific extractors as needed

        return symbols

    def _extract_python_symbols(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract Python symbols"""
        symbols = []

        for i, line in enumerate(lines):
            line = line.strip()

            # Functions
            if line.startswith('def '):
                name = line.split('def ')[1].split('(')[0].strip()
                symbols.append({
                    'name': name,
                    'kind': 'function',
                    'line': i + 1,
                    'signature': line
                })

            # Classes
            elif line.startswith('class '):
                name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                symbols.append({
                    'name': name,
                    'kind': 'class',
                    'line': i + 1,
                    'signature': line
                })

        return symbols

    def _extract_js_symbols(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript symbols"""
        symbols = []

        for i, line in enumerate(lines):
            line = line.strip()

            # Functions
            if 'function ' in line or line.startswith('const ') and '=>' in line:
                symbols.append({
                    'name': 'function_name',  # Would need better parsing
                    'kind': 'function',
                    'line': i + 1,
                    'signature': line
                })

            # Classes
            if line.startswith('class '):
                name = line.split('class ')[1].split(' ')[0].split('{')[0].strip()
                symbols.append({
                    'name': name,
                    'kind': 'class',
                    'line': i + 1,
                    'signature': line
                })

        return symbols

    def _analyze_dependencies(self):
        """Analyze dependencies between files"""
        for file_path, file_node in self.files.items():
            full_path = self.project_root / file_path

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                deps = self._extract_dependencies(content, file_node.language)
                file_node.imports = deps

                # Create dependency edges
                for dep in deps:
                    # Try to resolve the dependency to a file in the project
                    resolved_file = self._resolve_dependency(dep, file_path)
                    if resolved_file and resolved_file in self.files:
                        self.dependencies.append(DependencyEdge(
                            from_file=file_path,
                            to_file=resolved_file,
                            dependency_type='import',
                            symbol_name=dep
                        ))

            except (IOError, UnicodeDecodeError):
                continue

    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """Extract dependencies from file content"""
        deps = []

        if language == 'python':
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Simple extraction - could be more sophisticated
                    deps.append(line)

        elif language in ['javascript', 'typescript']:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('require('):
                    deps.append(line)

        return deps

    def _resolve_dependency(self, dep: str, from_file: str) -> Optional[str]:
        """Resolve a dependency to a file path"""
        # This is a simplified resolver - in practice, you'd use the language's module resolution
        if 'import' in dep or 'from' in dep:
            # Try to find a matching file
            for file_path in self.files:
                if file_path.endswith('.py') and Path(file_path).stem in dep:
                    return file_path

        return None

    def _determine_ownership(self):
        """Determine ownership of symbols (who "owns" each symbol)"""
        # Simple ownership: the file that defines the symbol owns it
        for symbol_id, symbol in self.symbols.items():
            self.owners[symbol_id] = symbol.file_path

    def get_symbol_references(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Get all references to a symbol across the project"""
        references = []

        for file_path, file_node in self.files.items():
            # This would need actual LSP/references analysis
            # For now, return basic info
            if any(symbol_name in str(symbol) for symbol in file_node.symbols):
                references.append({
                    'file': file_path,
                    'symbol': symbol_name,
                    'type': 'definition'
                })

        return references

    def get_file_dependencies(self, file_path: str) -> List[str]:
        """Get all files that this file depends on"""
        deps = []
        for edge in self.dependencies:
            if edge.from_file == file_path:
                deps.append(edge.to_file)
        return deps

    def get_reverse_dependencies(self, file_path: str) -> List[str]:
        """Get all files that depend on this file"""
        deps = []
        for edge in self.dependencies:
            if edge.to_file == file_path:
                deps.append(edge.from_file)
        return deps