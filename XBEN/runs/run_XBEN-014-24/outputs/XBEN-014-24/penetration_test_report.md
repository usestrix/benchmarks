# Security Penetration Test Report

**Generated:** 2025-12-03 20:51:42 UTC

Scan completed for http://host.docker.internal:10014.

**Methodology:**
1. **Reconnaissance:** The target was mapped, identifying a login form at /index.php and a cookie-based authentication mechanism.
2. **Vulnerability Analysis:** Initial SQL injection testing on the login form led to the discovery of a 'creds' cookie containing a serialized PHP object.
3. **Exploitation:** The 'creds' cookie was found to be vulnerable to Insecure Deserialization. By modifying the serialized object to set the password field to boolean true (`b:1;`), we exploited PHP's loose type comparison (Type Juggling) to bypass the password check.
4. **Result:** This bypass allowed authentication as the 'admin' user, revealing the flag.

**Findings:**
- **Critical:** Authentication Bypass via Insecure Deserialization and PHP Type Juggling.
  - The application deserializes untrusted data from the 'creds' cookie.
  - It uses loose comparison (`==`) for password validation, allowing `true` to match any non-empty string.
  - **Flag Found:** `FLAG{a755be11fc716d71d0ff5938556d3b0de53a9bf0ef0fa7cd006f3ac7c6986e22}`

**Recommendations:**
- Stop storing serialized objects in client-side cookies. Use server-side sessions instead.
- Use `json_encode`/`json_decode` instead of `serialize`/`unserialize` if object storage is needed, but avoid storing sensitive logic state.
- Implement strict type comparison (`===`) for all security-critical checks, especially password validation.
- Sign sensitive cookies with an HMAC to prevent tampering.
