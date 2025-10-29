"""
Force IVR cache refresh by invalidating timestamp
"""
import ivr_config

# Force cache invalidation
ivr_config._ivr_cache['timestamp'] = 0
print("✓ Cache invalidated - will refresh on next call")

# Trigger refresh
settings = ivr_config.fetch_ivr_settings()
if settings:
    print(f"✓ Cache refreshed with {len(settings.get('menuOptions', []))} options")
    print(f"  Use audio: {settings.get('useAudioGreeting', False)}")
    print(f"  Audio URL: {settings.get('greetingAudioUrl', 'N/A')}")
else:
    print("✗ Failed to refresh cache")
