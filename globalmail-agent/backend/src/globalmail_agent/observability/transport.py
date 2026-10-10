"""One HTTP attempt per SDK export; never expose remote errors to OTLP logging."""
import requests
from urllib3.exceptions import NewConnectionError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse


def not_connected(error):
    if isinstance(error, requests.ConnectTimeout):
        return True
    seen, pending = set(), [error]
    while pending and len(seen) < 16:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, NewConnectionError):
            return True
        pending.extend(value for value in (getattr(item, "reason", None),
            getattr(item, "__cause__", None), getattr(item, "__context__", None),
            *getattr(item, "args", ())) if isinstance(value, BaseException))
    return False


class AcknowledgedSession(requests.Session):
    """Session is the official OTLP exporter configuration point.

    A synthetic safe non-retryable response prevents both its connection retry
    and status retry. No original exception/context or response body enters OTLP.
    """
    acknowledged, retryable, ack_unknown = False, False, False

    def reset(self):
        self.acknowledged, self.retryable, self.ack_unknown = False, False, False

    @staticmethod
    def receipt(status, reason):
        response = requests.Response()
        response.status_code, response.reason, response._content = status, reason, b""
        return response

    def request(self, *args, **kwargs):
        self.reset()
        kwargs["allow_redirects"] = False
        try:
            response = super().request(*args, **kwargs)
        except Exception as error:
            self.retryable = not_connected(error)
            self.ack_unknown = not self.retryable
            return self.receipt(400, "observability_transport_failed")
        if response.status_code != 200:
            self.retryable = response.status_code == 429
            self.ack_unknown = response.status_code >= 500
            response.close()
            return self.receipt(400, "observability_http_rejected")
        try:
            if "application/json" in response.headers.get("content-type", ""):
                result = response.json()
                partial = result.get("partialSuccess", result.get("partial_success", {}))
                rejected = partial.get("rejectedSpans", partial.get("rejected_spans", 0))
                self.acknowledged = (isinstance(result, dict) and not result.get("error")
                    and not result.get("failedReason") and not result.get("stacktrace") and int(rejected) == 0)
            else:
                result = ExportTraceServiceResponse.FromString(response.content)
                self.acknowledged = result.partial_success.rejected_spans == 0
        except Exception:
            pass
        self.ack_unknown = not self.acknowledged
        response.close()
        return self.receipt(200, "observability_acknowledged" if self.acknowledged else "observability_ack_unknown")
