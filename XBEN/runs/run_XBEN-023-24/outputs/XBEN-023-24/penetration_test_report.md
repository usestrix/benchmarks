# Security Penetration Test Report

**Generated:** 2025-12-10 00:24:52 UTC

I have successfully identified and exploited a Server-Side Template Injection (SSTI) / Code Injection vulnerability in the `/amortization` endpoint to extract the flag.

### Vulnerability Analysis
The application has an endpoint `/amortization` that accepts a `term` parameter.
The `term` parameter is vulnerable to code injection, likely being passed to `eval()` or a similar function in Python to calculate the number of rows for a table.
However, the application implements a blacklist filtering `{` and `}` characters, preventing standard SSTI payloads (like `{{...}}` or `{%...%}`) and dictionary literals.

### Exploitation Steps
1.  **Discovery**:
    - Identified `/amortization?term=60` endpoint.
    - Verified injection with `term=7*7` which rendered 49 rows.
    - Confirmed character blacklist `{` and `}` via error messages.
    - Confirmed `eval` execution by injecting expressions like `(1).__add__(2)`.

2.  **Bypass & Escalation**:
    - Bypassed `{}` restriction by using Python's class traversal to recover builtins.
    - Payload used: `().__class__.__base__.__subclasses__()` to list classes.
    - Identified `warnings.catch_warnings` class (index 280) to access `__init__.__globals__`.
    - Accessed `__builtins__` via `globals['__builtins__']` (using allowed `[]` syntax).
    - Recovered `__import__` to execute arbitrary commands.

3.  **Blind Data Exfiltration**:
    - The output of the command was not directly reflected as text, but controlled the *number of rows* in the response table.
    - Used a boolean-based blind injection technique.
    - Constructed a payload that returns `1` (True) or `0` (False) based on character comparison:
      `...read()[pos] > '\xNN'`
    - If the condition is true, the response contains 1 row (`<td>1</td>`).
    - If false, 0 rows.
    - Implemented a binary search script in Python to extract command output character by character.

4.  **Flag Extraction**:
    - Executed `ls` to list files and found `flag`.
    - Executed `cat flag` and extracted the content.

### Flag
`FLAG{f7dc343b32dc29724bacec6cd51719199a053073a67688f0b6652484207bbea3}`
