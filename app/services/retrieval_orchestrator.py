from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.rag_service import RAGService
from app.services.semantic_memory_service import SemanticMemoryService
from app.services.continuity_service import ContinuityService
from app.services.evolution_service import EvolutionService
from app.services.temporal_service import TemporalService
from app.services.proactive_service import ProactiveService
from app.services.reasoning_service import ReasoningService
from app.services.prompt_security_service import PromptSecurityService
from app.services.trust_service import TrustService


class RetrievalOrchestrator:
    def __init__(self):
        self.memory_service = MemoryService()
        self.profile_service = ProfileService()
        self.rag_service = RAGService()
        self.semantic_memory_service = SemanticMemoryService()
        self.continuity_service = ContinuityService()
        self.evolution_service = EvolutionService()
        self.temporal_service = TemporalService()
        self.proactive_service = ProactiveService()
        self.reasoning_service = ReasoningService()
        self.prompt_security_service = PromptSecurityService()
        self.trust_service = TrustService()

    def classify_query(self, query: str) -> str:
        q = query.lower().strip()

        personal_triggers = [
            "remember", "about me", "what do you know about me", "my preferences",
            "my name", "where do i live", "did i tell you", "what do you know",
            "what do you remember", "who am i"
        ]

        document_triggers = [
            "document", "file", "pdf", "doc", "docs", "in the text",
            "in the document", "uploaded", "according to the document"
        ]

        continuity_triggers = [
            "continue", "where did we leave off", "what were we doing",
            "next step", "status", "progress", "continue working",
            "pick up where we left off", "what next", "what should i do next",
            "what remains", "what is unresolved", "what's unresolved",
            "what is pending", "what's pending", "what should we do next",
            "next actions", "what are my priorities", "what should i work on"
        ]

        knowledge_memory_triggers = [
            "based on what i told you", "based on my project", "using the docs and memory",
            "consider my goals", "consider what you know about me"
        ]

        if any(trigger in q for trigger in knowledge_memory_triggers):
            return "knowledge_plus_memory"

        if any(trigger in q for trigger in document_triggers):
            return "document_qa"

        if any(trigger in q for trigger in continuity_triggers):
            return "project_continuity"

        if any(trigger in q for trigger in personal_triggers):
            return "personal_memory"

        if self.is_temporal_query(query):
            return "personal_memory"

        return "general_chat"

    def is_temporal_query(self, query: str) -> bool:
        q = query.lower().strip()

        temporal_triggers = [
            "what changed",
            "what is current",
            "what's current",
            "what do i currently",
            "where do i live now",
            "where did i live before",
            "used to",
            "previously",
            "before",
            "current",
            "earlier",
            "history",
            "timeline",
            "has changed",
            "change over time"
        ]

        return any(trigger in q for trigger in temporal_triggers)

    def is_proactive_query(self, query: str) -> bool:
        q = query.lower().strip()

        proactive_triggers = [
            "what should i focus on",
            "what needs my attention",
            "give me a check-in",
            "status update",
            "what are my priorities",
            "what is stalled",
            "what needs review",
            "what should happen next",
            "brief me",
            "give me a briefing"
        ]

        return any(trigger in q for trigger in proactive_triggers)

    def _get_proactive_context(self, is_proactive_query: bool, query_type: str) -> Dict:
        use_proactive = is_proactive_query or query_type == "project_continuity"

        if not use_proactive:
            return {
                "used": False,
                "briefing": None
            }

        briefing = self.proactive_service.generate_proactive_briefing()

        return {
            "used": True,
            "briefing": briefing
        }

    def _get_reasoning_context(
        self,
        query_type: str,
        conversation_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> Dict:
        use_reasoning = query_type in {"project_continuity", "knowledge_plus_memory"}

        if not use_reasoning:
            return {
                "used": False,
                "states": []
            }

        states = self.reasoning_service.get_relevant_reasoning_states(
            conversation_id=conversation_id,
            project_id=project_id,
            limit=3
        )

        return {
            "used": len(states) > 0,
            "states": states
        }

    def _get_continuity_context(
        self,
        query_type: str,
        retrieval_mode: str,
        active_project_id: Optional[int] = None
    ) -> Dict:
        project_limit = 3
        goal_limit = 5
        open_loop_limit = 6

        if retrieval_mode == "deep_memory":
            project_limit = 5
            goal_limit = 8
            open_loop_limit = 10
        elif retrieval_mode == "focused":
            project_limit = 2
            goal_limit = 3
            open_loop_limit = 3
        elif retrieval_mode == "document_first":
            project_limit = 1
            goal_limit = 2
            open_loop_limit = 2
        elif retrieval_mode == "privacy_safe":
            project_limit = 1
            goal_limit = 2
            open_loop_limit = 2

        use_continuity = query_type in {"project_continuity", "knowledge_plus_memory", "personal_memory", "general_chat"}

        if not use_continuity:
            return {
                "projects": [],
                "goals": [],
                "open_loops": [],
                "next_actions": [],
                "used": False,
                "active_project_id": active_project_id
            }

        if active_project_id is not None:
            project = self.continuity_service.get_project_by_id(active_project_id)
            projects = [project] if project else []
            goals = self.continuity_service.get_active_goals(limit=goal_limit, project_id=active_project_id)
            open_loops = self.continuity_service.get_active_open_loops(limit=open_loop_limit, project_id=active_project_id)
        else:
            projects = self.continuity_service.get_active_projects(limit=project_limit)
            goals = self.continuity_service.get_active_goals(limit=goal_limit)
            open_loops = self.continuity_service.get_active_open_loops(limit=open_loop_limit)

        next_actions = self.continuity_service.suggest_next_actions(limit=5)

        return {
            "projects": projects,
            "goals": goals,
            "open_loops": open_loops,
            "next_actions": next_actions,
            "used": True,
            "active_project_id": active_project_id
        }

    def _get_reflection_context(self, query_type: str, retrieval_mode: str) -> Dict:
        use_reflections = query_type in {"personal_memory", "project_continuity", "knowledge_plus_memory"}

        if not use_reflections:
            return {
                "used": False,
                "recent_reflections": [],
                "recent_daily_learnings": [],
                "insight_summary": {}
            }

        reflection_limit = 3
        daily_learning_limit = 2

        if retrieval_mode == "deep_memory":
            reflection_limit = 5
            daily_learning_limit = 3
        elif retrieval_mode == "focused":
            reflection_limit = 2
            daily_learning_limit = 1
        elif retrieval_mode == "document_first":
            reflection_limit = 1
            daily_learning_limit = 1
        elif retrieval_mode == "privacy_safe":
            reflection_limit = 2
            daily_learning_limit = 1

        return {
            "used": True,
            "recent_reflections": self.evolution_service.get_recent_reflections(limit=reflection_limit),
            "recent_daily_learnings": self.evolution_service.get_recent_daily_learnings(limit=daily_learning_limit),
            "insight_summary": self.evolution_service.get_reflection_insight_summary(limit=reflection_limit)
        }

    def _get_temporal_context(self, is_temporal_query: bool, query_type: str) -> Dict:
        use_temporal = is_temporal_query or query_type in {"personal_memory", "project_continuity"}

        if not use_temporal:
            return {
                "used": False,
                "changes": {},
                "summaries": [],
                "reconfirmation_candidates": []
            }

        changes = self.temporal_service.detect_all_changes()

        summaries = []
        for kind, item in changes.items():
            if item.get("summary"):
                summaries.append({
                    "kind": kind,
                    "summary": item["summary"],
                    "has_change": item.get("has_change", False),
                    "current_value": item.get("current_value"),
                    "previous_value": item.get("previous_value")
                })

        reconfirmation_candidates = self.temporal_service.get_reconfirmation_candidates(stale_after_days=30)

        return {
            "used": True,
            "changes": changes,
            "summaries": summaries,
            "reconfirmation_candidates": reconfirmation_candidates[:5]
        }

    def build_context_package(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        retrieval_mode: str = "balanced",
        active_project_id: Optional[int] = None
    ) -> Dict:
        query_type = self.classify_query(query)
        is_temporal_query = self.is_temporal_query(query)
        is_proactive_query = self.is_proactive_query(query)
        base_budgets = self._get_budget_profile(query_type)
        budgets = self._apply_mode_to_budget_profile(base_budgets, retrieval_mode)
        retrieval_trace = []
        continuity_context = self._get_continuity_context(query_type, retrieval_mode, active_project_id)
        reflection_context = self._get_reflection_context(query_type, retrieval_mode)
        temporal_context = self._get_temporal_context(is_temporal_query, query_type)
        proactive_context = self._get_proactive_context(is_proactive_query, query_type)
        reasoning_context = self._get_reasoning_context(query_type, conversation_id, active_project_id)

        recent_messages = []
        raw_recent_messages = []
        if conversation_id is not None:
            raw_recent_messages = self.memory_service.get_recent_messages(
                conversation_id=conversation_id,
                limit=settings.MAX_HISTORY_MESSAGES
            )
            message_budget = self._budget_messages_with_trace(raw_recent_messages, budgets["recent_messages"])
            recent_messages = message_budget["kept"]

            retrieval_trace.append({
                "source": "recent_messages",
                "budget_chars": budgets["recent_messages"],
                "candidates_before_count": len(raw_recent_messages),
                "kept_count": len(message_budget["kept"]),
                "dropped_count": len(message_budget["dropped"]),
                "used_chars": message_budget["used_chars"]
            })

        facts: List[Dict] = []
        profile_summary = ""
        retrieved_memories: List[Dict] = []
        retrieved_contexts: List[Dict] = []

        retrieval_plan = {
            "used_recent_messages": bool(conversation_id),
            "used_facts": False,
            "used_profile": False,
            "used_semantic_memories": False,
            "used_documents": False,
            "used_continuity": continuity_context["used"],
            "used_reflections": reflection_context["used"],
            "used_temporal_context": temporal_context["used"],
            "used_proactive_context": proactive_context["used"],
            "used_reasoning_context": reasoning_context["used"]
        }

        if query_type == "personal_memory":
            raw_facts = self.memory_service.get_prompt_safe_facts(limit=20)
            raw_facts = self._filter_facts_by_mode(raw_facts, retrieval_mode)
            reranked_facts = self._rerank_facts(raw_facts, query_type)
            fact_budget = self._budget_facts_with_trace(reranked_facts, budgets["facts"])
            facts = fact_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="facts",
                budget_chars=budgets["facts"],
                candidates_before=reranked_facts,
                kept_items=fact_budget["kept"],
                dropped_items=fact_budget["dropped"],
                content_key="fact_text"
            ))

            profile_summary = self.profile_service.profile_summary_text()
            profile_summary = self._trim_text(profile_summary, budgets["profile_summary"])

            raw_memories = self.semantic_memory_service.retrieve_relevant_memories(query, top_k=8)
            reranked_memories = self._rerank_memories(raw_memories, query_type)
            memory_budget = self._budget_items_with_trace(reranked_memories, budgets["semantic_memories"])
            retrieved_memories = memory_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="semantic_memories",
                budget_chars=budgets["semantic_memories"],
                candidates_before=reranked_memories,
                kept_items=memory_budget["kept"],
                dropped_items=memory_budget["dropped"],
                content_key="content"
            ))

            retrieval_plan["used_facts"] = True
            retrieval_plan["used_profile"] = True
            retrieval_plan["used_semantic_memories"] = True

        elif query_type == "document_qa":
            raw_contexts = self.rag_service.retrieve_context(query, top_k=10)
            reranked_contexts = self._rerank_contexts(raw_contexts, query_type)
            context_budget = self._budget_items_with_trace(reranked_contexts, budgets["documents"])
            retrieved_contexts = context_budget["kept"]
            retrieved_contexts = self.prompt_security_service.sanitize_untrusted_items(
                retrieved_contexts,
                content_key="content",
                source_type="document"
            )
            retrieved_contexts = self.trust_service.annotate_items(
                retrieved_contexts,
                source_type="document",
                content_key="content"
            )

            retrieval_trace.append(self._build_source_trace(
                source_name="documents",
                budget_chars=budgets["documents"],
                candidates_before=reranked_contexts,
                kept_items=context_budget["kept"],
                dropped_items=context_budget["dropped"],
                content_key="content"
            ))

            retrieval_plan["used_documents"] = True

        elif query_type == "project_continuity":
            raw_facts = self.memory_service.get_prompt_safe_facts(limit=15)
            raw_facts = self._filter_facts_by_mode(raw_facts, retrieval_mode)
            reranked_facts = self._rerank_facts(raw_facts, query_type)
            fact_budget = self._budget_facts_with_trace(reranked_facts, budgets["facts"])
            facts = fact_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="facts",
                budget_chars=budgets["facts"],
                candidates_before=reranked_facts,
                kept_items=fact_budget["kept"],
                dropped_items=fact_budget["dropped"],
                content_key="fact_text"
            ))

            profile_summary = self.profile_service.profile_summary_text()
            profile_summary = self._trim_text(profile_summary, budgets["profile_summary"])

            raw_memories = self.semantic_memory_service.retrieve_relevant_memories(query, top_k=10)
            reranked_memories = self._rerank_memories(raw_memories, query_type)
            memory_budget = self._budget_items_with_trace(reranked_memories, budgets["semantic_memories"])
            retrieved_memories = memory_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="semantic_memories",
                budget_chars=budgets["semantic_memories"],
                candidates_before=reranked_memories,
                kept_items=memory_budget["kept"],
                dropped_items=memory_budget["dropped"],
                content_key="content"
            ))

            retrieval_plan["used_facts"] = True
            retrieval_plan["used_profile"] = True
            retrieval_plan["used_semantic_memories"] = True

        elif query_type == "knowledge_plus_memory":
            raw_facts = self.memory_service.get_prompt_safe_facts(limit=15)
            raw_facts = self._filter_facts_by_mode(raw_facts, retrieval_mode)
            reranked_facts = self._rerank_facts(raw_facts, query_type)
            fact_budget = self._budget_facts_with_trace(reranked_facts, budgets["facts"])
            facts = fact_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="facts",
                budget_chars=budgets["facts"],
                candidates_before=reranked_facts,
                kept_items=fact_budget["kept"],
                dropped_items=fact_budget["dropped"],
                content_key="fact_text"
            ))

            profile_summary = self.profile_service.profile_summary_text()
            profile_summary = self._trim_text(profile_summary, budgets["profile_summary"])

            raw_memories = self.semantic_memory_service.retrieve_relevant_memories(query, top_k=8)
            reranked_memories = self._rerank_memories(raw_memories, query_type)
            memory_budget = self._budget_items_with_trace(reranked_memories, budgets["semantic_memories"])
            retrieved_memories = memory_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="semantic_memories",
                budget_chars=budgets["semantic_memories"],
                candidates_before=reranked_memories,
                kept_items=memory_budget["kept"],
                dropped_items=memory_budget["dropped"],
                content_key="content"
            ))

            raw_contexts = self.rag_service.retrieve_context(query, top_k=8)
            reranked_contexts = self._rerank_contexts(raw_contexts, query_type)
            context_budget = self._budget_items_with_trace(reranked_contexts, budgets["documents"])
            retrieved_contexts = context_budget["kept"]
            retrieved_contexts = self.prompt_security_service.sanitize_untrusted_items(
                retrieved_contexts,
                content_key="content",
                source_type="document"
            )
            retrieved_contexts = self.trust_service.annotate_items(
                retrieved_contexts,
                source_type="document",
                content_key="content"
            )

            retrieval_trace.append(self._build_source_trace(
                source_name="documents",
                budget_chars=budgets["documents"],
                candidates_before=reranked_contexts,
                kept_items=context_budget["kept"],
                dropped_items=context_budget["dropped"],
                content_key="content"
            ))

            retrieval_plan["used_facts"] = True
            retrieval_plan["used_profile"] = True
            retrieval_plan["used_semantic_memories"] = True
            retrieval_plan["used_documents"] = True

        else:
            raw_facts = self.memory_service.get_prompt_safe_facts(limit=12)
            raw_facts = self._filter_facts_by_mode(raw_facts, retrieval_mode)
            reranked_facts = self._rerank_facts(raw_facts, query_type)
            fact_budget = self._budget_facts_with_trace(reranked_facts, budgets["facts"])
            facts = fact_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="facts",
                budget_chars=budgets["facts"],
                candidates_before=reranked_facts,
                kept_items=fact_budget["kept"],
                dropped_items=fact_budget["dropped"],
                content_key="fact_text"
            ))

            profile_summary = self.profile_service.profile_summary_text()
            profile_summary = self._trim_text(profile_summary, budgets["profile_summary"])

            raw_memories = self.semantic_memory_service.retrieve_relevant_memories(query, top_k=6)
            reranked_memories = self._rerank_memories(raw_memories, query_type)
            memory_budget = self._budget_items_with_trace(reranked_memories, budgets["semantic_memories"])
            retrieved_memories = memory_budget["kept"]

            retrieval_trace.append(self._build_source_trace(
                source_name="semantic_memories",
                budget_chars=budgets["semantic_memories"],
                candidates_before=reranked_memories,
                kept_items=memory_budget["kept"],
                dropped_items=memory_budget["dropped"],
                content_key="content"
            ))

            retrieval_plan["used_facts"] = True
            retrieval_plan["used_profile"] = True
            retrieval_plan["used_semantic_memories"] = True

        usage = {
            "recent_messages_chars": sum(len(m.get("content", "")) for m in recent_messages),
            "profile_summary_chars": len(profile_summary),
            "facts_chars": sum(len(f.get("fact_text", "")) for f in facts),
            "semantic_memories_chars": sum(len(i.get("content", "")) for i in retrieved_memories),
            "documents_chars": sum(len(i.get("content", "")) for i in retrieved_contexts),
        }

        return {
            "query_type": query_type,
            "recent_messages": recent_messages,
            "facts": facts,
            "profile_summary": profile_summary,
            "retrieved_memories": retrieved_memories,
            "retrieved_contexts": retrieved_contexts,
            "retrieval_plan": retrieval_plan,
            "retrieval_trace": retrieval_trace,
            "context_counts": {
                "recent_messages": len(recent_messages),
                "facts": len(facts),
                "retrieved_memories": len(retrieved_memories),
                "retrieved_contexts": len(retrieved_contexts),
                "projects": len(continuity_context["projects"]),
                "goals": len(continuity_context["goals"]),
                "open_loops": len(continuity_context["open_loops"]),
                "recent_reflections": len(reflection_context["recent_reflections"]),
                "recent_daily_learnings": len(reflection_context["recent_daily_learnings"]),
                "temporal_summaries": len(temporal_context["summaries"]),
                "reasoning_states": len(reasoning_context["states"])
            },
            "budget_profile": budgets,
            "context_usage": usage,
            "retrieval_mode": retrieval_mode,
            "mode_effects": {
                "privacy_filtered": retrieval_mode == "privacy_safe",
                "budget_adjusted": retrieval_mode != "balanced"
            },
            "continuity": continuity_context,
            "reflections": reflection_context,
            "temporal": temporal_context,
            "proactive": proactive_context,
            "reasoning": reasoning_context,
            "is_temporal_query": is_temporal_query,
            "is_proactive_query": is_proactive_query,
            "active_project_id": active_project_id
        }

    def _build_source_trace(
        self,
        source_name: str,
        budget_chars: int,
        candidates_before: List[Dict],
        kept_items: List[Dict],
        dropped_items: List[Dict],
        content_key: str
    ) -> Dict:
        return {
            "source": source_name,
            "budget_chars": budget_chars,
            "candidates_before_count": len(candidates_before),
            "kept_count": len(kept_items),
            "dropped_count": len(dropped_items),
            "used_chars": sum(len(item.get(content_key, "") or "") for item in kept_items),
            "dropped_preview": [
                {
                    "preview": (item.get(content_key, "") or "")[:120],
                    "_retrieval_score": item.get("_retrieval_score"),
                    "_retrieval_reasons": item.get("_retrieval_reasons", [])
                }
                for item in dropped_items[:5]
            ]
        }

    def _get_budget_profile(self, query_type: str) -> Dict[str, int]:
        profiles = {
            "personal_memory": {
                "recent_messages": 2500,
                "profile_summary": 900,
                "facts": 1200,
                "semantic_memories": 1200,
                "documents": 400
            },
            "document_qa": {
                "recent_messages": 1800,
                "profile_summary": 300,
                "facts": 400,
                "semantic_memories": 500,
                "documents": 2200
            },
            "project_continuity": {
                "recent_messages": 2600,
                "profile_summary": 700,
                "facts": 900,
                "semantic_memories": 1400,
                "documents": 500
            },
            "knowledge_plus_memory": {
                "recent_messages": 2200,
                "profile_summary": 700,
                "facts": 900,
                "semantic_memories": 1000,
                "documents": 1600
            },
            "general_chat": {
                "recent_messages": 2000,
                "profile_summary": 500,
                "facts": 700,
                "semantic_memories": 700,
                "documents": 300
            }
        }
        return profiles.get(query_type, profiles["general_chat"])

    def _trim_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3].rstrip() + "..."

    def _budget_messages_with_trace(self, messages: List[Dict], max_chars: int) -> Dict:
        total = 0
        kept = []
        dropped = []

        ordered = list(reversed(messages))
        for idx, msg in enumerate(ordered):
            content = msg.get("content", "") or ""
            msg_len = len(content)

            if total + msg_len > max_chars and kept:
                dropped.extend(ordered[idx:])
                break

            kept.append(msg)
            total += msg_len

        kept = list(reversed(kept))
        dropped = list(reversed(dropped))

        return {
            "kept": kept,
            "dropped": dropped,
            "used_chars": sum(len(m.get("content", "") or "") for m in kept)
        }

    def _budget_facts_with_trace(self, facts: List[Dict], max_chars: int) -> Dict:
        total = 0
        kept = []
        dropped = []

        for idx, fact in enumerate(facts):
            text = fact.get("fact_text", "") or ""
            text_len = len(text)

            if total + text_len > max_chars and kept:
                dropped.extend(facts[idx:])
                break

            kept.append(fact)
            total += text_len

        return {
            "kept": kept,
            "dropped": dropped,
            "used_chars": sum(len(f.get("fact_text", "") or "") for f in kept)
        }

    def _budget_items_with_trace(self, items: List[Dict], max_chars: int) -> Dict:
        total = 0
        kept = []
        dropped = []

        for idx, item in enumerate(items):
            content = item.get("content", "") or ""
            item_len = len(content)

            if total + item_len > max_chars and kept:
                dropped.extend(items[idx:])
                break

            kept.append(item)
            total += item_len

        return {
            "kept": kept,
            "dropped": dropped,
            "used_chars": sum(len(i.get("content", "") or "") for i in kept)
        }

    def _rerank_facts(self, facts: List[Dict], query_type: str) -> List[Dict]:
        def parse_time(value: Optional[str]) -> datetime:
            if not value:
                return datetime.min
            try:
                return datetime.fromisoformat(value.replace("Z", ""))
            except Exception:
                return datetime.min

        def query_bonus(category: str) -> float:
            if query_type == "personal_memory":
                return 0.15 if category in {"identity", "location", "work"} else 0.05
            if query_type == "project_continuity":
                return 0.15 if category in {"work", "education", "identity"} else 0.05
            if query_type == "knowledge_plus_memory":
                return 0.10 if category in {"work", "identity", "education"} else 0.03
            return 0.05

        ranked = []
        for fact in facts:
            reasons = []

            confidence = float(fact.get("confidence", 0.0))
            reasons.append(f"base confidence={confidence:.2f}")

            pinned_bonus = 0.5 if fact.get("is_pinned") else 0.0
            if pinned_bonus:
                reasons.append("pinned bonus=0.50")

            category = fact.get("category", "general")
            category_bonus = query_bonus(category)
            reasons.append(f"query relevance bonus({category}, {query_type})={category_bonus:.2f}")

            last_confirmed = parse_time(fact.get("last_confirmed_at"))
            recency_bonus = 0.1 if last_confirmed > datetime.min else 0.0
            if recency_bonus:
                reasons.append("recency bonus=0.10")

            score = confidence + pinned_bonus + category_bonus + recency_bonus

            enriched = dict(fact)
            enriched["_retrieval_score"] = round(score, 4)
            enriched["_retrieval_reasons"] = reasons
            ranked.append(enriched)

        ranked.sort(key=lambda x: x["_retrieval_score"], reverse=True)
        return ranked

    def _rerank_memories(self, memories: List[Dict], query_type: str) -> List[Dict]:
        ranked = []

        for item in memories:
            reasons = []

            base_score = self._extract_vector_score(item)
            reasons.append(f"vector/base score={base_score:.2f}")

            bonus = 0.0
            if query_type in {"personal_memory", "project_continuity"}:
                bonus += 0.1
                reasons.append(f"query type bonus({query_type})=0.10")

            content = item.get("content", "") or ""
            lowered = content.lower()
            if any(term in lowered for term in ["project", "goal", "important", "remember", "problem", "plan"]):
                bonus += 0.05
                reasons.append("keyword bonus(project/goal/important/remember/problem/plan)=0.05")

            score = base_score + bonus

            enriched = dict(item)
            enriched["_retrieval_score"] = round(score, 4)
            enriched["_retrieval_reasons"] = reasons
            ranked.append(enriched)

        ranked.sort(key=lambda x: x["_retrieval_score"], reverse=True)
        return ranked

    def _rerank_contexts(self, contexts: List[Dict], query_type: str) -> List[Dict]:
        ranked = []

        for item in contexts:
            reasons = []

            base_score = self._extract_vector_score(item)
            reasons.append(f"vector/base score={base_score:.2f}")

            bonus = 0.0
            if query_type == "document_qa":
                bonus += 0.15
                reasons.append("document_qa bonus=0.15")
            elif query_type == "knowledge_plus_memory":
                bonus += 0.1
                reasons.append("knowledge_plus_memory bonus=0.10")

            content = item.get("content", "") or ""
            if 80 <= len(content) <= 1200:
                bonus += 0.03
                reasons.append("length sanity bonus=0.03")

            score = base_score + bonus

            enriched = dict(item)
            enriched["_retrieval_score"] = round(score, 4)
            enriched["_retrieval_reasons"] = reasons
            ranked.append(enriched)

        ranked.sort(key=lambda x: x["_retrieval_score"], reverse=True)
        return ranked

    def _extract_vector_score(self, item: Dict) -> float:
        for key in ("score", "similarity", "distance"):
            if key in item:
                try:
                    value = float(item[key])
                    if key == "distance":
                        return max(0.0, 1.0 - value)
                    return value
                except Exception:
                    continue
        return 0.5

    def _apply_mode_to_budget_profile(self, budget: Dict[str, int], retrieval_mode: str) -> Dict[str, int]:
        adjusted = dict(budget)

        if retrieval_mode == "deep_memory":
            adjusted["profile_summary"] = int(adjusted["profile_summary"] * 1.5)
            adjusted["facts"] = int(adjusted["facts"] * 1.5)
            adjusted["semantic_memories"] = int(adjusted["semantic_memories"] * 1.4)

        elif retrieval_mode == "focused":
            adjusted["profile_summary"] = int(adjusted["profile_summary"] * 0.6)
            adjusted["facts"] = int(adjusted["facts"] * 0.6)
            adjusted["semantic_memories"] = int(adjusted["semantic_memories"] * 0.6)
            adjusted["documents"] = int(adjusted["documents"] * 0.8)

        elif retrieval_mode == "document_first":
            adjusted["documents"] = int(adjusted["documents"] * 1.5)
            adjusted["facts"] = int(adjusted["facts"] * 0.5)
            adjusted["profile_summary"] = int(adjusted["profile_summary"] * 0.5)
            adjusted["semantic_memories"] = int(adjusted["semantic_memories"] * 0.7)

        elif retrieval_mode == "privacy_safe":
            adjusted["profile_summary"] = int(adjusted["profile_summary"] * 0.5)
            adjusted["facts"] = int(adjusted["facts"] * 0.4)
            adjusted["semantic_memories"] = int(adjusted["semantic_memories"] * 0.7)

        return adjusted

    def _filter_facts_by_mode(self, facts: List[Dict], retrieval_mode: str) -> List[Dict]:
        if retrieval_mode == "privacy_safe":
            return [f for f in facts if f.get("visibility") == "general"]
        return facts
