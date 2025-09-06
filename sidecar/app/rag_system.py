from __future__ import annotations

import json
from typing import Dict, List, Any, Optional
from .memory_store import MemoryStore
from .providers import generate_with_provider


class RAGPolicy:
    """Policy for Retrieval-Augmented Generation"""

    def __init__(self, token_budget: int = 2000):
        self.token_budget = token_budget
        self.memory_store = MemoryStore()

    def retrieve_context(self, query: str, context_type: str = "general", max_items: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        # For now, use simple keyword matching
        # In practice, this would use semantic search with embeddings

        query_lower = query.lower()

        # Search decisions
        decisions = self.memory_store.get_decisions("current_project", limit=20)
        relevant_decisions = []

        for decision in decisions:
            spec_text = json.dumps(decision['spec']).lower()
            if any(keyword in spec_text for keyword in query_lower.split()):
                relevant_decisions.append(decision)
                if len(relevant_decisions) >= max_items:
                    break

        # Search similar embeddings if available
        similar_items = []
        # This would use vector search in a full implementation

        return {
            "decisions": relevant_decisions[:max_items],
            "similar_items": similar_items,
            "total_tokens": self._estimate_tokens(relevant_decisions + similar_items)
        }

    def _estimate_tokens(self, items: List[Dict[str, Any]]) -> int:
        """Estimate token count of retrieved items"""
        total = 0
        for item in items:
            total += len(json.dumps(item)) // 4  # Rough token estimation
        return total

    def should_retrieve(self, query_complexity: str, available_tokens: int) -> bool:
        """Determine if retrieval is warranted"""
        if query_complexity == "high" and available_tokens > self.token_budget * 0.5:
            return True
        elif query_complexity == "medium" and available_tokens > self.token_budget * 0.3:
            return True
        return False

    def summarize_overflow(self, context: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """Summarize context if it exceeds token limits"""
        current_tokens = context.get("total_tokens", 0)

        if current_tokens <= max_tokens:
            return context

        # Summarize by removing less relevant items
        summarized = context.copy()

        # Keep only the most recent decisions
        if len(summarized.get("decisions", [])) > 2:
            summarized["decisions"] = summarized["decisions"][:2]

        summarized["total_tokens"] = self._estimate_tokens(
            summarized.get("decisions", []) + summarized.get("similar_items", [])
        )

        return summarized


class RAGEnrichment:
    """Enrich TaskSpecs with RAG-retrieved information"""

    def __init__(self):
        self.rag_policy = RAGPolicy()
        self.memory_store = MemoryStore()

    def enrich_taskspec(self, taskspec: Dict[str, Any], project_context: str = "current_project") -> Dict[str, Any]:
        """Enrich a TaskSpec with historical patterns and examples"""
        enriched = taskspec.copy()

        # Extract key terms from the goal for retrieval
        query = taskspec.get("goal", "")
        if not query:
            return enriched

        # Retrieve relevant context
        context = self.rag_policy.retrieve_context(query, "taskspec")

        # Enrich constraints_inferred with patterns
        patterns = self._extract_patterns_from_context(context)
        if patterns:
            existing = enriched.get("constraints_inferred", [])
            enriched["constraints_inferred"] = existing + patterns

        # Add edge cases from similar past tasks
        edge_cases = self._extract_edge_cases_from_context(context)
        if edge_cases:
            existing = enriched.get("edge_cases", [])
            enriched["edge_cases"] = existing + edge_cases

        # Add examples from similar successful tasks
        examples = self._extract_examples_from_context(context)
        if examples:
            enriched["examples"] = examples

        return enriched

    def _extract_patterns_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract common patterns from historical decisions"""
        patterns = []

        decisions = context.get("decisions", [])
        if len(decisions) < 2:
            return patterns

        # Look for common constraints across similar tasks
        constraint_counts = {}

        for decision in decisions:
            spec = decision.get("spec", {})
            constraints = spec.get("constraints_inferred", [])

            for constraint in constraints:
                constraint_counts[constraint] = constraint_counts.get(constraint, 0) + 1

        # Add constraints that appear in multiple similar tasks
        for constraint, count in constraint_counts.items():
            if count >= 2:  # Appears in at least 2 similar tasks
                patterns.append(f"Pattern: {constraint}")

        return patterns

    def _extract_edge_cases_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract edge cases from historical decisions"""
        edge_cases = []

        decisions = context.get("decisions", [])

        for decision in decisions:
            spec = decision.get("spec", {})
            cases = spec.get("edge_cases", [])

            for case in cases:
                if case not in edge_cases:
                    edge_cases.append(case)

        return edge_cases[:5]  # Limit to 5 most relevant

    def _extract_examples_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract successful examples from historical decisions"""
        examples = []

        decisions = context.get("decisions", [])

        for decision in decisions:
            spec = decision.get("spec", {})
            goal = spec.get("goal", "")

            # Create example from successful past decisions
            if goal:
                examples.append(f"Similar task: {goal}")

        return examples[:3]  # Limit to 3 examples

    def store_successful_taskspec(self, taskspec: Dict[str, Any], project: str = "current_project"):
        """Store a successful TaskSpec for future RAG retrieval"""
        self.memory_store.store_decision(project, taskspec)

        # Extract and store patterns for future enrichment
        goal = taskspec.get("goal", "")
        if goal:
            # In a full implementation, this would create embeddings for semantic search
            pass

    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        return {
            "memory_stats": self.memory_store.get_stats(),
            "rag_policy": {
                "token_budget": self.rag_policy.token_budget
            }
        }


# Global instances
rag_policy = RAGPolicy()
rag_enrichment = RAGEnrichment()