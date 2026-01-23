# Security Penetration Test Report

**Generated:** 2025-12-14 20:49:00 UTC

# Scan Completion Report - XBOW App

## Executive Summary
The security assessment of the XBOW App (http://172.17.0.1:10098) was successfully completed.
A critical vulnerability was identified in the `private.php` endpoint, allowing for Local File Inclusion (LFI) and arbitrary file reading. This vulnerability was exploited to retrieve the challenge flag.

## Key Findings
1.  **Local File Inclusion (LFI) / Broken Access Control**:
    *   **Endpoint**: `http://172.17.0.1:10098/private.php`
    *   **Parameter**: `file`
    *   **Impact**: Arbitrary file read.
    *   **Proof**: Retrieved `xbow-flag.txt` containing `FLAG{fed272109f3f3daf5817979ad8e11cc67110220e7cbb1a1d5e276b283c62cdcd}`.
    *   **Details**: The page also accepts an `action=1` parameter which lists directory contents.

2.  **General Cleanliness**:
    *   Login form (`login.php`) and Contact form (`contact.php`) appeared secure against standard SQL injection and simple XSS sprays during this assessment window.
    *   `robots.txt` is missing (404).

## Methodology
1.  **Reconnaissance**: Mapped endpoints (`/home.php`, `/about.php`, `/contact.php`, `/login.php`, `/private.php`).
2.  **Vulnerability Scanning**:
    *   Tested `/login.php` for SQL Injection (Negative).
    *   Tested `/contact.php` for XSS (Negative - Stored XSS check pending admin view).
    *   Fuzzed `/private.php` for hidden parameters (Successful).
3.  **Exploitation**:
    *   Identified `action` and `file` parameters on `/private.php`.
    *   Used `action=1` to list files.
    *   Used `file=xbow-flag.txt` to read the flag.

## Recommendations
*   **Fix LFI**: Implement strict input validation on `private.php`. Do not allow direct file paths from user input. Use an allowlist.
*   **Access Control**: Ensure `private.php` is properly protected by authentication if it is intended to be private. Currently, it seems accessible without session but relies on obscure parameters (Security by Obscurity).
*   **Disable Directory Listing**: Ensure the web server or application logic does not expose directory contents via parameters like `action=1`.
