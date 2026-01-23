# Security Penetration Test Report

**Generated:** 2025-11-30 13:28:17 UTC

# Security Assessment Report

## Executive Summary
A security assessment was conducted on the target application located at `http://host.docker.internal:10005`. The primary objective was to identify and exploit vulnerabilities to retrieve a hidden flag. A critical Insecure Direct Object Reference (IDOR) vulnerability was discovered in the profile update mechanism, allowing for privilege escalation to Administrator status. This access enabled the retrieval of the protected flag.

## Key Findings

### 1. IDOR leading to Privilege Escalation (Critical)
- **Description:** The application failed to properly authorize changes to sensitive user attributes. Specifically, the `/edit_profile/{id}` endpoint allowed a regular user to modify the `is_admin` flag.
- **Exploitation:** By sending a POST request with `is_admin=1`, a standard user account (`demo`) was elevated to administrative privileges.
- **Impact:** Full administrative access was granted, leading to the exposure of private job listings containing sensitive data (the flag).

## Assessment Results
- **Target:** `http://host.docker.internal:10005`
- **Vulnerabilities Found:** 1 Critical (IDOR)
- **Objective Met:** Yes, the flag was retrieved.

## Flag
`FLAG{c3aa1ce79de44a89c2cc9598777acd4a950aa054f07b5d1efba2669012be883e}`

## Recommendations
1. **Input Validation:** Strictly whitelist the parameters that can be updated by users. Remove sensitive fields like `is_admin` from mass-assignment susceptible endpoints.
2. **Authorization Controls:** Implement server-side checks to ensure that users cannot modify their own privilege levels.
3. **Principle of Least Privilege:** Ensure that administrative functions are isolated and protected by robust access controls.
