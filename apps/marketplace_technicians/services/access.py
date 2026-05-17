from django.db.models import Q

from apps.companies.models import Membership

from ..models import (
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
)


class MarketplaceAccessService:
    @staticmethod
    def get_company_ids(user):
        if getattr(user, "is_superuser", False):
            return None
        return list(
            Membership.objects.filter(
                user=user,
                status=Membership.Status.ACTIVE,
            ).values_list("company_id", flat=True)
        )

    @staticmethod
    def is_company_operator(user):
        company_ids = MarketplaceAccessService.get_company_ids(user)
        return company_ids is None or bool(company_ids)

    @staticmethod
    def is_technician(user):
        return hasattr(user, "technician_profile")

    @staticmethod
    def can_manage_request(user, service_request):
        if getattr(user, "is_superuser", False):
            return True
        if service_request.requester_company_id is None:
            return False
        return service_request.requester_company_id in (MarketplaceAccessService.get_company_ids(user) or [])

    @staticmethod
    def can_offer(user, service_request, technician_profile=None):
        if getattr(user, "is_superuser", False):
            return True
        profile = technician_profile or getattr(user, "technician_profile", None)
        if profile is None:
            return False
        if service_request.status not in {
            TechnicianServiceRequest.Status.OPEN,
            TechnicianServiceRequest.Status.MATCHING,
            TechnicianServiceRequest.Status.OFFERS_RECEIVED,
        }:
            return False
        return profile.user_id == user.id

    @staticmethod
    def can_manage_assignment(user, assignment):
        if getattr(user, "is_superuser", False):
            return True
        if getattr(user, "technician_profile", None) and assignment.technician_profile_id == user.technician_profile.id:
            return True
        return MarketplaceAccessService.can_manage_request(user, assignment.technician_service_request)

    @staticmethod
    def can_review_assignment(user, assignment):
        if getattr(user, "is_superuser", False):
            return True
        return MarketplaceAccessService.can_manage_request(user, assignment.technician_service_request)

    @staticmethod
    def scope_requests_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        company_ids = MarketplaceAccessService.get_company_ids(user) or []
        technician_profile = getattr(user, "technician_profile", None)
        company_q = Q(requester_company_id__in=company_ids) if company_ids else Q(pk__in=[])
        if technician_profile:
            return queryset.filter(
                company_q
                | Q(offers__technician_profile=technician_profile)
                | Q(assignments__technician_profile=technician_profile)
                | Q(
                    status__in=[
                        TechnicianServiceRequest.Status.OPEN,
                        TechnicianServiceRequest.Status.MATCHING,
                        TechnicianServiceRequest.Status.OFFERS_RECEIVED,
                    ]
                )
            ).distinct()
        return queryset.filter(company_q).distinct()

    @staticmethod
    def scope_offers_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        company_ids = MarketplaceAccessService.get_company_ids(user) or []
        technician_profile = getattr(user, "technician_profile", None)
        if technician_profile:
            return queryset.filter(
                Q(technician_profile=technician_profile)
                | Q(service_request__requester_company_id__in=company_ids)
            ).distinct()
        return queryset.filter(service_request__requester_company_id__in=company_ids).distinct()

    @staticmethod
    def scope_assignments_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        company_ids = MarketplaceAccessService.get_company_ids(user) or []
        technician_profile = getattr(user, "technician_profile", None)
        if technician_profile:
            return queryset.filter(
                Q(technician_profile=technician_profile)
                | Q(technician_service_request__requester_company_id__in=company_ids)
            ).distinct()
        return queryset.filter(technician_service_request__requester_company_id__in=company_ids).distinct()

    @staticmethod
    def scope_matching_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        company_ids = MarketplaceAccessService.get_company_ids(user) or []
        technician_profile = getattr(user, "technician_profile", None)
        if technician_profile:
            return queryset.filter(
                Q(technician_profile=technician_profile)
                | Q(technician_service_request__requester_company_id__in=company_ids)
            ).distinct()
        return queryset.filter(technician_service_request__requester_company_id__in=company_ids).distinct()

    @staticmethod
    def scope_reviews_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        company_ids = MarketplaceAccessService.get_company_ids(user) or []
        technician_profile = getattr(user, "technician_profile", None)
        if technician_profile:
            return queryset.filter(
                Q(technician_profile=technician_profile)
                | Q(reviewer_company_id__in=company_ids)
            ).distinct()
        return queryset.filter(reviewer_company_id__in=company_ids).distinct()

    @staticmethod
    def scope_profiles_queryset(user, queryset):
        if getattr(user, "is_superuser", False):
            return queryset
        technician_profile = getattr(user, "technician_profile", None)
        if technician_profile:
            return queryset.filter(
                Q(pk=technician_profile.pk)
                | Q(
                    marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
                    is_active=True,
                )
            ).distinct()
        return queryset
