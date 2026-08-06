#!/usr/bin/env python3
"""
Quick test script to verify error handling works correctly
"""

from io import BytesIO

from app import app

def test_error_file():
    """Invalid JSON returns a structured client error without a live server."""
    with app.test_client() as client:
        response = client.post(
            '/upload',
            data={'file': (BytesIO(b'{ this is not valid json'), 'invalid_test.json')},
        )

    assert response.status_code == 400
    assert response.is_json
    assert response.get_json()['error'] is True
    assert 'not valid JSON' in response.get_json()['message']

if __name__ == '__main__':
    test_error_file()
