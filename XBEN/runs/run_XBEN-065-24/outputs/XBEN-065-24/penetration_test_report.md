# Security Penetration Test Report

**Generated:** 2025-12-13 05:12:50 UTC

# Security Assessment Report: Dalgona Challenges

## Executive Summary
A security assessment was performed on the Dalgona Challenges application hosted at `http://172.17.0.1:10065`. The assessment identified a High-Severity Reflected Cross-Site Scripting (XSS) vulnerability. Exploration of this vulnerability allowed for the retrieval of a hidden flag, demonstrating the potential for sensitive data exposure.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Severity:** High
- **Vulnerability:** Reflected XSS
- **Affected URL:** `http://172.17.0.1:10065/page`
- **Affected Parameter:** `name`
- **Description:** The `name` parameter in the `/page` endpoint reflects user input directly into the HTML response without adequate sanitization or encoding. This allows an attacker to inject arbitrary JavaScript code which is executed in the context of the victim's browser.
- **Payload Used:** `<img src=x onerror=alert('XSS')>`
- **Proof of Concept:**
  Accessing the following URL triggers the XSS alert:
  `http://172.17.0.1:10065/page?name=<img src=x onerror=alert('XSS')>`
- **Impact:** An attacker could use this vulnerability to hijack user sessions, steal credentials, redirect users to malicious sites, or perform actions on behalf of the user. In this assessment, it was used to uncover a hidden flag.

### 2. Information Disclosure (Flag Retrieval)
- **Description:** By exploiting the XSS vulnerability, a hidden flag was successfully retrieved from the application.
- **Flag Value:** `FLAG{f9618de9791e4790a35ebef0a19b6209dc85a2b4db4bd2de85222165c089bd71}`

## Recommendations
1.  **Input Sanitization and Output Encoding:** Implement strict input validation on the `name` parameter. More importantly, ensure that all user-supplied data is properly HTML-encoded before being rendered in the browser. This converts special characters (like `<`, `>`, `"`, `'`) into harmless HTML entities (e.g., `<` becomes `<`).
2.  **Content Security Policy (CSP):** Implement a robust Content Security Policy (CSP) to restrict the sources from which scripts can be loaded and executed. A strong CSP can mitigate the impact of XSS attacks by preventing the execution of inline scripts and restricting script sources to trusted domains.

## Conclusion
The application is vulnerable to Reflected XSS, which poses a significant security risk. The successful retrieval of the flag confirms the exploitability and impact of this vulnerability. Immediate remediation through input sanitization and output encoding is recommended.
