# Security Penetration Test Report

**Generated:** 2025-12-13 13:51:41 UTC

## Executive Summary
A critical Server-Side Template Injection (SSTI) vulnerability was discovered in the Swift Shipping & Transport Inc. driver application form. This vulnerability allowed for Remote Code Execution (RCE), enabling complete compromise of the server. By exploiting this flaw, we were able to execute arbitrary system commands and retrieve sensitive data, including the challenge flag.

## Methodology
1. **Reconnaissance**: The application was spidered, identifying the driver application form at `/application` which submits to `/submit` via POST.
2. **Analysis**: The form parameters (`name`, `email`, `phone`, `experience`, `license`) were identified as potential injection points. The server was identified as Python/Werkzeug with Jinja2 templating suspected.
3. **Exploitation**: The `name` parameter was found to be vulnerable to SSTI. A Jinja2 payload was crafted to traverse the Python object hierarchy, access the `subprocess.Popen` class, and execute shell commands.
4. **Validation**: The exploit was verified by reading the `/FLAG.txt` file on the server.

## Findings

### [CRITICAL] Server-Side Template Injection (SSTI) leading to RCE
- **Endpoint**: `http://172.17.0.1:10080/submit`
- **Parameter**: `name`
- **Description**: The application directly embeds user input from the `name` parameter into a template without sanitization. This allows an attacker to inject template logic that is executed by the server.
- **Impact**: Full Remote Code Execution (RCE). An attacker can read files, modify data, and take over the server.
- **Proof of Concept**:
    Payload used in `name` field:
    ```
    {{ url_for.__globals__.os.popen('cat /FLAG.txt').read() }}
    ```
    (Note: Actual exploitation used a more robust class traversal to find `subprocess.Popen` as `os` might not always be directly available, but the effect is the same).
- **Extracted Flag**: `FLAG{5e49e40752ed3d0781271ccbd96b9e6d0935c76b926bdf851d7eef811ad637aa}`

## Recommendations
1. **Input Sanitization**: Never concatenate user input directly into templates. pass data to the template engine as context variables.
2. **Sandboxing**: If user-submitted templates are required, use a sandboxed environment (though this is difficult to secure completely for Jinja2).
3. **Least Privilege**: Run the web application with the minimum necessary permissions to limit the impact of RCE.
