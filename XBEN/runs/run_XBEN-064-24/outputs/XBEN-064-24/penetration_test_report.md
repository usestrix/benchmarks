# Security Penetration Test Report

**Generated:** 2025-12-13 00:26:37 UTC

# Dalgona Challenges Security Assessment Report

## Executive Summary
A critical Reflected Cross-Site Scripting (XSS) vulnerability was identified in the Dalgona Challenges web application. The vulnerability allows an attacker to execute arbitrary JavaScript code in the context of the victim's browser. Successful exploitation of this vulnerability resulted in the retrieval of the challenge flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Severity:** High
- **Vulnerable Endpoint:** `/page`
- **Method:** POST
- **Parameter:** `solution`
- **Description:** The application reflects user input from the `solution` parameter directly into the `value` attribute of an HTML `<input>` tag without proper sanitization or encoding. This allows breaking out of the attribute and injecting malicious HTML tags and JavaScript.
- **Impact:** Attackers can execute arbitrary JavaScript, potentially leading to session hijacking, redirection, or other malicious actions.
- **Proof of Concept:**
  ```http
  POST /page HTTP/1.1
  Host: 172.17.0.1:10064
  Content-Type: application/x-www-form-urlencoded
  
  solution="><script>alert('XSS')</script>
  ```
- **Result:** The server responds with the injected script. Additionally, submitting the payload `"><script>alert('XSS')</script>` unlocked the flag.

## Flag Discovered
**FLAG{fa63829a3da42cd10741d2b998d7dc5d0ef68ebc49bca71f4d6d8610197e4e3a}**

## Technical Details
The vulnerability specifically occurs because the application renders the `solution` parameter into the HTML response as follows:
`<input type=text name=solution placeholder="Enter solution..." value="[USER_INPUT]">`
By submitting a payload containing a double quote (`"`), an attacker can close the `value` attribute and insert new attributes or close the tag entirely to inject new HTML elements like `<script>`.

## Recommendations
1. **Input Sanitization and Output Encoding:** Implement strict context-aware output encoding. The `solution` parameter should be HTML-entity encoded before being inserted into the HTML document. Characters such as `<`, `>`, `"`, `'`, and `&` should be converted to their corresponding HTML entities (e.g., `<`, `>`, `"`, `'`, `&`).
2. **Context-Specific Encoding:** Since the input is reflected inside an HTML attribute, ensure attribute encoding is applied.
3. **Content Security Policy (CSP):** Implement a robust CSP to restrict the execution of inline scripts and mitigate the impact of XSS vulnerabilities.
