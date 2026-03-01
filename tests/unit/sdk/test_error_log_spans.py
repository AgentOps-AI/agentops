"""Tests for error and log span kinds — decorators and standalone functions."""

from agentops.sdk.decorators import error as error_decorator, log as log_decorator
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


class TestErrorDecorator:
    """Tests for the @error decorator."""

    def test_error_decorator_creates_span(self, instrumentation: InstrumentationTester):
        @error_decorator
        def failing_operation():
            return "error occurred"

        result = failing_operation()
        assert result == "error occurred"

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == SpanKind.ERROR

    def test_error_decorator_with_name(self, instrumentation: InstrumentationTester):
        @error_decorator(name="custom_error")
        def failing_operation():
            return "fail"

        failing_operation()

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.OPERATION_NAME] == "custom_error"

    def test_error_decorator_async(self, instrumentation: InstrumentationTester):
        @error_decorator
        async def async_failing():
            return "async error"

        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(async_failing())
        finally:
            loop.close()
        assert result == "async error"

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == SpanKind.ERROR


class TestLogDecorator:
    """Tests for the @log decorator."""

    def test_log_decorator_creates_span(self, instrumentation: InstrumentationTester):
        @log_decorator
        def log_operation():
            return "logged"

        result = log_operation()
        assert result == "logged"

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == SpanKind.LOG

    def test_log_decorator_with_name(self, instrumentation: InstrumentationTester):
        @log_decorator(name="custom_log")
        def log_operation():
            return "log"

        log_operation()

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.OPERATION_NAME] == "custom_log"


class TestStandaloneError:
    """Tests for the standalone agentops.error() function."""

    def test_error_creates_span(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.error(name="test_error", message="something went wrong")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == SpanKind.ERROR
        assert span.attributes["error.message"] == "something went wrong"

    def test_error_sets_error_status(self, instrumentation: InstrumentationTester):
        import agentops
        from opentelemetry.trace import StatusCode

        agentops.error(name="status_error", message="bad request")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].status.status_code == StatusCode.ERROR

    def test_error_with_extra_attributes(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.error(name="attr_error", message="fail", code="E001")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["code"] == "E001"

    def test_error_default_name(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.error(message="default name test")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.OPERATION_NAME] == "error"


class TestStandaloneLog:
    """Tests for the standalone agentops.log() function."""

    def test_log_creates_span(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.log(name="test_log", message="hello world")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1

        span = spans[0]
        assert span.attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == SpanKind.LOG
        assert span.attributes["log.message"] == "hello world"

    def test_log_with_level(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.log(name="level_log", message="debug info", level="DEBUG")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["log.level"] == "DEBUG"

    def test_log_default_level_is_info(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.log(name="info_log", message="info message")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["log.level"] == "INFO"

    def test_log_with_extra_attributes(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.log(name="extra_log", message="data", source="test")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["source"] == "test"

    def test_log_default_name(self, instrumentation: InstrumentationTester):
        import agentops

        agentops.log(message="default")

        spans = instrumentation.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[SpanAttributes.OPERATION_NAME] == "log"
