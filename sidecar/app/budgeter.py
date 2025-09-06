from __future__ import annotations

from typing import Dict, Any, Optional
from .providers import provider_manager


class CostLatencyBudgeter:
    """Budgets cost and latency to pick optimal model/context size per task"""

    def __init__(self):
        self.budgets = {
            "cost_per_hour": 1.0,  # $1 per hour
            "max_latency_ms": 5000,  # 5 seconds
            "preferred_models": ["gpt-4", "gpt-3.5-turbo"]
        }

    def select_model_and_context(self, task_complexity: str, available_tokens: int) -> Dict[str, Any]:
        """
        Select optimal model and context size based on task complexity and budget
        """
        complexity_scores = {
            "low": 1,
            "medium": 2,
            "high": 3
        }

        complexity = complexity_scores.get(task_complexity, 2)

        # Select model based on complexity and cost
        if complexity >= 3 and self._can_afford_model("gpt-4"):
            model = "gpt-4"
            max_context = min(available_tokens, 8000)
        elif complexity >= 2 and self._can_afford_model("gpt-3.5-turbo"):
            model = "gpt-3.5-turbo"
            max_context = min(available_tokens, 4000)
        else:
            # Fallback to cheapest available
            model = "gpt-3.5-turbo"
            max_context = min(available_tokens, 2000)

        return {
            "model": model,
            "max_context": max_context,
            "estimated_cost": self._estimate_cost(model, max_context),
            "estimated_latency": self._estimate_latency(model, complexity)
        }

    def _can_afford_model(self, model: str) -> bool:
        """Check if we can afford using this model within budget"""
        # Get current usage
        stats = provider_manager.get_usage_stats()
        current_cost = sum(provider.get("estimated_cost", 0) for provider in stats.values())

        # Estimate cost for this model (rough hourly estimate)
        model_hourly_costs = {
            "gpt-4": 0.5,  # $0.50 per hour average
            "gpt-3.5-turbo": 0.1  # $0.10 per hour average
        }

        estimated_hourly = model_hourly_costs.get(model, 0.1)
        return current_cost + estimated_hourly <= self.budgets["cost_per_hour"]

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for a request"""
        costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }

        model_costs = costs.get(model, costs["gpt-3.5-turbo"])
        # Assume 70% output tokens
        input_tokens = tokens * 0.3
        output_tokens = tokens * 0.7

        return (input_tokens * model_costs["input"] + output_tokens * model_costs["output"]) / 1000

    def _estimate_latency(self, model: str, complexity: int) -> int:
        """Estimate latency in milliseconds"""
        base_latencies = {
            "gpt-4": 2000,
            "gpt-3.5-turbo": 1000
        }

        base = base_latencies.get(model, 1000)
        # Add complexity factor
        return base + (complexity - 1) * 500

    def update_budget(self, new_budget: Dict[str, Any]):
        """Update budget constraints"""
        self.budgets.update(new_budget)

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status"""
        stats = provider_manager.get_usage_stats()
        current_cost = sum(provider.get("estimated_cost", 0) for provider in stats.values())

        return {
            "current_cost": current_cost,
            "budget_limit": self.budgets["cost_per_hour"],
            "budget_remaining": max(0, self.budgets["cost_per_hour"] - current_cost),
            "max_latency": self.budgets["max_latency_ms"]
        }


# Global budgeter instance
budgeter = CostLatencyBudgeter()