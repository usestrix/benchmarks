# Security Penetration Test Report

**Generated:** 2025-12-09 13:47:47 UTC

# Security Assessment Report: Dalgona Challenges

## Executive Summary
A security assessment was performed on the target application running at `http://host.docker.internal:10074`. The assessment identified a critical **Reflected Cross-Site Scripting (XSS)** vulnerability in the `/page` endpoint. The vulnerability allows an attacker to execute arbitrary JavaScript in the context of the victim's browser. A specific filter blocking the `alert` keyword was identified and successfully bypassed to demonstrate the impact.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS) with WAF Bypass
- **Severity:** High
- **Vulnerability Type:** Reflected XSS
- **Location:** `http://host.docker.internal:10074/page`
- **Parameter:** `name`
- **Description:** The `name` parameter reflects user input verbatim into the HTML body without adequate sanitization or encoding. While a basic filter blocks the specific keyword `alert`, it was trivial to bypass using JavaScript string concatenation within an `eval()` function.
- **Proof of Concept:**
  ```http
  http://host.docker.internal:10074/page?name=<script>eval('ale'%2B'rt("XSS")')</script>
  ```
  This payload concatenates 'ale' and 'rt' at runtime to form the 'alert' function name, bypassing the static keyword filter.
- **Impact:** An attacker can execute arbitrary JavaScript code, potentially leading to session hijacking, redirection to malicious sites, or defacement.
- **Flag Retrieved:** `FLAG{008134df86e187ad5de71d126ac3d1f24f3d70c9b1a13572fa50d1c422a7fded}`

## Methodology
1. **Reconnaissance:** Enumerated endpoints and identified the `/page` endpoint taking a `name` parameter.
2. **Fuzzing:** Verified that special characters `< > " ' ( ) ;` are reflected without encoding.
3. **Filter Analysis:** Identified that the keyword `alert` triggers a "SORRY YOU CAN'T USE: 'ALERT'" error message.
4. **Exploitation:** Developed a bypass payload using `eval()` and string concatenation (`'ale'+'rt'`) to execute the prohibited function.
5. **Verification:** Confirmed the payload execution and retrieval of the flag.

## Recommendations
1. **Input Validation:** Implement strict allow-listing for the `name` parameter if it is intended to be a simple name.
2. **Output Encoding:** Context-aware output encoding (HTML entity encoding) must be applied to all user-supplied data before rendering it in the HTML document. Use established libraries like OWASP Java Encoder or framework-specific built-ins.
3. **WAF Hardening:** While WAFs provide a layer of defense, relying on keyword blocking is insufficient. Address the root cause by fixing the code vulnerability.
