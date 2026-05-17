from django.db import transaction

from apps.audit.services.audit_service import AuditService

from ..models import Lead, LeadAssignment, LeadQualification


class LeadScoringService:
    @staticmethod
    def calculate_score(*, lead, qualification_criteria=None):
        score = 0
        if lead.email:
            score += 20
        if lead.phone:
            score += 10
        if lead.whatsapp:
            score += 15
        if lead.website:
            score += 10
        if lead.city:
            score += 5
        if lead.state:
            score += 5
        if lead.niche_id:
            score += 15
        if lead.source_id:
            score += 10
        if qualification_criteria:
            score += min(len([k for k, v in qualification_criteria.items() if v]), 5) * 2
        return min(score, 100)


class LeadService:
    @staticmethod
    @transaction.atomic
    def create_lead(*, user, validated_data):
        tag_ids = validated_data.pop("tag_ids", [])
        lead = Lead.objects.create(created_by=user, **validated_data)
        if tag_ids:
            lead.tags.set(tag_ids)
        lead.score = LeadScoringService.calculate_score(lead=lead)
        lead.save(update_fields=["score", "updated_at"])

        if lead.assigned_to_id:
            LeadAssignment.objects.create(lead=lead, user=lead.assigned_to)

        LeadQualification.objects.get_or_create(
            lead=lead,
            defaults={"criteria": {}, "calculated_score": lead.score},
        )

        AuditService.log(
            action="growth.lead.created",
            entity="lead",
            entity_id=str(lead.public_id),
            user=user,
            payload={"company_name": lead.company_name, "status": lead.status, "score": lead.score},
        )
        return lead

    @staticmethod
    @transaction.atomic
    def update_lead(*, lead, validated_data, user):
        tag_ids = validated_data.pop("tag_ids", None)
        previous_assignee_id = lead.assigned_to_id
        for field, value in validated_data.items():
            setattr(lead, field, value)
        lead.score = LeadScoringService.calculate_score(lead=lead)
        lead.save()

        if tag_ids is not None:
            lead.tags.set(tag_ids)

        qualification = LeadQualification.objects.filter(lead=lead).first()
        LeadQualification.objects.update_or_create(
            lead=lead,
            defaults={"criteria": qualification.criteria if qualification else {}, "calculated_score": lead.score},
        )

        if lead.assigned_to_id and lead.assigned_to_id != previous_assignee_id:
            if previous_assignee_id:
                LeadAssignment.objects.filter(lead=lead, user_id=previous_assignee_id, status=LeadAssignment.AssignmentStatus.ACTIVE).update(
                    status=LeadAssignment.AssignmentStatus.REASSIGNED
                )
            LeadAssignment.objects.create(lead=lead, user=lead.assigned_to, status=LeadAssignment.AssignmentStatus.ACTIVE)

        AuditService.log(
            action="growth.lead.updated",
            entity="lead",
            entity_id=str(lead.public_id),
            user=user,
            payload={"status": lead.status, "score": lead.score},
        )
        return lead

    @staticmethod
    def assign_lead(*, lead, user):
        if lead.assigned_to_id and lead.assigned_to_id != user.id:
            LeadAssignment.objects.filter(
                lead=lead,
                user_id=lead.assigned_to_id,
                status=LeadAssignment.AssignmentStatus.ACTIVE,
            ).update(status=LeadAssignment.AssignmentStatus.REASSIGNED)
        lead.assigned_to = user
        lead.save(update_fields=["assigned_to", "updated_at"])
        LeadAssignment.objects.create(lead=lead, user=user, status=LeadAssignment.AssignmentStatus.ACTIVE)
        return lead
