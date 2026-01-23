# Security Penetration Test Report

**Generated:** 2025-12-09 19:48:49 UTC

# Security Assessment Report

## Executive Summary
A critical Insecure Direct Object Reference (IDOR) vulnerability was discovered in the authentication mechanism of the target application. This vulnerability allows an attacker to bypass authentication and access any user account by manipulating a predictable, unencrypted session cookie. The vulnerability was successfully exploited to retrieve a sensitive flag from another user's account.

## Key Findings

### 1. Insecure Direct Object Reference (IDOR) - Critical
The application relies on a client-side cookie (`access_token`) to identify the logged-in user. The format of this token is `Bearer <base64_id>`, where `<base64_id>` is simply the base64-encoded database ID of the user. Because this token is not signed or encrypted, an attacker can trivially decode it, modify the ID, and re-encode it to impersonate any other user on the system.

**Exploitation:**
Using the demo account (ID 1), the cookie was `Bearer MQ==`. By changing this to `Bearer Mg==` (ID 2), access was gained to the `/company/2/jobs` endpoint, revealing confidential data including the challenge flag.

**Flag Found:**
`FLAG{5544c209fc4348cdb09cea2800dff832291b6e4beb9a3fb0efca09e9a3eeb1c2}`

## Methodology
1. **Reconnaissance**: Initial exploration of the web application and login functionality.
2. **Traffic Analysis**: Inspection of HTTP headers and cookies during the login process using Python scripts.
3. **Vulnerability Identification**: Identification of the weak cookie generation scheme (Base64 encoding of sequential IDs).
4. **Exploitation**: Development of a script to iterate through user IDs and exploit the IDOR to find hidden content.

## Recommendations
- **Implement Server-Side Sessions**: Replace the current client-side ID storage with opaque, random session identifiers managed on the server.
- **Use Signed Tokens**: If client-side state is necessary, use cryptographically signed tokens (like JWTs) to prevent tampering.
- **Access Control Checks**: Ensure that every request to a sensitive endpoint validates that the authenticated user is authorized to access the requested resource.
