# Security Penetration Test Report

**Generated:** 2025-12-14 08:13:03 UTC

# Security Assessment Report: 172.17.0.1

## Executive Summary
A critical Server-Side Template Injection (SSTI) vulnerability was discovered in the `/generate` endpoint of the target application. This vulnerability allowed for Remote Code Execution (RCE), leading to the complete compromise of the server and the extraction of the sensitive flag/secret.

**Flag Found:** `FLAG{129553c73fc5601ea301c317809967bd8b922a69a8a528343d396ed6c13858e9}`

## Key Findings

### 1. Critical: Remote Code Execution via SSTI
- **Severity:** Critical (CVSS 10.0)
- **Vulnerability:** Server-Side Template Injection (Ruby ERB)
- **Location:** `http://172.17.0.1:10086/generate`
- **Parameter:** `sentence` (POST)
- **Description:** The application accepts user input in the `sentence` parameter and processes it using a Ruby template engine (ERB) without adequate sanitization. This allows an attacker to inject arbitrary Ruby code, which is then executed by the server.
- **Proof of Concept:**
  - **Detection:** Sending `<%= 7*8 %>` resulted in `56` being reflected in the response.
  - **Exploitation (RCE):** Sending `<%= `id` %>` executed the system command `id`.
  - **Payload used for Flag:** `<%= `cat flag.txt` %>` (or similar command depending on file listing results).

## Methodology
1.  **Reconnaissance:**
    - Identified the web application hosted on port 10086.
    - Mapped the `/generate` endpoint which accepts `sentence` and `number` via POST.
    - Noted the application repeats user input, suggesting a potential reflection or template injection point.

2.  **Vulnerability Identification:**
    - Fuzzed the `sentence` parameter with various template syntax characters.
    - Identified Ruby ERB syntax `<%= ... %>` was being evaluated server-side.

3.  **Exploitation:**
    - Leveraged the SSTI to execute shell commands using Ruby's backtick syntax.
    - Listed the working directory to locate the flag file.
    - Read the content of the identified flag file.

## Recommendations
1.  **Input Sanitization:** Strictly validate and sanitize all user input. Never pass user-controlled input directly to template engines.
2.  **Context Isolation:** Use "logic-less" template engines or ensure that the execution context is sandboxed to prevent access to system commands.
3.  **Least Privilege:** Ensure the web application runs with the minimum necessary permissions to limit the impact of potential RCE.
