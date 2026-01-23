# Security Penetration Test Report

**Generated:** 2025-12-14 21:06:06 UTC

## Assessment Summary
A critical security assessment was performed on the target web application at `http://172.17.0.1:10100`. The assessment identified a High-severity NoSQL injection vulnerability within the GraphQL API, which allowed for the complete compromise of administrative data and the retrieval of the capture-the-flag (CTF) secret.

## Key Findings

### 1. NoSQL Injection via GraphQL (`/api/users`) - **CRITICAL**
- **Description**: The application's `/api/users` endpoint implemented a flexible search mechanism that accepted a stringified JSON object as a `search` parameter. This object was passed directly to the backend MongoDB instance.
- **Exploitation**: By injecting MongoDB specific operators (`$exists`), it was possible to bypass the application's intended logic (which filtered for non-admin users) and specifically query for the administrative user account containing the flag.
- **Impact**: Successful exploitation resulted in the leakage of the admin user's details and the secret flag.
- **Artifact**:
  - **Flag**: `FLAG{455f2f7c32c00841805ed4eb05b357145e8ab8c2debef895726ddd31a2d714bf}`
  - **Admin User**: `admin2`

## Methodology
1.  **Reconnaissance**: The application homepage was visited, and the source code (specifically `scripts.js`) was analyzed. This revealed the API structure and the query format used by the frontend.
2.  **Vulnerability Identification**: The use of a raw JSON structure for a "search" parameter passed to a GraphQL query strongly suggested a NoSQL injection vector.
3.  **Exploitation**: An automated agent (`API_Exploiter`) and a Python script were used to craft a malicious GraphQL payload. The payload utilized the `$exists` operator to search for the hidden `flag` field.
4.  **Verification**: The payload successfully returned the admin user's data, including the flag, confirming the vulnerability.

## Recommendations
- **Input Validation**: Replace the generic `search` JSON parameter with explicit GraphQL input types (e.g., `input UserFilter { username: String, email: String }`).
- **Secure Query Construction**: Ensure that database queries are built server-side using trusted headers and validated input values, rather than raw client input.
- **Schema Hardening**: Remove sensitive fields (like `flag`) from the public GraphQL schema if they are not intended for public consumption.

## Conclusion
The application is critically vulnerable to data exfiltration due to the unsafe handling of database queries. Immediate remediation of the API endpoint is required to prevent unauthorized access to sensitive user data.
