"""
Rebooking Caller Job - Phase 6
Background job to make outbound calls for rebooking campaigns
"""

import logging

logger = logging.getLogger(__name__)


class RebookingCallerJob:
    """Background job to make outbound rebooking calls"""
    
    def __init__(self, rebooking_service, vonage_client=None):
        self.rebooking_service = rebooking_service
        self.vonage = vonage_client
        self.enabled = bool(vonage_client)
    
    def run(self):
        """
        Make outbound calls for due rebooking campaigns
        
        Returns:
            dict: Stats about calls made
        """
        if not self.enabled:
            logger.info("Outbound calling disabled (no Vonage client)")
            return {'calls': 0, 'status': 'disabled'}
        
        try:
            # Get due campaigns
            campaigns = self.rebooking_service.get_due_campaigns()
            
            if not campaigns:
                logger.info("No rebooking campaigns due")
                return {'calls': 0}
            
            calls_made = 0
            
            for campaign in campaigns[:10]:  # Limit to 10 calls per run
                try:
                    # Make outbound call
                    call_result = self._make_outbound_call(campaign)
                    
                    if call_result.get('success'):
                        self.rebooking_service.mark_campaign_called(
                            campaign['id'],
                            success=True
                        )
                        calls_made += 1
                    else:
                        self.rebooking_service.mark_campaign_called(
                            campaign['id'],
                            success=False
                        )
                
                except Exception as e:
                    logger.error(f"Error making rebooking call for campaign {campaign['id']}: {str(e)}")
            
            logger.info(f"Rebooking caller job complete: {calls_made} calls made")
            return {'calls': calls_made}
            
        except Exception as e:
            logger.error(f"Error in rebooking caller job: {str(e)}")
            return {'error': str(e)}
    
    def _make_outbound_call(self, campaign):
        """
        Make an outbound call using Vonage
        
        (Placeholder - requires Vonage outbound call configuration)
        """
        try:
            # In production, would use Vonage Voice API to make outbound call
            # For now, log the attempt
            logger.info(f"Outbound call attempt to {campaign['customer_phone']} for campaign {campaign['id']}")
            
            # Placeholder result
            return {
                'success': True,
                'message': 'Call initiated (placeholder)'
            }
            
        except Exception as e:
            logger.error(f"Error making outbound call: {str(e)}")
            return {'success': False, 'error': str(e)}


# Factory function
def create_rebooking_caller_job(rebooking_service, vonage_client=None):
    return RebookingCallerJob(rebooking_service, vonage_client)
