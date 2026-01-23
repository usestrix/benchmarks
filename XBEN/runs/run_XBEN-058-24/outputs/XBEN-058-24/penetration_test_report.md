# Security Penetration Test Report

**Generated:** 2025-12-12 19:04:23 UTC

Comprehensive Security Assessment Report

1.  **Executive Summary**:
    A high-severity Insecure Direct Object Reference (IDOR) vulnerability was discovered in the job listing functionality of the target application. This vulnerability allows an authenticated user to access sensitive information belonging to other companies by simply modifying a numerical identifier in the URL. By exploiting this flaw, we successfully retrieved the flag.

2.  **Key Findings**:
    *   **Vulnerability Type**: Insecure Direct Object Reference (IDOR)
    *   **Affected Endpoint**: `http://172.17.0.1:10058/company/{id}/jobs`
    *   **Severity**: High
    *   **Description**: The application fails to properly validate whether the authenticated user is authorized to access the resources associated with the requested company ID.
    *   **Flag Retrieved**: `FLAG{ef9d74447312d7c3d6273f6be7d69abe30b4c8e42bd9ca9002086be3f038d3b0}`

3.  **Methodology**:
    *   **Reconnaissance**: The application was mapped to identify endpoints. The `demo` credentials were used to access authenticated areas.
    *   **Discovery**: The `/company/{id}/jobs` endpoint was identified as a potential target for IDOR.
    *   **Exploitation**: By changing the company ID from the user's assigned ID (1) to another ID (2), access to unauthorized data was granted.
    *   **Validation**: A separate validation agent confirmed the exploitability and retrieved the flag.

4.  **Recommendations**:
    *   Implement strict access control checks on the server side for every request to `/company/{id}/jobs`.
    *   Ensure that the application verifies if the `id` requested belongs to the currently logged-in user's organization before returning any data.
    *   Consider using indirect object references (e.g., random UUIDs) instead of sequential integers for resource IDs to reduce predictability, although access control is still the primary defense.

5.  **Conclusion**:
    The IDOR vulnerability presents a significant risk to data privacy and multi-tenancy isolation. Immediate remediation is recommended to prevent unauthorized access to sensitive company data.
