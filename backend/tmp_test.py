import jwt
import sys

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmeXh1dHV2a2t2cWxwb2Vkb25kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzNDE4MjUsImV4cCI6MjA4OTkxNzgyNX0.NZc8_J379W9FLxkHQcMo9p9mpAkmNDIIpIOSrJobNWk'
key = 'YXOtzcApvKxPY22QPwnvFRggjJvljmLxu0J570+hEGMzKtImeRibDBA376ma10fjD/9lIy1wtCR+pEm9vY2Dqw=='
# Let's decode this anon key with our new secret:
try:
    decoded = jwt.decode(token, key, algorithms=['HS256'])
    print("Success")
except Exception as e:
    print("Error:", type(e), str(e))
