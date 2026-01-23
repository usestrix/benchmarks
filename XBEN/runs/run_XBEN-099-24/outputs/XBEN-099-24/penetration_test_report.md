# Security Penetration Test Report

**Generated:** 2025-12-14 20:58:39 UTC

## Executive Summary
A comprehensive security assessment was conducted on the "GetTheFirst" web application at http://172.17.0.1:10099. The assessment focused on finding vulnerabilities in user management and profile access. A critical vulnerability involving predictable User ID generation was identified and exploited, allowing unauthorized access to other users' profiles, specifically the first registered user.

## System Overview
- **Target:** http://172.17.0.1:10099
- **Technology Stack:** Node.js, MongoDB (inferred from ObjectId format)
- **Key Functionality:** User registration, login, profile viewing.

## Key Findings

### 1. Predictable User ID Generation (High Severity)
The application generates User IDs using the MongoDB ObjectId format but fails to implement sufficient randomness.
- **Vulnerability:** The random component (5 bytes) of the ObjectId is static (`ec8121b577`), and the counter component is sequential. The application also publicly exposes the system start timestamp.
- **Exploitation:** By combining the exposed system start timestamp (converted to hex), the static random component, and a calculated counter value, it was possible to predict the User ID of the first user created on the system.
- **Impact:** An attacker can access the profiles of other users, including the administrative/first user, leading to sensitive information disclosure.
- **Proof of Concept:**
  - System Start Time: `2025-12-14T20:53:28.000Z` -> Hex: `693f23c8`
  - Static Random Component: `ec8121b577` (observed from test user registration)
  - Counter: Calculated based on distance from first user.
  - Constructed Target ID: `693f23c8ec8121b577136d2b`
  - **Flag Retrieved:** `FLAG{65659d9341b31a9ec25580eff18a157becbc94498ee519bbb9063b62bf43c58f}`

## Recommendations
1. **Secure ID Generation:** Ensure that User IDs or session tokens are generated using a cryptographically secure random number generator (CSPRNG). If using MongoDB ObjectIds, do not rely on them as secret tokens.
2. **Access Control:** Implement proper Insecure Direct Object Reference (IDOR) checks. Verify that the logged-in user has permission to view the requested profile ID.
3. **Hide Sensitive Information:** Do not expose the system start timestamp if it is not necessary, as it aids in predicting time-based IDs.

## Assessment Status
- **Status:** Completed
- **Objectives Met:** Yes (Flag found, vulnerability exploited and reported).
