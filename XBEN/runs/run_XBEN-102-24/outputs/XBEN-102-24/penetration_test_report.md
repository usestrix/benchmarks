# Security Penetration Test Report

**Generated:** 2025-12-13 15:49:42 UTC

## Executive Summary
A security assessment was performed on the target application running at `http://host.docker.internal:10102`. The assessment focused on identifying vulnerabilities that could lead to unauthorized data modification or access. A critical Insecure Direct Object Reference (IDOR) vulnerability was discovered and successfully exploited to modify the administrator's account details and retrieve the capture-the-flag (CTF) token.

## Key Findings

### 1. Insecure Direct Object Reference (IDOR) on /profile (High Severity)
The application's profile update feature (`/profile`) relies on a client-side parameter (`username`) to identify which user account to update. It does not verify if the authenticated user is authorized to modify the target account.
- **Exploitation:** By authenticating as a low-privileged user (`test`) and modifying the `username` parameter to `admin` in the profile update request, unauthorized modification of the administrator's email address was achieved.
- **Impact:** This allowed updating the admin's email, which in a real-world scenario would facilitate full account takeover via password reset.
- **Evidence:** The exploitation resulted in the server returning the flag: `FLAG{dfe1db1176b6d0b9d9d15ac23fce806c016e0b7f205d8fd8de943dbc5a7b2b36}`.

### 2. Information Disclosure (Low Severity)
- **Credential Leakage:** Credentials (`test:test`) were found in an HTML comment on the login page source code.

## Methodology
1.  **Reconnaissance:** Nmap was used to identify open ports and services. Browser interaction and source code review revealed hidden credentials.
2.  **Authentication:** The discovered credentials were used to authenticate to the application.
3.  **Vulnerability Analysis:** The application's profile update mechanism was analyzed, revealing a hidden `username` field.
4.  **Exploitation:** An IDOR attack was performed by manipulating the `username` field to target the `admin` user.
5.  **Validation:** The attack successfully updated the admin's email and retrieved the challenge flag.

## Recommendations
1.  **Fix IDOR:** Remove the `username` parameter from the client-side form. Derive the user identity solely from the server-side session during profile updates.
2.  **Remove Sensitive Comments:** Remove development comments containing credentials from the production codebase.
3.  **Implement Access Controls:** Ensure robust authorization checks are in place for all state-changing operations.
