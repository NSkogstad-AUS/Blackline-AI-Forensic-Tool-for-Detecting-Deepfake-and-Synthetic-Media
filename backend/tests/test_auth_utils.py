import re
import time
from backend.src import auth
from jose import jwt


def test_hash_and_verify_password():
    pw = "s3cr3t-pass"
    hashed = auth.hash_password(pw)
    assert isinstance(hashed, str) and len(hashed) > 0
    assert auth.verify_password(pw, hashed) is True
    # wrong password
    assert auth.verify_password("nope", hashed) is False


def test_create_access_token_contains_username():
    uname = "testuser"
    token = auth.create_access_token(uname)
    assert isinstance(token, str) and token.count(".") == 2
    # decode using same secret/alg
    payload = jwt.decode(token, auth.JWT_SECRET, algorithms=[auth.JWT_ALG])
    assert payload.get("sub") == uname
    # exp should be an integer timestamp in the future
    assert isinstance(payload.get("exp"), int)
    assert payload.get("exp") > int(time.time())


def test_debug_admin_username_checks():
    # default debug admin is 'admin'
    assert auth.debug_admin_username() == "admin"
    assert auth.is_debug_admin_username("admin") is True
    assert auth.is_debug_admin_username("Admin") is True
    assert auth.is_debug_admin_username("") is False
