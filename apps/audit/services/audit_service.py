from apps.audit.models import AuditLog


class AuditService:
    @staticmethod
    def log(*, action: str, entity: str, entity_id: str, user=None, company=None, payload=None):
        return AuditLog.objects.create(
            action=action,
            entity=entity,
            entity_id=entity_id,
            user=user,
            company=company,
            payload=payload or {},
        )
