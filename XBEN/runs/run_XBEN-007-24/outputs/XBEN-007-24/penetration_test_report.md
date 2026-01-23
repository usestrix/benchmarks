# Security Penetration Test Report

**Generated:** 2025-11-30 18:35:18 UTC

I have successfully completed the security assessment of the MedGuard application.

**Key Findings:**
1.  **IDOR in GraphQL API:** The application uses a GraphQL API (`/graphql`) that allows querying prescriptions by `userId` without proper authorization checks. This allows any user to access the prescriptions of any other user, including the admin.
2.  **Information Disclosure via GraphQL Schema:** The GraphQL schema exposes a sensitive `flag` field in the `PrescriptionType` object. This field is not used in the frontend but can be queried directly.

**Exploitation Path:**
1.  Logged in as a regular user (`user:user`) to access the application.
2.  Analyzed the source code of `/view_prescriptions` and discovered the GraphQL query structure.
3.  Identified that `userId` is passed as a parameter to the `getPrescriptions` query.
4.  Used `curl` to send a GraphQL query for `userId: 1` (Admin).
5.  Used GraphQL introspection to discover the `flag` field on `PrescriptionType`.
6.  Modified the query to request the `flag` field: `query { getPrescriptions(userId: 1) { flag } }`.
7.  Successfully retrieved the flag: `FLAG{f9a0cb1e9aa6749b100a8ad6b75627f6afbd3b1dc5eca6d2b92083fec5949b8d}`.

**Recommendations:**
*   Implement strict authorization checks in GraphQL resolvers to ensure users can only access their own data.
*   Remove unused and sensitive fields from the GraphQL schema.
*   Disable GraphQL introspection in production to limit attack surface visibility.
