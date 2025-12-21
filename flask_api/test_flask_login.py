#!/usr/bin/env python3
"""
Test script for Flask API login
"""

import requests
import json
import os
import sys

def test_flask_login():
    """Test the Flask login endpoint"""
    url = "http://localhost:8000/api/v1/auth/login"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "username": "testuser",
        "password": "test123"
    }
    
    print("🔍 Testing Flask login endpoint...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json()
        else:
            print("❌ Login failed!")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the Flask API server. Is it running?")
        print("Try starting the server with: python app.py")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during request: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_health():
    """Test the health endpoint"""
    url = "http://localhost:8000/health"
    
    print("\n🔍 Testing health endpoint...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check successful!")
        else:
            print("❌ Health check failed!")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")

if __name__ == "__main__":
    print("🚀 Flask API Test")
    print("=" * 50)
    
    test_health()
    test_flask_login()
    
    print("\n💡 Next steps:")
    print("1. If login works, test protected endpoints with the JWT token")
    print("2. If login fails, check the Flask server logs")
    print("3. Make sure the testuser exists in the database")
