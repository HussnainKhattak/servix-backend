import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api/v1"


def api_request(path: str, method: str = "GET", data: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content)
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            err_json = json.loads(content)
        except Exception:
            err_json = {"raw": content}
        return e.code, err_json


def test_full_marketplace_workflow():
    print("=== 1. FETCH SERVICE CATEGORIES ===")
    status, res = api_request("/categories")
    assert status == 200, f"Failed categories: {res}"
    cats = res["data"]
    assert len(cats) > 0, "No categories found!"
    plumbing_cat = next((c for c in cats if c["slug"] == "plumbing"), cats[0])
    plumbing_id = plumbing_cat["id"]
    print(f"Categories Count: {len(cats)} | Selected Category: {plumbing_cat['name']} ({plumbing_id})")

    print("\n=== 2. REGISTER CUSTOMER & PROVIDER ===")
    ts = int(time.time())
    cust_email = f"sarah_cust_{ts}@servix.dev"
    pro_email = f"dave_pro_{ts}@servix.dev"

    # Register customer
    status, r_cust = api_request("/auth/register/customer", "POST", {
        "email": cust_email,
        "password": "SecurePassword123!",
        "full_name": "Sarah Connor",
        "phone": "555-1122",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "default_address": "400 Congress Ave",
    })
    assert status == 201, f"Customer register failed: {r_cust}"
    cust_token = r_cust["data"]["access_token"]
    print(f"Customer registered: {cust_email}")

    # Register provider
    status, r_pro = api_request("/auth/register/provider", "POST", {
        "email": pro_email,
        "password": "SecurePassword123!",
        "full_name": "Dave Master Plumber",
        "phone": "555-9988",
        "business_name": "Dave Pro Plumbing LLC",
        "trade": "Plumbing",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "hourly_rate": 95.0,
        "service_radius_miles": 25.0,
    })
    assert status == 201, f"Provider register failed: {r_pro}"
    pro_token = r_pro["data"]["access_token"]
    print(f"Provider registered: {pro_email}")

    print("\n=== 3. CUSTOMER POSTS SERVICE REQUEST ===")
    status, r_job = api_request("/jobs", "POST", {
        "title": "Fix Kitchen Pipe Leak",
        "description": "P-trap underneath kitchen sink ruptured and leaking onto floor.",
        "category_id": plumbing_id,
        "urgency": "EMERGENCY",
        "target_budget": 150.0,
        "address": "400 Congress Ave, Apt 4B",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "latitude": 30.2672,
        "longitude": -97.7431,
    }, token=cust_token)
    assert status == 201, f"Job create failed: {r_job}"
    job_id = r_job["data"]["id"]
    print(f"Job Created! ID: {job_id} | Status: {r_job['data']['status']}")

    print("\n=== 4. PROVIDER BROWSE NEARBY JOBS ===")
    status, r_nearby = api_request("/jobs/nearby", "GET", token=pro_token)
    assert status == 200, f"Nearby jobs failed: {r_nearby}"
    nearby_jobs = r_nearby["data"]
    print(f"Nearby available jobs count: {len(nearby_jobs)}")

    print("\n=== 5. PROVIDER SUBMITS BID QUOTE ===")
    status, r_bid = api_request("/bids", "POST", {
        "job_id": job_id,
        "amount": 135.0,
        "eta_description": "Within 45 minutes",
        "proposed_start_date": "2026-09-02T14:00:00Z",
        "message": "I have replacement PVC and brass fittings on my truck. Ready to dispatch immediately.",
        "warranty_terms": "6 Months Leak-Free Guarantee",
    }, token=pro_token)
    assert status == 201, f"Submit bid failed: {r_bid}"
    bid_id = r_bid["data"]["id"]
    print(f"Bid Submitted! ID: {bid_id} | Amount: ${r_bid['data']['amount']}")

    print("\n=== 6. CUSTOMER COMPARES QUOTES ===")
    status, r_quotes = api_request(f"/bids/job/{job_id}", "GET", token=cust_token)
    assert status == 200, f"Get job bids failed: {r_quotes}"
    quotes = r_quotes["data"]
    print(f"Quotes received on job: {len(quotes)}")

    print("\n=== 7. CUSTOMER ACCEPTS QUOTE & LOCKS ESCROW ===")
    status, r_book = api_request("/bookings/accept-bid", "POST", {
        "job_id": job_id,
        "bid_id": bid_id,
        "scheduled_date": "2026-09-02",
        "scheduled_time": "14:00",
    }, token=cust_token)
    assert status == 201, f"Accept bid failed: {r_book}"
    booking_data = r_book["data"]
    booking_id = booking_data["id"]
    print(f"Booking ID: {booking_id}")
    print(f"Escrow: {booking_data['escrow_status']} | Agreed: ${booking_data['agreed_price']} | Fee: ${booking_data['platform_fee']} | Payout: ${booking_data['provider_payout']}")

    print("\n=== 8. PROVIDER STARTS WORK ===")
    status, r_start = api_request(f"/bookings/{booking_id}/start", "POST", token=pro_token)
    assert status == 200, f"Start job failed: {r_start}"
    print(f"Booking Status: {r_start['data']['status']}")

    print("\n=== 9. CUSTOMER CONFIRMS COMPLETION & RELEASES ESCROW ===")
    status, r_release = api_request(f"/bookings/{booking_id}/confirm-release", "POST", token=cust_token)
    assert status == 200, f"Release escrow failed: {r_release}"
    rel_data = r_release["data"]
    print(f"Booking Status: {rel_data['status']} | Escrow Status: {rel_data['escrow_status']}")

    print("\n=== 10. CUSTOMER LEAVES 5-STAR REVIEW ===")
    status, r_rev = api_request("/reviews", "POST", {
        "booking_id": booking_id,
        "rating": 5.0,
        "comment": "Dave arrived in 30 minutes and fixed the leak cleanly. Highly recommend!",
        "punctuality_rating": 5.0,
        "cleanliness_rating": 5.0,
        "communication_rating": 5.0,
    }, token=cust_token)
    assert status == 201, f"Submit review failed: {r_rev}"
    print(f"Review Published! Rating: {r_rev['data']['rating']}")

    print("\n=== 11. CUSTOMER FAVORITES PROVIDER ===")
    status, r_me = api_request("/auth/me", "GET", token=pro_token)
    pro_profile_id = r_me["data"]["provider_profile"]["id"]
    status, r_fav = api_request(f"/favorites/{pro_profile_id}", "POST", token=cust_token)
    assert status == 201, f"Favorite provider failed: {r_fav}"
    print(f"Provider Favorited! ID: {r_fav['data']['id']}")

    print("\n========================================================")
    print("[SUCCESS] 100% OF SERVIX MARKETPLACE WORKFLOW VERIFIED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    test_full_marketplace_workflow()
