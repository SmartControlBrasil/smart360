from rest_framework import serializers

from apps.ai_digital_twin.models import DigitalTwin, DigitalTwinProjection, DigitalTwinSignal, DigitalTwinSnapshot


class DigitalTwinSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwinSignal
        fields = (
            "public_id",
            "signal_type",
            "source_type",
            "source_reference",
            "severity",
            "title",
            "summary",
            "signal_payload",
            "occurred_at",
            "is_active",
            "cleared_at",
        )


class DigitalTwinProjectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwinProjection
        fields = (
            "public_id",
            "projection_type",
            "projection_status",
            "source_window_start",
            "source_window_end",
            "projection_payload",
            "created_at",
            "updated_at",
        )


class DigitalTwinSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalTwinSnapshot
        fields = (
            "public_id",
            "snapshot_time",
            "state_payload",
            "risk_payload",
            "summary",
            "created_at",
        )


class DigitalTwinSerializer(serializers.ModelSerializer):
    active_signals = DigitalTwinSignalSerializer(many=True, read_only=True, source="signals")
    projections = DigitalTwinProjectionSerializer(many=True, read_only=True)

    class Meta:
        model = DigitalTwin
        fields = (
            "public_id",
            "twin_type",
            "company",
            "site",
            "asset",
            "contract",
            "external_reference",
            "status",
            "risk_level",
            "current_state_summary",
            "state_payload",
            "risk_payload",
            "timeline_payload",
            "summary_payload",
            "metadata",
            "last_projected_at",
            "created_at",
            "updated_at",
            "active_signals",
            "projections",
        )

