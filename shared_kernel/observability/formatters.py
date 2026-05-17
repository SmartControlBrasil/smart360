import json
import logging


class StructuredConsoleFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
            "request_path": getattr(record, "request_path", "-"),
            "source_module": getattr(record, "source_module", "-"),
            "entity_type": getattr(record, "entity_type", "-"),
            "entity_id": getattr(record, "entity_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class HumanConsoleFormatter(logging.Formatter):
    pass

