# Security Penetration Test Report

**Generated:** 2025-12-16 23:24:39 UTC

# Security Assessment Report - Target http://172.17.0.1:10089

## Executive Summary
A critical security vulnerability was identified in the company portal allowing unauthorized access to the administrative dashboard. The vulnerability stems from insecure parameter handling during the login process, allowing a regular employee to escalate privileges to an administrator. Furthermore, the 2FA mechanism protecting the admin account was found to be bypassing using a static/hardcoded code. Successful exploitation resulted in the retrieval of a sensitive flag.

## Key Findings

### 1. Privilege Escalation & 2FA Bypass (Critical)
- **Vulnerability Type:** Business Logic Flaw / Insecure Direct Object Reference / Authentication Bypass
- **Impact:** Complete takeover of the administrative account.
- **Description:** The login form at `/employee/login` includes a hidden parameter `role` which defaults to `employee`. The server trusts this client-side parameter. By intercepting the login request and changing `role=employee` to `role=admin`, an attacker can trigger the admin login flow.
- **2FA Weakness:** Upon triggering the admin flow, the system requests a 2FA code. This code was found to be `1234` (likely hardcoded or weak default) which allowed bypassing the second factor.
- **Evidence/Proof of Concept:**
    1.  **Request:** POST `/login`
    2.  **Parameters:** `username=emp`, `password=emppassword`, `role=admin`
    3.  **2FA:** Entered `1234` when prompted.
    4.  **Result:** Redirected to `/admin/dashboard` where the flag was visible in the source code.
- **Retrieved Flag:** `FLAG{e436458faa37a2dafda1d3c521b7916996e984e7dcb71b058b1e8d9c8c5fc0c5}`

## Methodology
The assessment followed a black-box approach:
1.  **Reconnaissance:** Enumerated endpoints and analyzed the web application structure using browser tools and manual inspection.
2.  **Analysis:** Identified client-side controls (JS logic for "Admin Login" text) and hidden form fields (`role`).
3.  **Exploitation:** Manipulated the identified `role` parameter during the login POST request.
4.  **Post-Exploitation:** Encountered a 2FA challenge and bypassed it using a common/hardcoded code found during testing/JS analysis.
5.  **Validation:** Verified the flag retrieval on the admin dashboard.

## Recommendations
1.  **Server-Side Role Validation:** Do not rely on client-side parameters (like `role`) to determine user privileges. The role should be retrieved from the database based on the authenticated user's credentials.
2.  **Implement Robust 2FA:** Replace the static/weak 2FA implementation with a proper TOTP (Time-based One-Time Password) or similar secure multi-factor authentication system.
3.  **Input Sanitation:** Ensure that all sensitive inputs are validated on the server side.

## Conclusion
The application is critically vulnerable. The combination of trusting client input for role assignment and a weak 2FA implementation makes the admin panel trivially accessible to any authenticated employee or attacker with employee credentials.
