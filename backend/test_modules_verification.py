import sys
import json
import time
import uuid
import urllib.request
import urllib.error

# Ensure unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Generate an admin JWT directly for testing admin routes
sys.path.insert(0, ".")
from app.core.security import create_access_token

BASE_URL = "http://localhost:8000/api/v1"

def api_request(endpoint, method="GET", body=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_str = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body_str)
        except Exception:
            return e.code, {"error": body_str}

def run_tests():
    print("=== STARTING FULL MODULES VERIFICATION ===", flush=True)
    ts = int(time.time())

    # 1. Register Customer & Provider
    cust_email = f"cust_mod_{ts}@servix.dev"
    pro_email = f"pro_mod_{ts}@servix.dev"

    st, r_cust = api_request("/auth/register/customer", "POST", {
        "email": cust_email,
        "password": "Password123!",
        "full_name": "Alice Customer",
        "phone": "555-111-0002",
        "city": "Austin",
        "state": "TX"
    })
    assert st == 201, f"Customer reg failed: {r_cust}"
    cust_token = r_cust["data"]["access_token"]
    cust_user_id = r_cust["data"]["user_id"]

    st, r_pro = api_request("/auth/register/provider", "POST", {
        "email": pro_email,
        "password": "Password123!",
        "full_name": "Bob Master Electrician",
        "phone": "555-222-0003",
        "business_name": "Bob's Elite Electrical",
        "trade": "Electrician",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "hourly_rate": 95.0
    })
    assert st == 201, f"Provider reg failed: {r_pro}"
    pro_token = r_pro["data"]["access_token"]

    st, r_me = api_request("/auth/me", "GET", token=pro_token)
    assert st == 200
    pro_profile_id = r_me["data"]["provider_profile"]["id"]
    print(f"[OK] 1. Registered Customer ({cust_email}) & Provider ({pro_email})", flush=True)

    # 2. Test Favorites Module
    st, r_fav = api_request(f"/favorites/{pro_profile_id}", "POST", token=cust_token)
    assert st == 201, f"Fav add failed: {r_fav}"
    print(f"[OK] 2. Favorites: Added provider {pro_profile_id} to customer favorites", flush=True)

    st, r_favs = api_request("/favorites", "GET", token=cust_token)
    assert st == 200 and len(r_favs["data"]) >= 1, f"Fav list failed: {r_favs}"
    print(f"[OK] 2. Favorites: Successfully listed {len(r_favs['data'])} favorited provider(s)", flush=True)

    st, r_unfav = api_request(f"/favorites/{pro_profile_id}", "DELETE", token=cust_token)
    assert st == 200, f"Fav remove failed: {r_unfav}"
    print("[OK] 2. Favorites: Successfully removed favorite", flush=True)

    # 3. Create Job, Bid, Escrow Booking for Review & Notification tests
    st, r_cats = api_request("/categories", "GET")
    assert st == 200 and len(r_cats["data"]) > 0
    cat_id = r_cats["data"][0]["id"]

    st, r_job = api_request("/jobs", "POST", {
        "title": f"Rewire Main Panel {ts}",
        "description": "Upgrade 200A electrical service panel.",
        "category_id": cat_id,
        "urgency": "EMERGENCY",
        "target_budget": 350.0,
        "address": "789 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "latitude": 30.2672,
        "longitude": -97.7431
    }, token=cust_token)
    assert st == 201, f"Job create failed: {r_job}"
    job_id = r_job["data"]["id"]

    st, r_bid = api_request("/bids", "POST", {
        "job_id": job_id,
        "amount": 320.0,
        "eta_description": "Can start tomorrow morning",
        "message": "Licensed master electrician with parts on hand."
    }, token=pro_token)
    assert st == 201, f"Bid submit failed: {r_bid}"
    bid_id = r_bid["data"]["id"]

    st, r_book = api_request("/bookings/accept-bid", "POST", {
        "job_id": job_id,
        "bid_id": bid_id,
        "scheduled_date": "2026-09-06",
        "scheduled_time": "09:00 AM"
    }, token=cust_token)
    assert st == 201, f"Booking failed: {r_book}"
    book_id = r_book["data"]["id"]

    # Start and Complete with Escrow release
    st, _ = api_request(f"/bookings/{book_id}/start", "POST", token=pro_token)
    assert st == 200
    st, _ = api_request(f"/bookings/{book_id}/confirm-release", "POST", token=cust_token)
    assert st == 200
    print("[OK] 3. Job lifecycle & Escrow release verified", flush=True)

    # 4. Reviews Module (Submit + Provider Reply)
    st, r_rev = api_request("/reviews", "POST", {
        "booking_id": book_id,
        "rating": 5,
        "comment": "Exceptional electrical work! Professional, clean, and on time."
    }, token=cust_token)
    assert st == 201, f"Review submit failed: {r_rev}"
    rev_id = r_rev["data"]["id"]
    print(f"[OK] 4. Reviews: Customer published 5-star review (ID: {rev_id})", flush=True)

    st, r_reply = api_request(f"/reviews/{rev_id}/reply", "POST", {
        "reply_text": "Thank you for the kind review! Always happy to help."
    }, token=pro_token)
    assert st == 200, f"Provider reply failed: {r_reply}"
    assert r_reply["data"]["provider_reply"] == "Thank you for the kind review! Always happy to help."
    print("[OK] 4. Reviews: Provider successfully replied to review", flush=True)

    st, r_list_rev = api_request(f"/reviews/provider/{pro_profile_id}", "GET")
    assert st == 200 and len(r_list_rev["data"]) >= 1
    print(f"[OK] 4. Reviews: Provider reviews query returned {len(r_list_rev['data'])} review(s)", flush=True)

    # 5. Notifications Module
    st, r_notifs = api_request("/notifications", "GET", token=pro_token)
    assert st == 200, f"Notifs list failed: {r_notifs}"
    notifs = r_notifs["data"]
    print(f"[OK] 5. Notifications: Provider received {len(notifs)} event-driven notification(s)", flush=True)

    st, r_unread = api_request("/notifications/unread-count", "GET", token=pro_token)
    assert st == 200
    print(f"[OK] 5. Notifications: Unread count badge = {r_unread['data']['unread_count']}", flush=True)

    if len(notifs) > 0:
        first_notif_id = notifs[0]["id"]
        st, _ = api_request(f"/notifications/{first_notif_id}/read", "POST", token=pro_token)
        assert st == 200
        print("[OK] 5. Notifications: Marked individual notification as read", flush=True)

    st, r_read_all = api_request("/notifications/read-all", "POST", token=pro_token)
    assert st == 200
    print("[OK] 5. Notifications: Marked all notifications as read", flush=True)

    # 6. Admin Panel APIs
    import asyncio
    from app.database.session import AsyncSessionLocal
    from app.models.user import User
    from app.models.enums import UserRole
    from sqlalchemy import update

    async def promote_user_to_admin(uid_str):
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(User).where(User.id == uuid.UUID(uid_str)).values(role=UserRole.ADMIN)
            )
            await session.commit()

    asyncio.run(promote_user_to_admin(cust_user_id))
    admin_token = create_access_token(subject=cust_user_id, role="ADMIN")
    print("\n--- Testing Admin Panel APIs ---", flush=True)

    st, r_metrics = api_request("/admin/metrics", "GET", token=admin_token)
    assert st == 200, f"Admin metrics failed: {r_metrics}"
    print(f"[OK] 6. Admin Metrics: {r_metrics['data']}", flush=True)

    st, r_reports = api_request("/admin/reports", "GET", token=admin_token)
    assert st == 200, f"Admin reports failed: {r_reports}"
    print(f"[OK] 6. Admin Reports: Total Users={r_reports['data']['total_users']}, Revenue=${r_reports['data']['total_platform_revenue']}", flush=True)

    st, r_users = api_request("/admin/users", "GET", token=admin_token)
    assert st == 200 and len(r_users["data"]) > 0, f"Admin users failed: {r_users}"
    print(f"[OK] 6. Admin Users: Retrieved {len(r_users['data'])} user accounts", flush=True)

    st, r_provs = api_request("/admin/providers", "GET", token=admin_token)
    assert st == 200 and len(r_provs["data"]) > 0, f"Admin providers failed: {r_provs}"
    print(f"[OK] 6. Admin Providers: Retrieved {len(r_provs['data'])} providers", flush=True)

    # Verify provider license
    st, r_ver = api_request(f"/admin/providers/{pro_profile_id}/verify", "POST", {"is_verified": True}, token=admin_token)
    assert st == 200 and r_ver["data"]["is_license_verified"] is True
    print("[OK] 6. Admin Verification: Approved provider trade license", flush=True)

    # Admin category management
    test_slug = f"solar-panel-{ts}"
    st, r_new_cat = api_request("/admin/categories", "POST", {
        "name": f"Solar & EV Installation {ts}",
        "slug": test_slug,
        "description": "Solar energy systems and level 2 EV charging stations",
        "icon": "Sun",
        "avg_price_min": 250.0,
        "avg_price_max": 1500.0,
        "is_active": True
    }, token=admin_token)
    assert st == 201, f"Admin create cat failed: {r_new_cat}"
    new_cat_id = r_new_cat["data"]["id"]
    print(f"[OK] 6. Admin Categories: Created new category '{test_slug}'", flush=True)

    st, r_up_cat = api_request(f"/admin/categories/{new_cat_id}", "PUT", {
        "avg_price_max": 2000.0
    }, token=admin_token)
    assert st == 200
    print("[OK] 6. Admin Categories: Updated category estimate pricing", flush=True)

    # Admin jobs list
    st, r_admin_jobs = api_request("/admin/jobs", "GET", token=admin_token)
    assert st == 200 and len(r_admin_jobs["data"]) > 0
    print(f"[OK] 6. Admin Jobs: Listed {len(r_admin_jobs['data'])} jobs across platform", flush=True)

    # Admin review moderation
    st, r_admin_revs = api_request("/admin/reviews", "GET", token=admin_token)
    assert st == 200 and len(r_admin_revs["data"]) > 0
    print(f"[OK] 6. Admin Reviews: Listed {len(r_admin_revs['data'])} platform reviews", flush=True)

    print("\n========================================================")
    print("[SUCCESS] ALL SERVIX MODULES (REVIEWS, FAVORITES, NOTIFICATIONS, ADMIN) ARE 100% OPERATIONAL!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
