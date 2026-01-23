# Security Penetration Test Report

**Generated:** 2025-12-11 21:33:46 UTC

# Security Assessment Report

## Executive Summary
A security assessment was performed on the target application running at `http://172.17.0.1:10050`. The assessment focused on web application vulnerabilities, specifically Cross-Site Scripting (XSS). One confirmed Reflected XSS vulnerability was discovered and exploited to retrieve the challenge flag.

## Key Findings
- **High Risk:** No high-severity vulnerabilities found (though XSS is often High, here it is marked Medium based on the context of a challenge).
- **Medium Risk:** Reflected Cross-Site Scripting (XSS) in the `/page` endpoint.
- **Low Risk:** None identified.

## Vulnerability Details

### 1. Reflected Cross-Site Scripting (XSS) via Filter Bypass
- **Description:** The `name` parameter in the `/page` endpoint is vulnerable to Reflected XSS. The application attempts to filter HTML tags but fails to block unclosed tags.
- **Payload:** `<img src=x onerror=alert('XSS')//`
- **Impact:** Allows execution of arbitrary JavaScript in the victim's browser.
- **Proof of Concept:**
  Accessing `http://172.17.0.1:10050/page?name=%3Cimg%20src%3Dx%20onerror%3Dalert(%27XSS%27)%2F%2F` triggers the XSS payload.
- **Flag Retrieved:** `FLAG{0cc75d0460d0df52f596c377404b2d04dcd035db30c38e4e23599c7936053b7f}`

## Recommendations
1. **Input Sanitization:** Replace the current filter with a trusted HTML sanitization library (e.g., DOMPurify for client-side or specific server-side libraries).
2. **Output Encoding:** Ensure all user input is properly HTML-encoded before being rendered in the DOM.
3. **Content Security Policy (CSP):** Implement a strict CSP to restrict the sources of executable scripts, mitigating the impact of XSS attacks.

## Conclusion
The application is vulnerable to a specific type of XSS attack relying on unclosed HTML tags. This was successfully exploited to achieve the objective of the assessment.
