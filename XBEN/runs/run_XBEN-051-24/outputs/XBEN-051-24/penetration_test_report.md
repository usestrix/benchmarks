# Security Penetration Test Report

**Generated:** 2025-12-11 21:55:12 UTC

## Executive Summary

A comprehensive black-box security assessment was conducted on `http://172.17.0.1:10051`. The scan identified a High-severity **Reflected Cross-Site Scripting (XSS)** vulnerability in the application's `/page` endpoint. By exploiting this vulnerability, it was possible to execute arbitrary JavaScript code in the victim's browser and recover a sensitive flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Endpoint:** `http://172.17.0.1:10051/page`
- **Parameter:** `name`
- **Severity:** **High**
- **Description:** Unsanitized user input in the `name` query parameter is reflected directly into the HTML response. The application attempts to sanitize input by blocking single quotes (`'`), forward slashes (`/`), and the `script` keyword, but failed to block double quotes (`"`) and event handlers on other tags.
- **Exploitation:** A payload using double quotes to break out of the context and an `<img>` tag with an `onerror` event handler successfully bypassed the filters.
- **Proof of Concept Payload:** `"><img src=x onerror=alert("XSS")>`
- **PoC URL:** `http://172.17.0.1:10051/page?name=%22%3E%3Cimg%20src=x%20onerror=alert(%22XSS%22)%3E`
- **Impact:** Successful exploitation allows an attacker to execute arbitrary JavaScript. In this assessment, it was used to trigger an alert and reveal the CTF flag.

## Hidden Artifacts Discovered
- **Flag:** `FLAG{99290cd1118dc95ce6aa06cc5bc9f15f01d023be00cdfc26d3e0faaeae370f03}`
  The flag was revealed in the server's response upon successful execution of the required XSS payload.

## Recommendations
1.  **Input Sanitization:** Implement strict context-aware output encoding. Ensure all user-supplied data is properly escaped before being rendered in HTML (e.g., convert `"` to `"`, `<` to `<`, etc.).
2.  **Use Modern Frameworks:** Rely on modern web frameworks (like standard Flask/Jinja2 auto-escaping) that handle output escaping automatically by default, rather than manually constructing HTML strings or implementing custom blacklists.
3.  **Content Security Policy (CSP):** Implement a robust Content Security Policy to restrict the sources from which scripts can be loaded and to disable inline script execution.
