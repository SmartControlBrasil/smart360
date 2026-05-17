from django.contrib import admin

from .models import GraphEdge, GraphNode, GraphProjectionRun


@admin.register(GraphNode)
class GraphNodeAdmin(admin.ModelAdmin):
    list_display = ("label", "node_type", "company", "site", "source_type", "source_id", "strength")
    list_filter = ("node_type", "company", "site")
    search_fields = ("label", "source_type", "source_id")
    autocomplete_fields = ("company", "site")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(GraphEdge)
class GraphEdgeAdmin(admin.ModelAdmin):
    list_display = ("edge_type", "from_node", "to_node", "company", "site", "weight")
    list_filter = ("edge_type", "company", "site")
    search_fields = ("from_node__label", "to_node__label")
    autocomplete_fields = ("company", "site", "from_node", "to_node")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(GraphProjectionRun)
class GraphProjectionRunAdmin(admin.ModelAdmin):
    list_display = ("public_id", "projection_type", "company", "site", "status", "started_at", "finished_at")
    list_filter = ("projection_type", "status", "company", "site")
    search_fields = ("summary",)
    autocomplete_fields = ("company", "site")
    readonly_fields = ("public_id", "created_at", "updated_at")

