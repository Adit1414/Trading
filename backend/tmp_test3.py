import sys
sys.path.append('d:\\aditya data\\Projects\\AlgoKaisen\\backend')

from app.core.auth import decode_token

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmeXh1dHV2a2t2cWxwb2Vkb25kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzNDE4MjUsImV4cCI6MjA4OTkxNzgyNX0.NZc8_J379W9FLxkHQcMo9p9mpAkmNDIIpIOSrJobNWk'

try:
    print(decode_token(token))
except Exception as e:
    print(type(e), e)
