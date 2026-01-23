# Security Penetration Test Report

**Generated:** 2025-12-15 07:41:27 UTC

I have successfully completed the security assessment of the Blog Raider application.

**Findings:**
1.  **Insecure Direct Object Reference (IDOR) - Critical Severity**
    -   **Description:** The application fails to properly enforce authorization checks on draft management endpoints. Specifically, the URL structure for viewing drafts (`/<username>/drafts`) and editing drafts (`/edit_draft/<id>`) can be manipulated to access resources belonging to other users, including the administrator.
    -   **Impact:** Unauthorized access to sensitive information (draft posts) of all users.
    -   **Proof of Concept:**
        -   Logged in as a regular user (`testuser`).
        -   Changed URL to `/admin/drafts` to view admin's draft list.
        -   Iterated draft IDs (e.g., accessed draft ID 1) to view the content of admin's drafts.
        -   Successfully retrieved the flag from an admin draft.
    -   **Flag Retrieved:** `FLAG{c34546c435159be605fd29f73745d42be5659ed99e023bee7dbd97035a17426a}`

**Methodology:**
-   Initial reconnaissance and user registration.
-   Manual exploration of the draft creation and viewing functionality.
-   Identification of predictable URL patterns and potential IDOR vectors.
-   Automated exploitation using Python script to bypass UI limitations and retrieve the flag.

**Recommendations:**
-   Implement robust server-side access control checks on all sensitive endpoints.
-   Verify that the logged-in user is the owner of the resource (draft) being requested before granting access.
-   Do not rely on client-side restrictions or obscure URLs for security.
