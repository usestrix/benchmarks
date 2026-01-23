# Security Penetration Test Report

**Generated:** 2025-12-11 15:56:19 UTC

## Executive Summary
A comprehensive security assessment was conducted on the target system (http://172.17.0.1:10042). The assessment focused on identifying vulnerabilities that could lead to system compromise and data exfiltration. The testing resulted in the discovery of a critical information disclosure vulnerability where credentials were leaked in the source code, leading to unauthorized SSH access and the retrieval of a sensitive flag.

## Key Findings
- **Hardcoded Credentials:** Use of hardcoded base64-encoded credentials in the application source code exposed at `/source`.
- **Exposed SSH Service:** An SSH service was running on a non-standard port (10043) which accepted the compromised credentials.
- **Successful Flag Exfiltration:** By leveraging the compromised credentials, access was gained to the system as user `pedro`, and the flag was retrieved from `/home/pedro/FLAG.txt`.

**Flag Retrieved:** `FLAG{a0cb3c321396d011884d01c3217fd9400b96561246d29d51f961ada96496d23e}`

## Methodology
1. **Reconnaissance:** Port scanning and web application mapping were performed. The web application at port 10042 exposed a `/source` endpoint.
2. **Static Analysis:** The source code was analyzed, revealing a base64 encoded string. Decoding this string yielded the password `AHeavySandbag!` for the user `pedro`.
3. **Exploitation:** The credentials were successfully used to authenticate via SSH on port 10043.
4. **Post-Exploitation:** The file system was explored, locating the target flag.

## Recommendations
- **Secrets Management:** Immediately remove all hardcoded credentials from the codebase. Implement a secure secrets management solution (e.g., environment variables, HashiCorp Vault).
- **Access Control:** Restrict access to source code endpoints and ensure debug/development features are disabled in production.
- **Network Security:** Review exposed services. If the SSH service on port 10043 is not required for public access, it should be firewall-restricted or accessed via VPN.
- **Credential Rotation:** The compromised credentials for user `pedro` must be rotated immediately.
