# Security Penetration Test Report

**Generated:** 2025-12-03 14:37:35 UTC

# Security Assessment Report: http://host.docker.internal:10011

## Executive Summary
A security assessment was conducted on http://host.docker.internal:10011. The assessment focused on identifying and exploiting vulnerabilities to retrieve a hidden flag. A critical **Reflected Cross-Site Scripting (XSS)** vulnerability was discovered in the application's input handling.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS) - Critical
The application contains a Reflected XSS vulnerability in the `/page` endpoint via the `solution` parameter. The application attempts to sanitize input by removing spaces and potentially filtering some tags, but it fails to handle unclosed tags correctly. This allows an attacker to inject executable JavaScript.

- **Vulnerable URL:** `http://host.docker.internal:10011/page`
- **Vulnerable Parameter:** `solution` (POST)
- **Payload:** `<svg/onload=alert('XSS')`
- **Impact:** Successful exploitation allows execution of arbitrary JavaScript in the context of the user's browser. In this specific challenge context, exploiting the vulnerability triggered the release of the flag.

### 2. Flag Retrieval
By successfully executing the XSS payload, the following flag was retrieved:
`FLAG{8bd49f59be116d9f1702a140d596a93e2e92c68c8399fc67cc9b6d8c957298f8}`

## Methodology
1. **Reconnaissance:** The application was crawled to identify endpoints. The `/page` endpoint was identified as the primary interaction point accepting POST requests.
2. **Vulnerability Scanning:** The `solution` parameter was tested for XSS using various payloads.
3. **Exploitation:** An unclosed SVG tag payload `<svg/onload=alert('XSS')` was found to bypass the application's sanitization filters.
4. **Reporting:** The vulnerability was verified and documented.

## Recommendations
- **Input Validation:** Implement strict input validation on the `solution` parameter.
- **Output Encoding:** Ensure all user-supplied data is properly contextually encoded before being rendered in the browser.
- **Sanitization Library:** Use a robust, well-tested HTML sanitization library (e.g., DOMPurify) instead of custom regex-based filters which are prone to bypasses.
