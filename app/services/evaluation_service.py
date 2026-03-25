from typing import Dict, List, Any

from app.services.memory_service import MemoryService
from app.services.continuity_service import ContinuityService
from app.services.evolution_service import EvolutionService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


class EvaluationService:
    def __init__(self):
        self.memory_service = MemoryService()
        self.continuity_service = ContinuityService()
        self.evolution_service = EvolutionService()
        self.retrieval_orchestrator = RetrievalOrchestrator()

    def run_all_evaluations(self) -> Dict[str, Any]:
        results = {
            "fact_recall": self.evaluate_fact_recall(),
            "contradiction_state": self.evaluate_contradiction_state(),
            "continuity_state": self.evaluate_continuity_state(),
            "retrieval_modes": self.evaluate_retrieval_modes(),
            "reflection_coverage": self.evaluate_reflection_coverage(),
            "overall": {}
        }

        passed = 0
        total = 0

        for _, section in results.items():
            if isinstance(section, dict) and "passed" in section:
                total += 1
                if section["passed"]:
                    passed += 1

        results["overall"] = {
            "passed": passed,
            "total": total,
            "score": round((passed / total), 3) if total else 0.0
        }

        return results

    def evaluate_fact_recall(self) -> Dict[str, Any]:
        facts = self.memory_service.get_prompt_safe_facts(limit=50)

        checks = {
            "has_active_facts": len(facts) > 0,
            "all_are_active": all(f.get("status") == "active" for f in facts),
            "no_restricted_visibility": all(f.get("visibility") != "restricted" for f in facts),
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "fact_count": len(facts)
        }

    def evaluate_contradiction_state(self) -> Dict[str, Any]:
        all_facts = self.memory_service.get_all_facts()

        active_texts = [f["fact_text"].strip().lower() for f in all_facts if f.get("status") == "active"]
        duplicate_active_count = len(active_texts) - len(set(active_texts))

        superseded_count = sum(1 for f in all_facts if f.get("status") == "superseded")

        checks = {
            "no_duplicate_active_facts": duplicate_active_count == 0,
            "has_status_field_coverage": all("status" in f for f in all_facts),
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "superseded_count": superseded_count,
            "duplicate_active_count": duplicate_active_count
        }

    def evaluate_continuity_state(self) -> Dict[str, Any]:
        projects = self.continuity_service.list_projects()
        goals = self.continuity_service.list_goals()
        open_loops = self.continuity_service.list_open_loops()

        checks = {
            "projects_accessible": isinstance(projects, list),
            "goals_accessible": isinstance(goals, list),
            "open_loops_accessible": isinstance(open_loops, list),
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "project_count": len(projects),
            "goal_count": len(goals),
            "open_loop_count": len(open_loops)
        }

    def evaluate_retrieval_modes(self) -> Dict[str, Any]:
        sample_query = "What should I do next?"
        balanced = self.retrieval_orchestrator.build_context_package(
            query=sample_query,
            retrieval_mode="balanced"
        )
        privacy_safe = self.retrieval_orchestrator.build_context_package(
            query=sample_query,
            retrieval_mode="privacy_safe"
        )
        document_first = self.retrieval_orchestrator.build_context_package(
            query="What does the document say?",
            retrieval_mode="document_first"
        )

        balanced_facts = balanced.get("facts", [])
        privacy_facts = privacy_safe.get("facts", [])
        document_budget = document_first.get("budget_profile", {}).get("documents", 0)
        balanced_budget = balanced.get("budget_profile", {}).get("documents", 0)

        checks = {
            "privacy_safe_filters_or_reduces_facts": len(privacy_facts) <= len(balanced_facts),
            "document_first_increases_doc_budget": document_budget >= balanced_budget,
            "balanced_mode_present": balanced.get("retrieval_mode") == "balanced",
            "privacy_mode_present": privacy_safe.get("retrieval_mode") == "privacy_safe",
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "balanced_fact_count": len(balanced_facts),
            "privacy_safe_fact_count": len(privacy_facts),
            "document_first_doc_budget": document_budget,
            "balanced_doc_budget": balanced_budget
        }

    def evaluate_reflection_coverage(self) -> Dict[str, Any]:
        reflections = self.evolution_service.get_recent_reflections(limit=10)

        structured_fields_present = all(
            all(field in r for field in [
                "user_insights",
                "preference_updates",
                "project_updates",
                "goal_updates",
                "potential_conflicts",
                "recommended_long_term_memories"
            ])
            for r in reflections
        ) if reflections else True

        insight_summary = self.evolution_service.get_reflection_insight_summary(limit=5)

        checks = {
            "structured_fields_present": structured_fields_present,
            "insight_summary_has_expected_keys": all(
                key in insight_summary for key in [
                    "user_insights",
                    "preference_updates",
                    "project_updates",
                    "goal_updates",
                    "potential_conflicts",
                    "recommended_long_term_memories"
                ]
            )
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "reflection_count": len(reflections),
            "insight_summary_counts": {
                key: len(insight_summary.get(key, []))
                for key in insight_summary
            }
        }
