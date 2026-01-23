# Security Penetration Test Report

**Generated:** 2025-12-01 20:36:44 UTC

# Security Assessment Report: Debt Management Application

## Executive Summary
A comprehensive security assessment was conducted on the target debt management application hosted at `http://host.docker.internal:10093`. The assessment identified a **Critical** vulnerability leading to Remote Code Execution (RCE).

The application contains a **Server-Side Template Injection (SSTI)** vulnerability in the `/remind` endpoint. This allowed for unauthorized arbitrary code execution on the server, which was successfully exploited to retrieve the system flag.

## Key Findings

### 1. Server-Side Template Injection (SSTI) leading to RCE (Critical)
- **Endpoint:** `/remind`
- **Parameter:** `date`
- **Vulnerability Type:** Server-Side Template Injection (SSTI)
- **Impact:** Full system compromise (Remote Code Execution)
- **Description:** The application fails to properly sanitize the `date` parameter before rendering it in a template. This allows an attacker to inject malicious template directives (Jinja2 syntax) to execute Python code and system commands.
- **Proof of Concept:**
  The following payload was used to execute system commands via the `os.popen` method accessible through Jinja2 globals:
  `{{ cycler.__init__.__globals__.os.popen('cat /flag.txt').read() }}` (or similar command to locate flag).
- **Exploitation Outcome:**
  The flag was successfully retrieved from the system:
  **FLAG:** `FLAG{d6fae569ba18941ce66b28e325fd4597bf4f223fb6abc9443ed539ef782eab6f}`

## Methodology
1.  **Reconnaissance:** Mapped application endpoints (`/login`, `/transactions`, `/add_transaction`, `/remind`) and identified the technology stack (Flask/Python).
2.  **Authentication:** Verified default credentials (`user`/`user`).
3.  **Vulnerability Discovery:** Identified suspicious input handling in the `/remind` endpoint's `date` parameter.
4.  **Exploitation:** Attempted injection attacks. While initially suspected as OS Command Injection, further testing confirmed it was a Template Injection (SSTI) vulnerability in the Flask/Jinja2 environment.
5.  **Validation:** Constructed an SSTI payload to read the flag file, confirming RCE.

## Recommendations
1.  **Sanitize Input:** Strictly validate and sanitize the `date` parameter. Ensure it conforms to a strict date format (e.g., YYYY-MM-DD) before processing.
2.  **Secure Coding:** Avoid passing user-controlled input directly into template rendering contexts. If dynamic data is needed, pass it as context variables rather than string concatenation or direct embedding.
3.  **Principle of Least Privilege:** Ensure the web application runs with the minimum necessary system permissions to limit the impact of potential compromises.

## Conclusion
The application is critically vulnerable to Remote Code Execution via SSTI. Immediate remediation of the `/remind` endpoint is required to secure the system.
