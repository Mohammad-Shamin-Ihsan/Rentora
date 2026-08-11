"""
Auth dependency for the Ratings & Reviews endpoints.

⚠️ TEMPORARY — your team's real login system (Module 1 Part 1) hasn't
been built yet, so there's no real JWT to verify. For now, this trusts
a plain header telling it who's "logged in," so you can test THIS
module today without waiting on the auth module.

Once Module 1 Part 1 exists, replace the body of get_current_user_id()
with real JWT verification (decode the token your login endpoint
issues, pull the user id out of it) — the function's signature and
what it returns (an int user id) stay exactly the same, so nothing
else in this codebase has to change.
"""

from fastapi import Header, HTTPException, status


def get_current_user_id(x_debug_user_id: int = Header(..., alias="X-Debug-User-Id")) -> int:
    """
    DEV-ONLY. The frontend/Postman/docs page sends:
      X-Debug-User-Id: 2
    and this trusts it completely — obviously never do this in
    production. Swap this out the moment real auth exists.
    """
    if x_debug_user_id <= 0:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid X-Debug-User-Id header.")
    return x_debug_user_id
