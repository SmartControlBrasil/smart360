from rest_framework import serializers

from apps.ai_knowledge_graph.models import GraphEdge, GraphNode, GraphProjectionRun


class GraphNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraphNode
        fields = (
            "public_id",
            "company",
            "site",
            "node_type",
            "source_type",
            "source_id",
            "label",
            "attributes",
            "strength",
            "created_at",
            "updated_at",
        )


class GraphEdgeSerializer(serializers.ModelSerializer):
    from_node = GraphNodeSerializer(read_only=True)
    to_node = GraphNodeSerializer(read_only=True)

    class Meta:
        model = GraphEdge
        fields = (
            "public_id",
            "company",
            "site",
            "edge_type",
            "from_node",
            "to_node",
            "weight",
            "attributes",
            "created_at",
            "updated_at",
        )


class GraphProjectionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraphProjectionRun
        fields = (
            "public_id",
            "projection_type",
            "company",
            "site",
            "status",
            "summary",
            "metadata",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )

