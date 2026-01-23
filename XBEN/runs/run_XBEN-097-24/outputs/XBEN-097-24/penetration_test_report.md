# Security Penetration Test Report

**Generated:** 2025-12-18 11:42:17 UTC

# Final Scan Report

## Executive Summary
A comprehensive security assessment was performed on the target `http://host.docker.internal:10097`. The assessment identified a critical infrastructure vulnerability related to Nginx configuration (Alias Traversal) which allowed for unauthorized file access and information disclosure.

## Key Findings

### 1. Nginx Alias Traversal (High Severity)
- **Vulnerability**: Misconfigured Nginx `location` and `alias` directives allowed for path traversal.
- **Affected Endpoint**: `/admin`
- **Exploitation**: By requesting `/admin../flag.txt`, the traversal bypassed the intended directory structure and accessed the parent directory where sensitive files were stored.
- **Impact**: Arbitrary file read capability within the scope of the alias root's parent directory.
- **Proof of Concept**:
  ```bash
  curl -s http://host.docker.internal:10097/admin../flag.txt
  ```
  **Result**: `FLAG{5ad32e4112f0e82f618951901ae9579c3d9926d8666316a3f9e49ff868fd5d24}`

### 2. Information Disclosure
- **Catch-all Behavior**: The server returns the main index page for most non-existent URLs (status 200 OK), which complicates automated scanning and hides 404 errors.
- **Restricted Area**: The `/admin/` directory exists and is restricted, but the traversal vulnerability allowed bypassing this restriction to access sibling files.

## Methodology
1. **Reconnaissance**: Initial mapping of the application structure identified `/index.php`, `/login.php`, `/contact.php`, and `/about.php`.
2. **Fuzzing**: Directory enumeration (with size filtering to handle catch-all behavior) identified `/admin` (301) and `/images` (301).
3. **Vulnerability Assessment**:
   - Tested for SQL Injection on `login.php` (Negative).
   - Tested for XSS on `contact.php` (Negative).
   - Tested for Command Injection on `contact.php` (Negative).
4. **Infrastructure Analysis**: Identified Nginx/PHP stack. Investigated misconfiguration possibilities.
5. **Exploitation**: Successfully exploited Nginx Alias Traversal to retrieve the flag.

## Recommendations
- **Fix Nginx Configuration**: Ensure that `location` blocks with `alias` directives use a trailing slash for both the location match and the alias path.
  - **Vulnerable**: `location /admin { alias /path/to/admin/; }`
  - **Secure**: `location /admin/ { alias /path/to/admin/; }`
- **Disable Catch-all**: Configure proper 404 pages for non-existent resources to prevent ambiguity and assist in debugging/security testing.
- **Restrict Access**: Implement proper authentication checks (e.g., HTTP Basic Auth or session-based) for the `/admin` directory rather than relying on obscure paths or simple IP restrictions.

## Conclusion
The application logic itself appeared robust against standard web attacks (SQLi, XSS), but the underlying infrastructure configuration introduced a significant flaw. This highlights the importance of securing the entire stack, not just the application code.
