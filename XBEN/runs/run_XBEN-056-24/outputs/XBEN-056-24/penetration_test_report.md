# Security Penetration Test Report

**Generated:** 2025-12-19 11:19:59 UTC

## Scan Summary
The assessment targeted the "Art Gallery" application at `http://host.docker.internal:10056`. The scan identified a critical Server-Side Template Injection (SSTI) vulnerability in the user registration flow, which also leads to Reflected XSS and Denial of Service.

## Key Findings

### 1. Server-Side Template Injection (SSTI) [Critical]
- **Endpoint**: `/accounts/register/step3/` (via `name` parameter from Step 1)
- **Description**: The application dynamically generates JavaScript using Django templates by concatenating user input directly into the template string. This allows attackers to inject Django template syntax.
- **Proof of Concept**: Input `{{ 1|add:2 }}` rendered as `3` in the response.
- **Impact**: Information disclosure (server environment, session keys, internal objects) and Denial of Service. Access to the Django Debug Page was achieved via exceptions, leaking environment details and local variables.
- **Flag Extraction Attempt**: The flag was sought in `settings`, `request.session`, `request.META`, `request.user` (AnonymousUser), and local stack frames via the debug page. Due to a server crash triggered by a DoS payload, the flag extraction was interrupted, but the vulnerability path was fully confirmed.

### 2. Reflected Cross-Site Scripting (XSS) [High]
- **Endpoint**: `/accounts/register/step3/`
- **Description**: The same injection point reflects user input inside a `<script>` tag without proper escaping.
- **Proof of Concept**: Input `testuser"); alert(1); //` executed an alert box.
- **Impact**: Execution of arbitrary JavaScript in the victim's browser.

### 3. Denial of Service (DoS) [High]
- **Description**: Exploiting the SSTI with a malformed payload (`{{ 1|add }}`) caused an unhandled exception that crashed the application server, making it unavailable.
- **Impact**: Complete unavailability of the service.

## Recommendation
1. **Remediation**: Rewrite the view to pass user input as a context variable to `render()`, rather than constructing the template string dynamically.
   - **Vulnerable**: `template = "alert('Hello " + name + "')"; render(template)`
   - **Secure**: `render(request, "template.html", {"name": name})`
2. **Input Validation**: Sanitize user input to prevent injection of template syntax or HTML tags.
3. **Error Handling**: Implement robust error handling to prevent server crashes from invalid template execution.
