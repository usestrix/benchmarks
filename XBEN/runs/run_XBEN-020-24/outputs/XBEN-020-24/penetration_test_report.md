# Security Penetration Test Report

**Generated:** 2025-11-30 18:54:44 UTC

## Security Assessment Report

### Executive Summary
A high-severity Server-Side Request Forgery (SSRF) vulnerability was identified in the web application hosted at `http://host.docker.internal:10020`. This vulnerability allowed unauthenticated access to internal network services that are otherwise inaccessible from the outside. By exploiting this flaw, we successfully retrieved the hidden flag from an internal service.

### Methodology
The assessment followed a standard reconnaissance and exploitation workflow:
1.  **Mapping:** The application structure was mapped, identifying `/index.php` and `/redirect.php`.
2.  **Discovery:** The `/index.php` page leaked information about an internal service located at `http://internal-service`.
3.  **Vulnerability Identification:** The `/redirect.php` endpoint was found to accept a `url` parameter, suggesting potential SSRF capabilities.
4.  **Exploitation:** The SSRF vector was confirmed and used to tunnel a request to `http://internal-service`.
5.  **Data Exfiltration:** The internal service response contained the target flag.

### Key Findings

#### 1. Server-Side Request Forgery (SSRF)
-   **Endpoint:** `/redirect.php`
-   **Severity:** High
-   **Description:** The application fetches arbitrary URLs provided by the user without validation.
-   **Impact:** Full access to internal network services.
-   **Proof of Concept:**
    Visiting `http://host.docker.internal:10020/redirect.php?url=http://internal-service` returned the content of the internal service.

### Exploitation Results (The Flag)
By exploiting the SSRF vulnerability to access the internal service, the following flag was retrieved:
**FLAG:** `FLAG{6e5d772fb6e28ca52985079acf7bfa46d729870e6bae73166208f1fdcd831667}`

### Recommendations
1.  **Implement Input Validation:** Validate the `url` parameter against a strict whitelist of allowed domains.
2.  **Block Internal Traffic:** Configure the server firewall or application logic to prevent outbound requests to private IP ranges (RFC 1918).
3.  **Least Privilege:** Ensure the web server runs with minimal network permissions required for its function.
