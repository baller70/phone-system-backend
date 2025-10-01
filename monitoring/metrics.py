
"""
Metrics Collection Service
Tracks system performance and call metrics using Prometheus
"""
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# Call Metrics
calls_total = Counter('calls_total', 'Total number of calls received', ['status'])
call_duration = Histogram('call_duration_seconds', 'Call duration in seconds')
active_calls = Gauge('active_calls', 'Number of currently active calls')

# Booking Metrics
bookings_total = Counter('bookings_total', 'Total number of bookings', ['status'])
booking_value = Histogram('booking_value_dollars', 'Booking value in dollars')

# AI Performance Metrics
ai_responses_total = Counter('ai_responses_total', 'Total AI responses', ['intent'])
ai_confidence = Histogram('ai_confidence_score', 'AI confidence scores')
sentiment_total = Counter('sentiment_total', 'Customer sentiment', ['sentiment'])

# System Health Metrics
api_errors_total = Counter('api_errors_total', 'Total API errors', ['service'])
escalations_total = Counter('escalations_total', 'Total escalations', ['reason'])

class MetricsService:
    def __init__(self):
        logger.info("Metrics Service initialized")
    
    def record_call_start(self):
        """Record a new call starting"""
        calls_total.labels(status='started').inc()
        active_calls.inc()
    
    def record_call_end(self, duration_seconds, status='completed'):
        """Record a call ending"""
        calls_total.labels(status=status).inc()
        call_duration.observe(duration_seconds)
        active_calls.dec()
    
    def record_booking(self, status='success', value=0):
        """Record a booking attempt"""
        bookings_total.labels(status=status).inc()
        if value > 0:
            booking_value.observe(value)
    
    def record_ai_response(self, intent, confidence):
        """Record AI response"""
        ai_responses_total.labels(intent=intent).inc()
        ai_confidence.observe(confidence)
    
    def record_sentiment(self, sentiment):
        """Record customer sentiment"""
        sentiment_total.labels(sentiment=sentiment).inc()
    
    def record_api_error(self, service):
        """Record API error"""
        api_errors_total.labels(service=service).inc()
    
    def record_escalation(self, reason):
        """Record escalation"""
        escalations_total.labels(reason=reason).inc()
    
    def get_metrics(self):
        """Get current metrics in Prometheus format"""
        return generate_latest()
    
    def get_content_type(self):
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST

# Global metrics service instance
metrics_service = MetricsService()
