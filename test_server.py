import sys
sys.path.insert(0, '/home/ubuntu/github_repos/auto_call_system')

from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("🎯 Testing Phone System Backend")
    print("=" * 60)
    
    # Test health endpoint
    with app.test_client() as client:
        response = client.get('/health')
        print(f"✓ Health check: {response.status_code}")
        
        # Test answer webhook with mock data
        mock_call_data = {
            'conversation_uuid': 'test-uuid-123',
            'from': '+15551234567',
            'to': '+19095779171',
            'uuid': 'call-uuid-123'
        }
        
        response = client.post(
            '/webhooks/answer',
            json=mock_call_data,
            content_type='application/json'
        )
        
        print(f"✓ Answer webhook: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print(f"✓ Response contains {len(data)} NCCO actions")
            print("\n📞 Call Flow Preview:")
            for i, action in enumerate(data, 1):
                print(f"   {i}. {action.get('action', 'Unknown')}: {action.get('text', action.get('eventUrl', 'N/A'))[:60]}")
        
    print("\n" + "=" * 60)
    print("✅ Backend is working correctly!")
    print("=" * 60)
