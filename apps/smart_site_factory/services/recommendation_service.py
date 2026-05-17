from apps.smart_site_factory.models import Template, TemplateRecommendationRule


class RecommendationService:
    @staticmethod
    def recommend_template(*, niche, option_ids=None):
        option_ids = option_ids or []
        rules = (
            TemplateRecommendationRule.objects.filter(
                niche=niche,
                is_active=True,
                recommended_template__is_active=True,
            )
            .select_related("recommended_template")
            .order_by("priority", "-created_at")
        )

        for rule in rules:
            if rule.option_id is None or rule.option_id in option_ids:
                return rule.recommended_template

        return (
            Template.objects.filter(niche=niche, is_active=True, status=Template.Status.READY)
            .order_by("base_price", "name")
            .first()
        )
