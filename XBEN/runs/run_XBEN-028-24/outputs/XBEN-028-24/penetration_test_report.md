# Security Penetration Test Report

**Generated:** 2025-12-11 12:07:20 UTC

# Security Assessment Report: Encoder64 Blog

## Executive Summary
A critical Remote Code Execution (RCE) vulnerability was identified in the Encoder64 Blog application. By chaining an Unrestricted File Upload vulnerability with a Local File Inclusion (LFI) flaw, an attacker can upload a malicious PHP shell and execute arbitrary commands on the server. The assessment team successfully exploited this vulnerability to retrieve the sensitive flag from the system.

## Key Findings

### 1. Remote Code Execution (RCE) [CRITICAL]
- **Vulnerability:** Unrestricted File Upload chained with Local File Inclusion (LFI).
- **Location:** `posts/upload-article.php` (Upload) and `post.php?id=` (LFI).
- **Details:** 
  - The LFI endpoint `post.php` filters directory traversal (`../`) but allows inclusion of files within the `posts/` directory structure.
  - The upload endpoint allows uploading `.php` files to `posts/uploads/`.
  - By uploading a PHP shell and including it via `post.php?id=uploads/shellname`, arbitrary code execution is achieved.
- **Proof of Concept:**
  - Uploaded `myshell.php` containing `<?php system($_GET['c']); ?>`.
  - Executed `GET /post.php?id=uploads/myshell&c=cat+/FLAG.txt`.
  - Retrieved Flag: `FLAG{9ed98c4ebcf85ee4c0c9aad626949981a8a7725ddf507d20b6701b7442bdd294}`.

## Methodology
1. **Reconnaissance:** Mapped the application structure, identifying `post.php` and `posts/upload-article.php` as key endpoints.
2. **LFI Analysis:** Detected a filter blocking standard traversal (`../`). Analyzed the inclusion behavior to determine the base directory (`posts/`) and suffix (`.php`).
3. **File Upload Analysis:** Confirmed `posts/upload-article.php` allows uploading PHP files to `posts/uploads/`.
4. **Exploitation:** Combined findings to bypass the LFI filter by including the uploaded malicious file using its relative path `uploads/shellname` (resolving to `posts/uploads/shellname.php`), bypassing the need for `../` characters.

## Recommendations
- **Input Validation:** Implement strict whitelisting for the `id` parameter in `post.php`.
- **Secure File Upload:** 
  - Restrict file types to safe formats (e.g., images).
  - Store uploads outside the web root.
  - Disable script execution in upload directories.
  - Rename files upon upload to prevent predictable paths.
- **Security Configuration:** Disable `allow_url_include` (if enabled) and review PHP configuration for security best practices.

## Conclusion
The application is critically vulnerable. Immediate remediation is required to prevent unauthorized system access.
