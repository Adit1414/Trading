import requests
import os
import json

URL = "https://kfyxutuvkkvqlpoedond.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmeXh1dHV2a2t2cWxwb2Vkb25kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzNDE4MjUsImV4cCI6MjA4OTkxNzgyNX0.NZc8_J379W9FLxkHQcMo9p9mpAkmNDIIpIOSrJobNWk"

res = requests.post(
    f"{URL}/auth/v1/signup",
    headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
    json={"email": "testagent12345@test.com", "password": "TestPassword123!"}
)
print("Response:", res.status_code, res.text)
if res.status_code == 200:
    token = res.json().get("access_token")
    if token:
        import base64
        header_b64 = token.split('.')[0]
        header_b64 += "=" * ((4 - len(header_b64) % 4) % 4)
        print("Header:", base64.urlsafe_b64decode(header_b64).decode())
