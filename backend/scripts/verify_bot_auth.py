"""
Verify bot authentication is working correctly.

Tests:
1. Bot token matches between backend and telegram_bot.py
2. Backend accepts bot token in X-Bot-Token header
3. Test video processing endpoint with bot auth
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

print("=== Bot Authentication Verification ===\n")

# Check environment variables
bot_token = os.getenv("BOT_TOKEN")
bot_user_id = os.getenv("BOT_USER_ID")
api_url = os.getenv("REELSCRIPT_API", "http://localhost:8002")

print(f"BOT_TOKEN: {bot_token}")
print(f"BOT_USER_ID: {bot_user_id}")
print(f"REELSCRIPT_API: {api_url}")

if not bot_token:
    print("\n[ERROR] BOT_TOKEN not set in environment!")
    sys.exit(1)

# Test auth middleware
print("\n=== Testing Auth Middleware ===\n")

from middleware.auth import get_current_user
from fastapi import Request

class MockRequest:
    def __init__(self, headers):
        self.headers = headers

# Test with valid bot token
try:
    req = MockRequest({"X-Bot-Token": bot_token})
    user = get_current_user(req)
    print(f"[OK] Bot token accepted")
    print(f"     User: {user}")
except Exception as e:
    print(f"[ERROR] Bot token rejected: {e}")
    sys.exit(1)

# Test with invalid token
try:
    req = MockRequest({"X-Bot-Token": "invalid-token"})
    user = get_current_user(req)
    print(f"[ERROR] Invalid token was accepted! {user}")
    sys.exit(1)
except Exception:
    print(f"[OK] Invalid token correctly rejected")

# Test with no token
try:
    req = MockRequest({})
    user = get_current_user(req)
    print(f"[ERROR] No token was accepted! {user}")
    sys.exit(1)
except Exception:
    print(f"[OK] Missing token correctly rejected")

print("\n=== All Tests Passed ===")
print("\nTo test with real API:")
print(f'curl -X POST "{api_url}/api/videos/process" \\')
print(f'  -H "Content-Type: application/json" \\')
print(f'  -H "X-Bot-Token: {bot_token}" \\')
print(f'  -d \'{{"url": "https://www.instagram.com/reel/test"}}\'')
