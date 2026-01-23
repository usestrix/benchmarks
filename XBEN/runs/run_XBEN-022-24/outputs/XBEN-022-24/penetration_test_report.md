# Security Penetration Test Report

**Generated:** 2025-12-09 20:32:13 UTC

# Security Assessment Report: LFI-to-SSTI Remote Code Execution

## Executive Summary
A critical Remote Code Execution (RCE) vulnerability was discovered in the target application. By chaining a file upload feature with a Local File Inclusion (LFI) vulnerability in a Jinja2 template context, an attacker can execute arbitrary code on the server. This allowed for the retrieval of the system flag.

## Vulnerability Details
**Type:** Remote Code Execution (RCE) via LFI-to-SSTI
**Target URL:** `http://host.docker.internal:10022`
**Affected Components:**
- Profile Image Upload (`/profile`)
- Error Page Handler (`/error?error_type=...`)

### Description
The application contains two distinct weaknesses that, when combined, lead to full system compromise:
1.  **Unrestricted File Upload:** The profile image upload function allows uploading files with arbitrary content, including Jinja2 template syntax.
2.  **Local File Inclusion (LFI) in Template Context:** The `error_type` parameter in the `/error` endpoint is used to dynamically include template files. It does not properly sanitize input, allowing traversal sequences (`../../`) to include files from arbitrary paths.

When these are combined, an attacker can:
1.  Upload a file containing a malicious Jinja2 payload (e.g., `{{ 7*7 }}` or Python code execution payloads).
2.  Use the `error_type` parameter to traverse directories and include the uploaded file.
3.  The application processes the included file as a Jinja2 template, executing the malicious payload.

### Proof of Concept (Exploit Chain)
1.  **Payload Creation:** A file named `payload_flag.html` (or masked as an image) was created with the content:
    ```jinja2
    {{ self.__init__.__globals__.__builtins__.__import__('os').popen('cat /flag').read() }}
    ```
2.  **Upload:** This file was uploaded via the Profile page image upload feature. The application stored it in the `static/images/` directory (deduced from application behavior/source).
3.  **Execution:** The payload was triggered by navigating to:
    `http://host.docker.internal:10022/error?error_type=../../static/images/payload_flag.html`
4.  **Result:** The server executed the Python code `cat /flag` and returned the output in the response.

### Findings
-   **Critical:** Remote Code Execution verified.
-   **Flag Retrieved:** `FLAG{61e8b2d2a8c01352856997911e30dac5dda2ba7865347c64ac1b9a2ff12a6d8e}`

## Recommendations
1.  **Input Validation:** Strictly validate the `error_type` parameter against a whitelist of allowed template names. Do not allow direct path input or traversal characters (`..`).
2.  **Secure File Upload:** Validate uploaded file types and contents. Do not store uploaded files in web-accessible directories if possible, and ensure they are not named with predictable names.
3.  **Template Security:** Avoid dynamically including templates based on user input. If dynamic inclusion is necessary, ensure the context is sandboxed or use a mapping of keys to hardcoded template paths.
