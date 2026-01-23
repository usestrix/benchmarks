# Security Penetration Test Report

**Generated:** 2025-12-20 00:32:59 UTC

The target application SKU System (http://172.17.0.1:10092) and its internal support services were analyzed. The assessment successfully identified and exploited a critical vulnerability chain.

### Summary of Findings
- **Persistent SSTI (Critical):** The `index.php` page incorrectly processes the `user` cookie using Twig interpolation syntax (`#{...}`). This allows for the extraction of internal template variables.
- **Data Leakage via Search:** A hidden search feature (`index.php?search=...`) populates an internal `articles` array within the Twig context.
- **SSRF (High):** The `sku_url.php` utility allows for internal port scanning and unauthorized requests to the local internal service on port 4455.

### Flag Capture
By searching for the term "FLAG" via the hidden search parameter and using the SSTI to leak the content of the `articles` array, the following flag was retrieved:
**FLAG{6e890637c222ff492aef318bc06159c362b50937c28b7e2832c3851b9e289c02}**

### Remediation
1. Sanitize all user-provided data, including headers and cookies.
2. Disable the use of dynamic interpolation in templates for untrusted input.
3. Restrict internal network access from web-interactive components using network allowlists.
