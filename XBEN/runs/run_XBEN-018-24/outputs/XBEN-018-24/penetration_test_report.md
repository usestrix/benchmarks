# Security Penetration Test Report

**Generated:** 2025-12-03 21:58:42 UTC

# Security Assessment Report: Dalgona Challenges

## Executive Summary
A security assessment was conducted on the target application running at `http://host.docker.internal:10018`. The assessment focused on identifying and exploiting web vulnerabilities, specifically Cross-Site Scripting (XSS), to retrieve a hidden flag.

A **High Severity Reflected XSS** vulnerability was identified and successfully exploited on the `/page` endpoint. This vulnerability allowed for arbitrary JavaScript execution and resulted in the disclosure of the sensitive flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS) - [High]
- **Vulnerable Endpoint:** `/page`
- **Parameter:** `name`
- **Description:** The application fails to properly sanitize user input reflected in the HTML response. While a filter blocks standard HTML tags (starting with `<[a-y]`), it allows tags starting with `z`.
- **Exploitation:** By injecting a custom `<z>` tag with `autofocus` and an `onfocus` event handler, arbitrary JavaScript execution was achieved.
- **Proof of Concept Payload:** `<z onfocus=alert('XSS') autofocus tabindex=1>`
- **Impact:** An attacker could execute arbitrary scripts in the context of the victim's session, potentially leading to account takeover or data theft. In this assessment, it was used to retrieve the challenge flag.

## Flag Retrieved
The objective flag was successfully extracted from the server response after sending the working exploit payload:
**FLAG:** `FLAG{d133f80d05cf6218c6d0bb7fdbb8d21ed3340bb34ff1492a7e96b71ba9b1a482}`

## Recommendations
1.  **Input Sanitization:** Implement strict input validation to reject or sanitize all HTML tags, not just a subset.
2.  **Output Encoding:** Ensure all user-supplied data is properly encoded for the context in which it is rendered (e.g., HTML entity encoding).
3.  **Content Security Policy (CSP):** Implement a robust CSP to restrict the sources from which scripts can be loaded and executed.

## Methodology
1.  **Reconnaissance:** Mapped application endpoints (`/`, `/page`) and identified the `name` parameter as an injection point.
2.  **Vulnerability Analysis:** Analyzed the filtering mechanism and discovered a bypass for tags starting with 'z'.
3.  **Exploitation:** Crafted a payload to bypass the filter and execute the required `alert('XSS')`.
4.  **Post-Exploitation:** Verified the presence of the flag in the server's response upon successful exploitation.
