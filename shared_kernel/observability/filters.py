import logging

from shared_kernel.observability.context import get_correlation_id, get_request_path


class ObservabilityContextFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_correlation_id() or "-"
        record.request_path = get_request_path() or "-"
        record.source_module = getattr(record, "source_module", "-")
        record.entity_type = getattr(record, "entity_type", "-")
        record.entity_id = getattr(record, "entity_id", "-")
        return True

