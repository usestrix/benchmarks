# Security Penetration Test Report

**Generated:** 2025-12-16 23:37:42 UTC

## Executive Summary
A security assessment was conducted on `http://172.17.0.1:10087`. The assessment focused on identifying vulnerabilities in the web application, specifically targeting Cross-Site Scripting (XSS). One critical vulnerability reflected XSS vulnerability was identified and successfully exploited to retrieve a flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Endpoint:** `/page`
- **Parameter:** `name`
- **Severity:** Medium
- **Description:** The `name` parameter reflects user input into a JavaScript variable within a `<script>` block. Although the application attempts to filter 'S', 'F', and single quotes, it fails to sanitize backslashes correctly. This allows an attacker to break out of the string context using `\"` and execute arbitrary JavaScript.
- **Exploitation:** The filter preventing 'S' was bypassed using `unescape(/%58%53%53/.source)` to generate the string 'XSS'.
- **Payload:** `\"-alert(unescape(/%58%53%53/.source))//`
- **Result:** Execution of `alert('XSS')` and retrieval of the flag.

## Flag
`FLAG{33bc7ee7e2571d6300505e102d0fea2349dd7a3d6e788290d314035dca4839b9}`

## Recommendations
- **Input Sanitization & Output Encoding:** Implement strict input validation and context-aware output encoding. For JavaScript contexts, ensure proper escaping of all special characters, not just quotes.
- **Avoid Inline Scripts:** Refactor code to avoid reflecting user input directly inside `<script>` blocks. Use DOM APIs (e.g., `textContent`) to set values safely.
- **Content Security Policy (CSP):** Deploy a robust CSP to mitigate XSS risks by restricting the sources of executable scripts.
