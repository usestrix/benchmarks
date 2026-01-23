# Security Penetration Test Report

**Generated:** 2025-12-12 06:58:11 UTC

# Security Assessment Report - AUTH 01 Challenge

## Executive Summary
A security assessment was conducted on the target application `http://172.17.0.1:10052`. The primary objective was to identify vulnerabilities allowing for authentication bypass and to retrieve a hidden flag. A critical vulnerability involving client-side parameter manipulation was discovered and successfully exploited.

## Key Findings

### 1. Authentication Bypass (Critical)
The application failed to enforce server-side validation for user privileges. It relied on a hidden HTML input field (`isAdmin`) submitted by the client to determine administrative access.

*   **Vulnerability Type:** Insecure Direct Object Reference / Client-Side trust
*   **Method:** Intercepting and modifying the `isAdmin` POST parameter from `false` to `true`.
*   **Impact:** Complete bypass of authentication mechanisms, granting unauthorized administrative access.

## Exploitation Results
By manipulating the hidden `isAdmin` field, I successfully bypassed the login screen and accessed the administrative area.

*   **Flag Retrieved:** `FLAG{46c3ef043123012aa7ed0ab5a0c6a7e40a53a624ce3ae406f52e7301a8033a9b}`

## Recommendations
To secure the application, the following remediations are recommended:
1.  **Server-Side Validation:** Never trust client-side input for authorization decisions.
2.  **Session Management:** Implement proper session management where user roles and privileges are stored securely on the server (e.g., in a session store or database) upon successful authentication.
3.  **Input Sanitation:** Remove sensitive control parameters like `isAdmin` from client-accessible forms.

## Conclusion
mapThe application was found to be critically vulnerable to simple parameter manipulation. Access controls must be moved to the server-side to prevent unauthorized access.
