
"""
Authentication middleware for protecting API endpoints
and ensuring multi-tenant data isolation
"""

import os
import jwt
import logging
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Secret key for JWT validation (should match NextAuth secret)
JWT_SECRET = os.getenv('NEXTAUTH_SECRET', 'y77l5Ozmqb0woc5Hm1IxKaiR8zjdVRNK')

def decode_token(token):
    """Decode and validate JWT token"""
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode the token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None

def get_user_from_request():
    """Extract user information from request headers"""
    # Try to get token from Authorization header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None
    
    payload = decode_token(auth_header)
    
    if not payload:
        return None
    
    # Extract user info from payload
    user_id = payload.get('sub') or payload.get('userId') or payload.get('id')
    user_email = payload.get('email')
    
    return {
        'id': user_id,
        'email': user_email,
        'name': payload.get('name'),
    }

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_from_request()
        
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Add user to request context
        request.user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """Decorator to optionally extract user info but not require it"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_from_request()
        request.user = user
        return f(*args, **kwargs)
    
    return decorated_function
