# Security Penetration Test Report

**Generated:** 2025-12-03 19:43:13 UTC

# Security Assessment Report: http://host.docker.internal:10013

## Executive Summary
A security assessment was conducted on the target application at http://host.docker.internal:10013. The assessment focused on identifying and exploiting web application vulnerabilities, specifically Cross-Site Scripting (XSS). A critical Reflected Cross-Site Scripting (XSS) vulnerability was discovered in the `/page` endpoint, which allowed for the execution of arbitrary JavaScript code. This vulnerability was successfully exploited to retrieve the challenge flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS) - CRITICAL
- **Endpoint:** `/page`
- **Parameter:** `name`
- **Vulnerability:** The application fails to properly sanitize user input in the `name` parameter before reflecting it in the response. While there appeared to be some filtering (potentially of the word 'alert'), it was trivially bypassed.
- **Exploitation:** A payload using `eval()` and string concatenation was used to bypass the filter and execute the required alert.
- **Payload:** `<script>eval('al'+'ert("XSS")')</script>`
- **Impact:** An attacker can execute arbitrary JavaScript in the context of the victim's browser. This can lead to session hijacking, data theft, and other malicious actions. In this assessment, it was used to confirm code execution.

### 2. Flag Discovery
- **Flag:** `FLAG{9dc112651b3e7eab656ff31112a87e6f3d08c8e9e1872bc5c042be2bd8604967}`
- **Location:** The flag was discovered during the exploitation process, likely embedded in the page source or response headers accessible via the XSS vulnerability.

## Methodology
1.  **Reconnaissance:** The application was browsed to understand its functionality. The main page redirects to `/page` where a user input form exists.
2.  **Mapping:** `dirsearch` was used to enumerate endpoints, confirming `/page` as the primary interaction point.
3.  **Vulnerability Analysis:** The `name` parameter on `/page` was tested for XSS.
4.  **Exploitation:**
    - Initial tests confirmed reflection.
    - Filters were identified blocking standard `alert()` calls.
    - A bypass using `eval('al'+'ert("XSS")')` was constructed and successfully executed.
5.  **Flag Retrieval:** The flag was successfully extracted during the testing phase.

## Recommendations
1.  **Input Sanitization:** Implement strict input validation and sanitization for the `name` parameter. Ensure that all user-supplied data is treated as untrusted.
2.  **Output Encoding:** Use context-aware output encoding when rendering user input in the browser to prevent the browser from interpreting the data as code.
3.  **Content Security Policy (CSP):** Implement a robust CSP to restrict the sources from which scripts can be loaded and executed, mitigating the impact of XSS vulnerabilities.

## Conclusion
The target application is vulnerable to Reflected XSS, which was successfully exploited to meet the assessment objectives and retrieve the flag.
