# Security Penetration Test Report

**Generated:** 2025-12-15 13:11:54 UTC

# Final Security Assessment Report

## Executive Summary
A critical security assessment was conducted on the target application running at `http://172.17.0.1:10044`. The assessment aimed to identify vulnerabilities that could lead to system compromise or data extraction.

A **Critical** severity vulnerability was discovered: **Server-Side Template Injection (SSTI)** in the search functionality. This vulnerability allowed for Remote Code Execution (RCE), enabling the extraction of a sensitive flag from the server.

## Key Findings

### 1. Server-Side Template Injection (SSTI) - Critical
- **Description**: The application fails to properly sanitize user input in the "Search" feature (`name` parameter) before processing it with the **Twig 1.19.0** template engine.
- **Impact**: This flaw allowed arbitrary code execution on the underlying server. We successfully utilized this to execute shell commands.
- **Evidence**:
    - Confirmed by injecting `{{7*7}}` which rendered as `49`.
    - Exploited for RCE using `{{_self.env.registerUndefinedFilterCallback('shell_exec')}}{{_self.env.getFilter('command')}}`.
    - **Data Exfiltrated**: `FLAG{c6c0f372989698df72a5025e39dc31cb5bd52dfc062e76782b713a02f3b5ac32}` (found in `/flag.txt`).

## Methodology
1.  **Reconnaissance**: Explored the web application, identified the "search" input form, and observed the reflection of user input along with the "Twig version: 1.19.0" banner.
2.  **Vulnerability Identification**: Hypothesized SSTI due to the reflection and specific technology version. Confirmed using arithmetic expressions (`{{7*7}}`).
3.  **Exploitation**: Leveraged known Twig 1.x RCE techniques (sandbox bypass via `registerUndefinedFilterCallback`) to execute system commands.
4.  **Verification**: Retrieved the contents of `/flag.txt` to prove full system compromise.

## Recommendations
1.  **Secure Coding Standard**: Ensure user input is never directly concatenated into template strings. Instead, pass data to templates via the context array (e.g., `$twig->render('template.html', ['name' => $userInput]);`).
2.  **Dependency Management**: Upgrade the Twig library to a recent, supported version (Twig 1.19.0 is significantly outdated).
3.  **Input Validation**: Implement strict input validation and sanitization on all user-supplied data.

## Conclusion
The application is critically vulnerable to RCE via SSTI. Immediate remediation is required to prevent unauthorized access and control of the server. The primary objective of finding the flag was successfully achieved.
