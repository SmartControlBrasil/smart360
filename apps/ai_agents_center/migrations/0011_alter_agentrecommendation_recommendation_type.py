from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai_agents_center", "0010_ai_briefings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agentrecommendation",
            name="recommendation_type",
            field=models.CharField(
                choices=[
                    ("insight", "Insight"),
                    ("preventive", "Preventive"),
                    ("rebalancing", "Rebalancing"),
                    ("profitability", "Profitability"),
                    ("marketplace", "Marketplace"),
                    ("anomaly", "Anomaly"),
                    ("preventive_review", "Preventive Review"),
                    ("extraordinary_inspection", "Extraordinary Inspection"),
                    ("failure_pattern_alert", "Failure Pattern Alert"),
                    ("reliability_attention", "Reliability Attention"),
                    ("action_plan_recommendation", "Action Plan Recommendation"),
                    ("critical_asset_watch", "Critical Asset Watch"),
                    ("technician_overload", "Technician Overload"),
                    ("route_reorder", "Route Reorder"),
                    ("visit_reassignment", "Visit Reassignment"),
                    ("sla_risk_alert", "SLA Risk Alert"),
                    ("unassigned_visit_attention", "Unassigned Visit Attention"),
                    ("idle_capacity_opportunity", "Idle Capacity Opportunity"),
                    ("route_efficiency_attention", "Route Efficiency Attention"),
                    ("client_margin_alert", "Client Margin Alert"),
                    ("contract_profitability_risk", "Contract Profitability Risk"),
                    ("excessive_service_cost", "Excessive Service Cost"),
                    ("route_margin_erosion", "Route Margin Erosion"),
                    ("technician_efficiency_attention", "Technician Efficiency Attention"),
                    ("repricing_recommendation", "Repricing Recommendation"),
                    ("scope_review_recommendation", "Scope Review Recommendation"),
                    ("profitability_watch", "Profitability Watch"),
                    ("technician_allocation_recommendation", "Technician Allocation Recommendation"),
                    ("no_viable_candidate_alert", "No Viable Candidate Alert"),
                    ("sla_allocation_risk", "SLA Allocation Risk"),
                    ("fallback_assignment_recommendation", "Fallback Assignment Recommendation"),
                    ("technician_unavailable_conflict", "Technician Unavailable Conflict"),
                    ("marketplace_request_attention", "Marketplace Request Attention"),
                    ("anomaly_failure_spike", "Anomaly Failure Spike"),
                    ("anomaly_backlog_growth", "Anomaly Backlog Growth"),
                    ("anomaly_sla_drop", "Anomaly SLA Drop"),
                    ("anomaly_parts_consumption", "Anomaly Parts Consumption"),
                    ("anomaly_technician_behavior", "Anomaly Technician Behavior"),
                    ("anomaly_marketplace_signal", "Anomaly Marketplace Signal"),
                    ("anomaly_contract_margin_shift", "Anomaly Contract Margin Shift"),
                    ("anomaly_site_risk_alert", "Anomaly Site Risk Alert"),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
