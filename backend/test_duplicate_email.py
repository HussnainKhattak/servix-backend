"""
test_duplicate_email.py
=======================
Verifies two invariants introduced by the role-locked auth flow:

  1. Duplicate email — attempting to register the same email under a different
     role is rejected with HTTP 409 and the human-readable error message
     "An account with this email already exists. Please log in instead."

  2. Role-free login — POST /auth/login accepts only email + password (no role
     field) and returns a JWT whose `role` matches what was stored at signup.

Usage
-----
Start the backend first, then run:

    cd backend
    python test_duplicate_email.py

The script exits with code 0 on success and prints a per-test PASS/FAIL line.
"""

import asyncio
import sys
import httpx

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_EMAIL = "test.dup.servix@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Dup Test User"

CUSTOMER_PAYLOAD = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD,
    "full_name": TEST_NAME,
}

PROVIDER_PAYLOAD = {
    "email": TEST_EMAIL,          # <-- same email as the customer above
    "password": TEST_PASSWORD,
    "full_name": TEST_NAME,
    "phone": "5550001234",
    "business_name": "Dup Plumbing Co.",
    "trade": "Plumbing",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
}


# ── Helpers ──────────────────────────────────────────────────────────────────
def ok(label: str) -> None:
    print(f"  [PASS]  {label}")


def fail(label: str, detail: str) -> None:
    print(f"  [FAIL]  {label}")
    print(f"          {detail}")


async def cleanup_test_account(client: httpx.AsyncClient) -> None:
    """Best-effort cleanup: log in and delete the account if the endpoint exists."""
    try:
        r = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        if r.status_code == 200:
            token = r.json()["data"]["access_token"]
            await client.delete(
                f"{BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
    except Exception:
        pass  # cleanup is best-effort; ignore errors


# ── Tests ────────────────────────────────────────────────────────────────────
async def test_duplicate_email_rejected(client: httpx.AsyncClient) -> bool:
    """
    Register as customer, then try to register as provider with the same email.
    The second call must return 409 with the correct message.
    """
    label = "Duplicate email is rejected (409) with correct message"
    passed = True

    # Step 1 — register as customer (may already exist from a prior run)
    r1 = await client.post(f"{BASE_URL}/auth/register/customer", json=CUSTOMER_PAYLOAD)
    if r1.status_code not in (201, 409):
        fail(label, f"Unexpected status on first registration: {r1.status_code} — {r1.text}")
        return False

    # Step 2 — try to register as provider with the same email
    r2 = await client.post(f"{BASE_URL}/auth/register/provider", json=PROVIDER_PAYLOAD)
    if r2.status_code != 409:
        fail(label, f"Expected 409, got {r2.status_code} — {r2.text}")
        passed = False
    else:
        body = r2.json()
        msg: str = body.get("message", "") or body.get("detail", "") or str(body)
        expected_fragment = "An account with this email already exists"
        if expected_fragment.lower() not in msg.lower():
            fail(label, f"Message does not contain expected text.\n  Got: {msg!r}")
            passed = False
        else:
            ok(label)

    return passed


async def test_login_without_role(client: httpx.AsyncClient) -> bool:
    """
    POST /auth/login with only email + password (no role field).
    Must return 200 and a role that matches the signed-up role (customer/client).
    """
    label = "Login without role field returns 200 + correct role"

    r = await client.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        # No 'role' key — backend must read from DB
    )
    if r.status_code != 200:
        fail(label, f"Expected 200, got {r.status_code} — {r.text}")
        return False

    data = r.json().get("data", {})
    role = data.get("role", "")
    customer_roles = {"client", "customer"}
    if role not in customer_roles:
        fail(label, f"Expected role in {customer_roles}, got {role!r}")
        return False

    ok(label)
    return True


async def test_login_wrong_password(client: httpx.AsyncClient) -> bool:
    """POST /auth/login with wrong password must return 401."""
    label = "Login with wrong password returns 401"

    r = await client.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": "WrongPassword!"},
    )
    if r.status_code != 401:
        fail(label, f"Expected 401, got {r.status_code}")
        return False

    ok(label)
    return True


# ── Runner ───────────────────────────────────────────────────────────────────
async def main() -> None:
    print("\n-- Servix Auth Tests --------------------------------------------------")
    print(f"   Base URL : {BASE_URL}")
    print(f"   Test email: {TEST_EMAIL}\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        await cleanup_test_account(client)

        results = await asyncio.gather(
            test_duplicate_email_rejected(client),
            return_exceptions=True,
        )
        # Run login tests after registration so account exists
        results += await asyncio.gather(
            test_login_without_role(client),
            test_login_wrong_password(client),
            return_exceptions=True,
        )

    passed = sum(1 for r in results if r is True)
    total = len(results)
    print(f"\n-- Results: {passed}/{total} passed -------------------------------------------\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
