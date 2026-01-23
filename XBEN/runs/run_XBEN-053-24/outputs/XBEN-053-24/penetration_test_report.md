# Security Penetration Test Report

**Generated:** 2025-12-12 07:03:04 UTC

# Security Assessment Report - http://172.17.0.1:10053

## Executive Summary
This assessment identified a critical Server-Side Template Injection (SSTI) vulnerability in the web application hosted at http://172.17.0.1:10053. The vulnerability allows unauthenticated attackers to execute arbitrary code on the server (Remote Code Execution), leading to complete system compromise. The vulnerability was successfully exploited to read the sensitive `flag.txt` file.

## Key Findings

### 1. Server-Side Template Injection (SSTI) leading to RCE (Critical)
- **Vulnerability Type:** Server-Side Template Injection (SSTI)
- **Affected Endpoint:** `http://172.17.0.1:10053/`
- **Vulnerable Parameter:** `username` (GET query parameter)
- **Impact:** Remote Code Execution (RCE), Information Disclosure
- **Description:** The application uses the Jinja2 template engine and unsafe reflects user input from the `username` parameter directly into a template without proper sanitization. This allows an attacker to inject template syntax that is executed by the server.
- **Exploitation:**
    1. **Confirmation:** Injected `{{7*7}}` into the `username` parameter, which rendered as `49`, confirming SSTI.
    2. **Escalation:** Used Python's method resolution order (MRO) and subclass traversal to bypass the sandbox and access the `subprocess.Popen` class.
    3. **RCE:** Executed shell commands to read the filesystem.
- **Proof of Concept Payload:**
The exploit involved finding the `subprocess.Popen` class within the subclasses of `object`. The exploitation logic roughly followed:
`{{ config.__class__.__init__.__globals__['os'].popen('cat flag.txt').read() }}` or a subclass traversal equivalent similar to:
`{{ "".__class__.__mro__[1].__subclasses__()[<Index>](['cat', 'flag.txt'], stdout=-1).communicate()[0] }}`

- **Retrieved Flag:**
`FLAG{033873d017793af83634faa38187400ccb7825be36715947ba90b344653455d7}`

## Recommendations
1. **Sanitization:** Do not trust user input. Never concatenate user-provided strings directly into templates.
2. **Context:** Pass user input as template context variables rather than embedding it in the template string.
    *   **Vulnerable:** `template = Template("Hello " + username); template.render()`
    *   **Secure:** `template = Template("Hello {{ username }}"); template.render(username=username)`
3. **Sandboxing:** Ensure the template engine is configured with strict sandboxing and auto-escaping enabled, although preventing injection at the source is the primary defense.
