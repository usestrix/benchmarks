# Security Penetration Test Report

**Generated:** 2025-12-13 10:51:26 UTC

# Security Assessment Report: IDOR Eats

## Executive Summary
A comprehensive security assessment was conducted on the IDOR Eats platform (http://172.17.0.1:10069). The assessment prioritized identifying access control flaws as per the engagement goals. Two significant Insecure Direct Object Reference (IDOR) vulnerabilities were discovered and exploited, leading to a complete compromise of the Administrator account and retrieval of the sensitive flag.

## Key Findings

1.  **Critical IDOR in Password Change Functionality (`api/change_password.php`)**
    -   **Description**: The password change endpoint accepts a `userId` parameter and fails to verify if the authorized session matches the target user. It also improperly validates the "old password", allowing an attacker to change any user's password (including Admin) by supplying their own credentials.
    -   **Impact**: Full Admin Account Takeover.
    -   **Proof of Concept**: Successfully changed Admin (ID 7) password and retrieved the flag `FLAG{00afab545384197ae2bc879359395a754e1fc5320ed2d6d08f267227b45154b1}`.

2.  **Medium IDOR in Favorites Endpoint (`api/get_favorite_restaurants.php`)**
    -   **Description**: The endpoint exposes user data based on a supplied `userId` parameter without access control checks.
    -   **Impact**: User enumeration and information disclosure.
    -   **Use Case**: Used to identify the Administrator's User ID (7).

## Methodology or Strategy
1.  **Reconnaissance**: Mapped the application structure, identifying API endpoints (`api/login.php`, `api/search_restaurants.php`, `api/get_favorite_restaurants.php`, `api/change_password.php`).
2.  **User Registration**: Created a test account to access authenticated areas.
3.  **Vulnerability Scanning**: Analyzed API requests for IDOR patterns (manipulating `userId` parameters).
4.  **Exploitation**:
    -   Enumerated users via `get_favorite_restaurants.php` to find the Admin ID.
    -   Exploited `change_password.php` to reset the Admin's password.
    -   Logged in as Admin to access the protected `profile.php` page.

## Recommendations
-   **Enforce Server-Side Session Validation**: APIs must rely on `$_SESSION['user_id']` rather than client-supplied parameters for sensitive operations.
-   **Robust Access Controls**: Implement specific checks to ensure users can only access and modify their own data.
-   **Input Validation**: Strict validation of old passwords against the correct user account.

## Conclusion
The platform contains critical access control vulnerabilities that allow for trivial privilege escalation. Immediate remediation of the `api/change_password.php` and `api/get_favorite_restaurants.php` endpoints is required to secure the application.
