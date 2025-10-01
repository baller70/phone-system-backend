
"""
Health Check Service
Monitors system health and dependencies
"""
import logging
import os
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class HealthCheckService:
    def __init__(self):
        self.start_time = datetime.now()
        logger.info("Health Check Service initialized")
    
    def check_calcom_health(self):
        """Check if Cal.com API is accessible"""
        try:
            api_key = os.getenv('CALCOM_API_KEY')
            if not api_key:
                return {'status': 'unavailable', 'message': 'API key not configured'}
            
            response = requests.get(
                'https://api.cal.com/v1/availability',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=5
            )
            
            if response.status_code == 200:
                return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'status': 'degraded', 'status_code': response.status_code}
                
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_redis_health(self):
        """Check if Redis is accessible"""
        try:
            from intelligence.conversation_memory import conversation_memory
            
            if not conversation_memory.redis_available:
                return {'status': 'unavailable', 'message': 'Using in-memory fallback'}
            
            conversation_memory.redis_client.ping()
            return {'status': 'healthy'}
            
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_sms_health(self):
        """Check if SMS service is configured"""
        try:
            from integrations.sms_service import sms_service
            
            if not sms_service.enabled:
                return {'status': 'unavailable', 'message': 'SMS service not configured'}
            
            # Just check if credentials exist
            return {'status': 'healthy'}
            
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def get_system_health(self):
        """Get overall system health status"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime_seconds,
            'dependencies': {
                'calcom': self.check_calcom_health(),
                'redis': self.check_redis_health(),
                'sms': self.check_sms_health()
            }
        }
        
        # Determine overall status
        dep_statuses = [dep['status'] for dep in health_status['dependencies'].values()]
        
        if any(status == 'unhealthy' for status in dep_statuses):
            health_status['status'] = 'unhealthy'
        elif any(status == 'degraded' for status in dep_statuses):
            health_status['status'] = 'degraded'
        
        return health_status

# Global health check service instance
health_check_service = HealthCheckService()
