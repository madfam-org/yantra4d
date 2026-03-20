"""
OpenTelemetry Tracing Module
Initializes TracerProvider with OTLP exporter when OTEL_EXPORTER_OTLP_ENDPOINT
is set. Provides a @traced decorator for adding manual spans to functions.

All exports are safe to use even when OpenTelemetry is not installed or not
configured — they degrade to no-ops.
"""
import functools
import logging
import os

logger = logging.getLogger(__name__)

_tracer = None


def init_tracing(app):
    """Initialize OpenTelemetry tracing for the Flask app.

    Requires:
      - OTEL_EXPORTER_OTLP_ENDPOINT env var to be set
      - opentelemetry packages installed

    When either condition is missing the function is a silent no-op.
    """
    global _tracer

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set; tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
    except ImportError:
        logger.info("opentelemetry packages not installed; tracing disabled")
        return

    resource = Resource.create({"service.name": "yantra4d-api"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _tracer = trace.get_tracer("yantra4d")

    FlaskInstrumentor().instrument_app(app)
    logger.info("OpenTelemetry tracing initialized (endpoint=%s)", endpoint)


def traced(name: str | None = None):
    """Decorator that wraps a function in an OpenTelemetry span.

    Usage::

        @traced("render.openscad")
        def run_render(...):
            ...

    When tracing is not active the decorator is transparent.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _tracer is None:
                return fn(*args, **kwargs)
            span_name = name or f"{fn.__module__}.{fn.__qualname__}"
            with _tracer.start_as_current_span(span_name):
                return fn(*args, **kwargs)
        return wrapper
    return decorator
