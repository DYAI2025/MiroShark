"""
Unit tests for internal API authentication guard
"""
import os
import pytest
from app import create_app
from app.config import Config


def test_health_endpoint_without_auth():
    """Test that /health endpoint is accessible without authentication"""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert response.json['service'] == 'MiroShark Backend'


def test_protected_api_without_internal_key():
    """Test that protected API routes return 401 without internal key"""
    # Set internal key to enable auth guard
    os.environ['MIROSHARK_INTERNAL_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test a protected API route (graph ontology generate)
        response = client.post('/api/graph/ontology/generate')
        assert response.status_code == 401


def test_protected_api_with_correct_internal_key():
    """Test that protected API routes succeed with correct internal key"""
    # Set internal key to enable auth guard
    os.environ['MIROSHARK_INTERNAL_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test a protected API route with correct header
        response = client.post(
            '/api/graph/ontology/generate',
            headers={'x-miroshark-internal-key': 'test-secret-key'}
        )
        # Should return 400 (bad request) or 422 (validation error) rather than 401
        # because the request is missing required fields, but auth passed
        assert response.status_code != 401


def test_protected_api_with_wrong_internal_key():
    """Test that protected API routes return 401 with wrong internal key"""
    # Set internal key to enable auth guard
    os.environ['MIROSHARK_INTERNAL_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test a protected API route with wrong header
        response = client.post(
            '/api/graph/ontology/generate',
            headers={'x-miroshark-internal-key': 'wrong-key'}
        )
        assert response.status_code == 401


def test_protected_api_without_internal_key_env():
    """Test that protected API routes fail-closed in production when internal key is not set"""
    # Ensure internal key is not set
    if 'MIROSHARK_INTERNAL_KEY' in os.environ:
        del os.environ['MIROSHARK_INTERNAL_KEY']
    
    # Mock Config.DEBUG to simulate production/staging mode
    original_debug = Config.DEBUG
    Config.DEBUG = False
    
    try:
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test a protected API route when key is not configured
            # In production mode without key, should return 503
            response = client.post('/api/graph/ontology/generate')
            # Should return 503 (service unavailable) when key not configured in production
            assert response.status_code == 503
    finally:
        Config.DEBUG = original_debug


def test_protected_api_without_internal_key_env_debug():
    """Test that protected API routes fail-open in debug mode when internal key is not set"""
    # Ensure internal key is not set
    if 'MIROSHARK_INTERNAL_KEY' in os.environ:
        del os.environ['MIROSHARK_INTERNAL_KEY']
    
    # Mock Config.DEBUG to simulate development mode
    original_debug = Config.DEBUG
    Config.DEBUG = True
    
    try:
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test a protected API route when key is not configured in debug mode
            # In debug mode without key, auth guard is disabled (fail-open for development)
            # Request will fail with 400 due to missing required fields, not 401/503
            response = client.post('/api/graph/ontology/generate')
            # Should return 400 (bad request) because auth guard is disabled
            assert response.status_code == 400
    finally:
        Config.DEBUG = original_debug


def test_openapi_docs_without_internal_key():
    """Test that OpenAPI docs are accessible without authentication (if configured)"""
    # Set internal key to enable auth guard
    os.environ['MIROSHARK_INTERNAL_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test OpenAPI docs endpoint
        response = client.get('/api/openapi.json')
        # May be 200 (if exempt) or 401 (if protected)
        # This test documents current behavior
        assert response.status_code in [200, 401]
