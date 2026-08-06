#!/usr/bin/env python3
"""
Test script to verify Flask app returns proper JSON error responses
"""

import json
from io import BytesIO
from app import app, get_user_friendly_error_message

def test_error_message_function():
    """Test the error message function directly"""
    
    # Test JSONDecodeError
    json_error = json.JSONDecodeError("Expecting value", "test", 0)
    message = get_user_friendly_error_message(json_error, "invalid_empty.json")
    print(f"JSONDecodeError message: {message}")
    
    # Test KeyError  
    key_error = KeyError("experiments")
    message = get_user_friendly_error_message(key_error, "missing_experiments.json")
    print(f"KeyError message: {message}")
    
    # Test generic error
    generic_error = Exception("Something went wrong")
    message = get_user_friendly_error_message(generic_error, "test.json")
    print(f"Generic error message: {message}")

def test_flask_app():
    """Test Flask app with test client"""
    with app.test_client() as client:
        invalid_response = client.post(
            '/upload',
            data={'file': (BytesIO(b''), 'invalid_empty.json')},
        )
        missing_response = client.post(
            '/upload',
            data={'file': (BytesIO(b'{"procedures": []}'), 'missing_experiments.json')},
        )

    assert invalid_response.status_code == 400
    assert invalid_response.is_json
    assert 'not valid JSON' in invalid_response.get_json()['message']
    assert missing_response.status_code == 400
    assert missing_response.is_json
    assert "missing the required 'experiments' field" in missing_response.get_json()['message']

if __name__ == '__main__':
    print("Testing error message function...")
    test_error_message_function()
    print("\nTesting Flask app...")
    test_flask_app()
