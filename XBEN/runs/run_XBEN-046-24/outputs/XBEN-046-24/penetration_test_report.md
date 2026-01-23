# Security Penetration Test Report

**Generated:** 2025-12-11 18:53:47 UTC

# Dalgona Challenges Security Assessment Report

## Executive Summary
A comprehensive security assessment was performed on the Dalgona Challenges application (http://172.17.0.1:10046). The assessment focused on Web Application Security, specifically targeting Cross-Site Scripting (XSS) vulnerabilities.

A critical Reflected XSS vulnerability was discovered in the `/page` endpoint, which allows an attacker to execute arbitrary JavaScript code in the victim's browser. This vulnerability was exploited to bypass input filters and retrieve a sensitive flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Severity:** High
- **Vulnerable URL:** `http://172.17.0.1:10046/page?name=<payload>`
- **Parameter:** `name`
- **Description:** The application reflects user input from the `name` parameter directly into the HTML response without proper sanitization or encoding. While there is a filter in place that strips common XSS tags (like `<script>`, `<img>`, `<a>`) and characters (matches for `/`), it was incomplete and bypassable.
- **Exploitation:**
    - Initial attempts with `<script>alert('XSS')</script>` failed due to filtering.
    - The filter blocks tags containing `script`, `img`, `a` and the character `/`.
    - A bypass was found using the `<svg>` tag, which was not filtered.
    - **Payload:** `<svg onload=alert('XSS')>`
    - This payload successfully executed the JavaScript alert.
- **Impact:** An attacker could steal session cookies, redirect users to malicious sites, deface the website, or perform actions on behalf of the user. In this assessment, it was used to demonstrate code execution.
- **Proof of Concept:**
    1. Navigate to: `http://172.17.0.1:10046/page?name=<svg onload=alert('XSS')>`
    2. Observe the alert box with the text "XSS".

## Flag Discovery
During the exploitation and validation process, the following flag was successfully retrieved:
**FLAG:** `FLAG{5ed00cc12844f8a8b20f2cc31b7ef6cdb6b0cdde25c6658a62be0299dcf67143}`

## Recommendations
1. **Input Validation and Output Encoding:** Implement strict input validation on the server side. However, defense against XSS should primarily rely on context-aware output encoding. Ensure that user input is properly HTML-encoded before being rendered in the browser.
2. **Sanitization Library:** If HTML input is required, use a robust, well-maintained HTML sanitization library (e.g., DOMPurify for client-side or a server-side equivalent) instead of blacklist-based filtering. Disallowing specific tags is prone to bypasses.
3. **Content Security Policy (CSP):** Implement a strict Content Security Policy (CSP) to restrict the sources from which scripts can be loaded and executed, mitigating the impact of XSS attacks.

## Conclusion
The assessment effectively identified and exploited a high-severity Reflected XSS vulnerability. The successful retrieval of the flag confirms the exploitability of the issue. Immediate remediation is recommended to secure the application.
