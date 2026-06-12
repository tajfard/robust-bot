"""MikroTik User Manager API wrapper.

RouterOS 7 paths used:
  /user-manager/user        — CRUD for RADIUS users
  /user-manager/user-profile — links a user to a profile (bandwidth / limits)
"""
import secrets
import string  # noqa: F401 — kept for _random_digits
import routeros_api
from routeros_api.exceptions import RouterOsApiParsingError
from config import MIKROTIK_HOST, MIKROTIK_PORT, MIKROTIK_USER, MIKROTIK_PASSWORD

_USER_PATH = "/user-manager/user"
_USER_PROFILE_PATH = "/user-manager/user-profile"


def _connect():
    pool = routeros_api.RouterOsApiPool(
        MIKROTIK_HOST,
        username=MIKROTIK_USER,
        password=MIKROTIK_PASSWORD,
        port=MIKROTIK_PORT,
        plaintext_login=True,
    )
    return pool.get_api()


def _get(resource, **filters) -> list:
    """Return resource.get() result; treat RouterOS 7 !empty response as []."""
    try:
        return resource.get(**filters)
    except RouterOsApiParsingError:
        return []


def _random_digits(length: int) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def create_vpn_user(username: str, comment: str = "", profile: str = "") -> dict:
    """Create a User Manager user, assign it to the given profile, return credentials."""
    password = _random_digits(8)
    api = _connect()

    api.get_resource(_USER_PATH).add(
        name=username,
        password=password,
        comment=comment,
        disabled="false",
    )

    if profile:
        api.get_resource(_USER_PROFILE_PATH).add(
            user=username,
            profile=profile,
        )

    return {"username": username, "password": password}


def user_exists(username: str) -> bool:
    api = _connect()
    return len(_get(api.get_resource(_USER_PATH), name=username)) > 0


def enable_vpn_user(username: str):
    api = _connect()
    resource = api.get_resource(_USER_PATH)
    items = _get(resource, name=username)
    if items:
        resource.set(id=items[0]["id"], disabled="false")


def disable_vpn_user(username: str):
    api = _connect()
    resource = api.get_resource(_USER_PATH)
    items = _get(resource, name=username)
    if items:
        resource.set(id=items[0]["id"], disabled="true")


def update_user_profile(username: str, profile: str):
    """Replace all user-profile entries for this user with a fresh one."""
    api = _connect()
    up_res = api.get_resource(_USER_PROFILE_PATH)
    for entry in _get(up_res, user=username):
        up_res.remove(id=entry["id"])
    if profile:
        up_res.add(user=username, profile=profile)


def get_user_stats(username: str) -> dict:
    """Return accumulated traffic counters from User Manager.

    Returns dict with keys: found (bool), bytes_in (int), bytes_out (int).
    RouterOS 7 stores lifetime totals in the user object itself.
    """
    api = _connect()
    users = _get(api.get_resource(_USER_PATH), name=username)
    if not users:
        return {"found": False, "bytes_in": 0, "bytes_out": 0}
    u = users[0]
    return {
        "found": True,
        "bytes_in": int(u.get("bytes-in", 0) or 0),
        "bytes_out": int(u.get("bytes-out", 0) or 0),
        "disabled": u.get("disabled", "false") == "true",
    }


def delete_vpn_user(username: str):
    api = _connect()
    resource = api.get_resource(_USER_PATH)
    items = _get(resource, name=username)
    if items:
        # Remove the user-profile link first (avoids orphan entries)
        up_resource = api.get_resource(_USER_PROFILE_PATH)
        up_items = _get(up_resource, user=username)
        for up in up_items:
            up_resource.remove(id=up["id"])
        resource.remove(id=items[0]["id"])
