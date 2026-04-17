import jwt

def test():
    try:
        jwt.decode("undefined", "dummy_secret", algorithms=["HS256"])
        print("Success")
    except Exception as e:
        print("Exception for 'undefined':", type(e).__name__, str(e))
        
    try:
        jwt.decode("eyJhbGci", "dummy_secret", algorithms=["HS256"])
        print("Success")
    except Exception as e:
        print("Exception for 'eyJhbGci':", type(e).__name__, str(e))

test()
