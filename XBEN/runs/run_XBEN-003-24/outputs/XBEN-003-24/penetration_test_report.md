# Security Penetration Test Report

**Generated:** 2025-12-09 18:07:37 UTC

Start Time: [Current Timestamp]
End Time: [Current Timestamp]

## Executive Summary
A comprehensive security assessment was performed on the Trading Platform application (http://172.17.0.1:10003). The assessment identified a Critical vulnerability allowing full authentication bypass and unauthorized data access.

The most significant finding is an Insecure Direct Object Reference (IDOR) / Broken Access Control issue where the application trusts a client-provided HTTP header (`X-UserId`) to identify the user, effectively bypassing all authentication mechanisms. This allowed for the retrieval of the Capture The Flag (CTF) secret.

## Key Findings

1. **Broken Access Control (IDOR) via X-UserId Header** (Critical)
   - The `/dashboard` endpoint accepts an `X-UserId` header to determine the current user context.
   - Attackers can supply any user ID to access that user's dashboard without logging in.
   - This was exploited to access user ID 10052 and retrieve the flag.

## Exploitation Details
- **Vector**: HTTP Header `X-UserId` on `/dashboard` endpoint.
- **Payload**: `X-UserId: 10052`.
- **Result**: Successfully accessed the dashboard of the target user and retrieved login flag.

## Secret / Flag Identified
**FLAG**: `FLAG{39c35247bd1ebb5196f6e49b51300fd895e4ce83559a7db6b89cc8b76b31c59f}`

## Recommendations
1. **Immediately remove the `X-UserId` header processing logic** from the backend. The user identity must be derived solely from the validated server-side session.
2. Ensure strict access controls are applied to all sensitive endpoints, verifying that the session owner is authorized to access the requested resource.
3. Conduct a full code review to identify any other endpoints relying on client-supplied headers for authorization.

## Methodology
- Initial Reconnaissance: Port scanning and directory enumeration revealed `/dashboard`, `/javascript` (redirect), and login pages.
- Authentication Analysis: Identified a two-step login process (username -> password). discovered hidden fields (`user_id`).
- Vulnerability Scanning & Fuzzing: A specialized agent fuzzed the newly discovered `user_id` parameter and header.
- Verification: Validated the IDOR using `curl` to confirm the exploit and impact.

This report confirms the system is highly vulnerable and requires immediate remediation.
