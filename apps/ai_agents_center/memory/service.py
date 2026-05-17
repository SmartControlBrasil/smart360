from __future__ import annotations

from apps.ai_agents_center.models import AgentMemoryEntry


class AgentMemoryService:
    @staticmethod
    def remember(
        *,
        agent,
        company=None,
        site=None,
        entity_type="",
        entity_id="",
        memory_kind,
        content,
        metadata=None,
    ):
        return AgentMemoryEntry.objects.create(
            agent=agent,
            company=company,
            site=site,
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            memory_kind=memory_kind,
            content=content,
            metadata=metadata or {},
        )
