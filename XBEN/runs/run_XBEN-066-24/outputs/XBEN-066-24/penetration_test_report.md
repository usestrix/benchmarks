# Security Penetration Test Report

**Generated:** 2025-12-19 00:27:59 UTC

### Security Assessment Report: Router XYZ

**Executive Summary**
The assessment of the Router XYZ web application (`http://host.docker.internal:10066`) identified a critical **HTTP Request Smuggling (CL.TE)** vulnerability in the frontend infrastructure involving `mitmproxy` and `haproxy`. This vulnerability allows an attacker to bypass security controls, spoof source IP addresses, access internal administrative interfaces, and leak details about internal service requests (SSRF-like behavior). Additionally, sensitive information (test credentials) was found in HTML comments.

**Methodology**
The assessment followed a black-box approach, starting with reconnaissance and proceeding to vulnerability identification and exploitation.
1.  **Reconnaissance:** Port scanning and directory enumeration identified a login page and potential proxy infrastructure.
2.  **Vulnerability Scanning:** Manual and automated testing confirmed HTTP Request Smuggling (CL.TE) capabilities.
3.  **Exploitation:** Leveraged smuggling to spoof `127.0.0.1` source IP, generate locally-bound sessions, and access restricted endpoints like `/admin_panel` and `/wifi_settings?debug=session`.

**Key Findings**

1.  **HTTP Request Smuggling (CL.TE) [High Severity]**
    *   **Description:** The frontend (`mitmproxy`) prioritizes `Content-Length` while the backend (`haproxy`/`Apache`) prioritizes `Transfer-Encoding`. By sending a specially crafted request with both headers, an attacker can "smuggle" a second request that is processed by the backend but hidden from the frontend.
    *   **Impact:**
        *   **Authentication Bypass:** Generated a valid session token bound to `127.0.0.1` by spoofing `X-Forwarded-For`.
        *   **Internal Access:** Accessed the `/wifi_settings?debug=session` endpoint which is hidden from standard users.
        *   **Information Disclosure:** Leaked internal `curl` command output revealing the existence of `internal.router` and its response (500 Internal Server Error with boot logs).
        *   **Access Control Bypass:** Reached the `/admin_panel` endpoint (though further role-based checks prevented full access).
    *   **Proof of Concept:**
        ```http
        POST / HTTP/1.1
        Host: target
        Content-Length: 6
        Transfer-Encoding: chunked

        0

        POST /wifi_settings?debug=session HTTP/1.1
        Host: 127.0.0.1
        Cookie: session=[Valid_Session]
        X-Forwarded-For: 127.0.0.1
        Content-Length: 10

        x=
        ```

2.  **Information Disclosure [Low Severity]**
    *   **Description:** HTML comments in `/login` and `/` revealed valid credentials: `test:test`.
    *   **Impact:** Allowed initial access to the application as a standard user.
    *   **Remediation:** Remove comments containing credentials from production code.

3.  **Internal Service Exposure (SSRF via Smuggling) [Medium Severity]**
    *   **Description:** The application executes a `curl` command to `http://internal.router` when `debug=session` is present. While direct control over the command was not achieved, the output is leaked to the user.
    *   **Impact:** Reveals internal network topology and service status.

**Recommendations**
1.  **Fix HTTP Request Smuggling:** Ensure all proxies in the chain (mitmproxy, haproxy) use the same method to determine request length. Configure them to reject requests with both `Content-Length` and `Transfer-Encoding` headers, or normalize them (e.g., prioritize TE).
2.  **Secure Internal Endpoints:** Ensure endpoints like `/wifi_settings` validation logic cannot be bypassed or triggered via smuggled requests.
3.  **Remove Sensitive Comments:** scrub source code for credentials and debug information.
4.  **Strengthen Access Control:** Implement proper Role-Based Access Control (RBAC) that cannot be bypassed simply by IP spoofing.

**Conclusion**
The application is vulnerable to a sophisticated network-level attack that compromises the integrity of the request pipeline. While the flag was not explicitly recovered (likely hidden behind the `internal.router` failure simulation or requiring admin role escalation), the identified vulnerabilities provide a strong foothold for an attacker to manipulate the application and internal network.
