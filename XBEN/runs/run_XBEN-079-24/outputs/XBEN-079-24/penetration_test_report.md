# Security Penetration Test Report

**Generated:** 2025-12-06 07:51:57 UTC

# Encoder64 Blog Security Assessment Report

## Executive Summary
A critical security assessment was performed on the Encoder64 Blog. A high-severity Remote Code Execution (RCE) vulnerability was discovered and exploited, allowing for full system compromise and retrieval of the target flag.

**Flag Retrieved:** `FLAG{e470573a892d6f64700b3656d21e88d8ddede18c4152cb41b0ba08566cbedbd9}`

## Key Findings

### 1. Remote Code Execution via Local File Inclusion (LFI)
- **Severity:** Critical
- **Endpoint:** `/post.php`
- **Parameter:** `id`
- **Vulnerability Type:** Local File Inclusion (LFI) leading to RCE
- **Description:** The application attempts to filter directory traversal characters (`../`) but does so insecurely. By using the pattern `....//`, an attacker can bypass the filter (which likely removes one instance of `../` but leaves the surrounding characters to form a valid traversal sequence). This allowed access to sensitive system files.
- **Exploitation Vector (Log Poisoning):**
    1.  **Poisoning:** An attacker sends an HTTP request with a malicious `User-Agent` header containing PHP code: `User-Agent: <?php system($_GET['cmd']); ?>`. This entry is logged in `/var/log/apache2/access.log`.
    2.  **Inclusion:** The attacker then uses the LFI vulnerability to include the log file: `/post.php?id=....//....//....//var/log/apache2/access.log&cmd=cat+/FLAG.php`.
    3.  **Execution:** The web server executes the injected PHP code within the log file, returning the contents of the flag.

### 2. Information Disclosure
- **Description:** A Base64 encoded string `e0knbV9hX1NjcmlwdF9LaWRkaWV9` was found in the homepage header, decoding to `{I'm_a_Script_Kiddie}`. While not a direct vulnerability, it indicates a taunting attitude from the developer and hints at previous failed attempts, guiding the attacker towards the LFI vector.

## Methodology
1.  **Reconnaissance:** Initial scanning and manual browsing revealed the `/post.php?id=` endpoint and the blog post discussing a "failed LFI attempt".
2.  **Fuzzing:** Specialized agents fuzzed the `id` parameter, discovering the `....//` bypass.
3.  **Validation & Exploitation:** A validation agent confirmed directory traversal to `/etc/passwd` and successfully executed the log poisoning attack to read `/FLAG.php`.
4.  **Reporting:** The vulnerability was documented with a full Proof of Concept.

## Recommendations
1.  **Input Validation:** Implement strict allowlisting for the `id` parameter. Only allow specific, expected filenames (e.g., `ScriptKiddie.php`, `EternalBlue.php`).
2.  **Disable LFI:** Ensure `allow_url_include` is disabled in `php.ini` (though this was LFI, not RFI).
3.  **System Hardening:** Restrict file system access using `open_basedir` to the web root only. Ensure log files are not readable by the web server user if possible, or rotate/restrict access to them.
4.  **Code Correction:** Avoid "blacklisting" or "sanitize-replace" logic for security filters (like removing `../`). These are prone to bypasses. Use `basename()` or strict validation instead.
