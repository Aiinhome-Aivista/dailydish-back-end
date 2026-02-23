import random
import string
import uuid
import time
import hashlib

# In production use Redis instead of dict
CAPTCHA_STORE = {}

CAPTCHA_EXPIRY_SECONDS = 120  # 2 minutes

def generate_captcha():
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    captcha_id = str(uuid.uuid4())

    hashed_code = hashlib.sha256(captcha_text.encode()).hexdigest()

    CAPTCHA_STORE[captcha_id] = {
        "code": hashed_code,
        "expires": time.time() + CAPTCHA_EXPIRY_SECONDS
    }

    return captcha_id, captcha_text


def verify_captcha(captcha_id, user_input):
    record = CAPTCHA_STORE.get(captcha_id)

    if not record:
        return False

    # Expiry check
    if time.time() > record["expires"]:
        CAPTCHA_STORE.pop(captcha_id, None)
        return False

    hashed_input = hashlib.sha256(user_input.upper().encode()).hexdigest()

    # One-time use
    CAPTCHA_STORE.pop(captcha_id, None)

    return hashed_input == record["code"]