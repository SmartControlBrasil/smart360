from django.test import TestCase

from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditService


class AuditServiceTests(TestCase):
    def test_log_creates_audit_entry(self):
        entry = AuditService.log(action="company.created", entity="company", entity_id="123", payload={"name": "Acme"})
        self.assertIsInstance(entry, AuditLog)
        self.assertEqual(AuditLog.objects.count(), 1)
