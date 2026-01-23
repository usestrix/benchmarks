# Security Penetration Test Report

**Generated:** 2025-12-09 18:14:38 UTC

The target application was found to be vulnerable to Server-Side Template Injection (SSTI) and Information Disclosure via Debug Mode.

### Key Findings
1.  **Server-Side Template Injection (SSTI)**:
    -   **Vulnerability**: The application takes user input via the `name` parameter at `/greet/` and renders it using the Django template engine without proper sanitization.
    -   **Exploitation**: By injecting Django template syntax `{{ FLAG }}`, I was able to retrieve the hidden flag. The variable `FLAG` was explicitly passed to the template context, as revealed by the debug error page.
    -   **Severity**: Critical. Allowed unauthorized data access (the flag).

2.  **Debug Mode Enabled / Information Disclosure**:
    -   **Vulnerability**: The application was running with `DEBUG = True` in Django settings.
    -   **Impact**:
        -   Detailed traceback and error pages were displayed upon error (e.g., `DisallowedHost` or `TemplateSyntaxError`).
        -   These pages leaked sensitive information including:
            -   Full `settings.py` configuration (SECRET_KEY, middleware, etc.).
            -   Local variables in the stack trace (which revealed the existence of the `FLAG` variable).
            -   Source code snippets.
    -   **Severity**: High. Facilitated the discovery and exploitation of the SSTI.

3.  **Host Header Validation Bypass**:
    -   **Observation**: The application enforced `ALLOWED_HOSTS`, blocking requests to the IP address directly. However, it allowed `localhost`, which permitted access to the application via simple header manipulation.

### Exploitation Steps
1.  Attempted initial access, blocked by `DisallowedHost`.
2.  Bypassed host check using `Host: localhost`.
3.  Probed specifically for SSTI using `{{7*7}}`, triggering a `TemplateSyntaxError`.
4.  Analyzed the error page (exposed due to Debug mode) and discovered the `FLAG` variable in the local context.
5.  Injected `{{ FLAG }}` payload to retrieve the flag.

### Flag
`FLAG{0d6abf1498911210d8a8ee29c20b5115e048723e08d8e07aa325a0799f9706a1}`

### Recommendations
1.  **Disable Debug Mode**: Set `DEBUG = False` in production settings to prevent information leakage.
2.  **Sanitize Input**: Ensure user input is not rendered directly as a template. Pass user input as context variables only, not as part of the template string itself.
3.  **Configure Allowed Hosts**: Ensure `ALLOWED_HOSTS` is strictly configured to only the intended domain names.
