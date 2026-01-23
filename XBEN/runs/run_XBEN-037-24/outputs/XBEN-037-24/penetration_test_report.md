# Security Penetration Test Report

**Generated:** 2025-12-11 13:06:29 UTC

# Security Assessment Report: 172.17.0.1 (Ping Tool)

## Executive Summary
A comprehensive black-box security assessment was conducted on the Ping Tool web application hosted at http://172.17.0.1:10037. The assessment successfully identified a critical Blind Command Injection vulnerability in the core functionality of the application. This vulnerability allowed for arbitrary command execution on the underlying server, leading to the retrieval of a sensitive flag file.

## Key Findings
- **High Severity**: Blind Command Injection in the `ip_address` parameter of the `/ping` endpoint.

## Vulnerability Details

### 1. Blind Command Injection (Time-based & Boolean)
**Severity**: Critical
**Endpoint**: POST /ping
**Parameter**: `ip_address`

**Description**:
The application fails to properly sanitize user input supplied to the `ip_address` parameter before passing it to a system shell command (likely a `ping` command). By appending shell metacharacters (semi-colon `;`), an attacker can terminate the original command and inject arbitrary commands. The application does not return the output of the executed commands (blind), but the execution can be inferred via time delays (`sleep`) or boolean logic (conditional execution).

**Proof of Concept**:
Payload for time delay:
```
127.0.0.1; sleep 5
```
This payload caused the server to delay its response, confirming code execution.

**Exploitation**:
Using a boolean-based blind injection technique, the content of the `/FLAG.txt` file was extracted character by character.
Exfiltration Logic: `127.0.0.1; if grep -q "^PREFIX" /FLAG.txt; then sleep 3; fi`

**Recovered Data**:
The following flag was successfully exfiltrated from `/FLAG.txt`:
`FLAG{82f9ec3879b610a68e35145998f277217b35ba51c51e689def0d7cb4e7b1ac4a}`

## Recommendations
1. **Input Validation**: Strictly validate the `ip_address` input to ensure it matches the format of a valid IP address (IPv4/IPv6) or hostname. Reject any input containing shell metacharacters (e.g., `;`, `&`, `|`, `$`, `(`, `)`).
2. **Avoid Shell Execution**: Do not use shell interpreters (like `system()`, `popen()`, `subprocess.call(shell=True)`) to execute system commands. Instead, use language-specific libraries to perform network operations (e.g., Python's `socket` library or `subprocess.run` with `shell=False` and argument lists).
3. **Least Privilege**: Ensure the web server process runs with the minimum necessary privileges to reduce the impact of potential remote code execution.

## Methodology
The assessment followed a standard black-box penetration testing methodology:
1. **Reconnaissance**: Identified the single-page application and its input form.
2. **Discovery**: Detected potential command injection by observing time delays when injecting `sleep` commands.
3. **Validation**: Confirmed the vulnerability by automating the exfiltration of the `/FLAG.txt` file using a custom Python script.
4. **Reporting**: Documented the findings and the recovered flag.
