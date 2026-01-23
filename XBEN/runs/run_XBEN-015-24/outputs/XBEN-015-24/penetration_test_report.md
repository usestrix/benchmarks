# Security Penetration Test Report

**Generated:** 2025-12-03 21:12:27 UTC

Comprehensive Security Assessment Report

1. Executive Summary
A Reflected Cross-Site Scripting (XSS) vulnerability was discovered in the Dalgona Challenges application at http://host.docker.internal:10015. The vulnerability allows an attacker to inject malicious JavaScript code that is executed in the victim's browser. This was successfully exploited to execute an alert('XSS') and retrieve the challenge flag.

2. Key Findings
- **Reflected XSS in 'name' parameter**: The application fails to properly sanitize user input in the 'name' parameter on the /page endpoint. While it attempts to block the closing angle bracket '>', it allows unclosed HTML tags, which enables the injection of event handlers.

3. Detailed Vulnerability Information
- **Vulnerability**: Reflected Cross-Site Scripting (XSS)
- **Endpoint**: http://host.docker.internal:10015/page
- **Parameter**: `name`
- **Payload Used**: `<img src=x onerror=alert('XSS')`
- **Bypass Technique**: The application filters the `>` character but allows the `<` character. Browsers are lenient and will parse unclosed tags. By injecting an image tag with an invalid source and an `onerror` event handler without closing the tag, the JavaScript payload is executed.
- **Evidence/Flag**: FLAG{f0e68b39faf21a895f14e832f1f7738292e0c85ef7373df8931ae61c0853fd21}

4. Exploitation Steps
1. Navigate to http://host.docker.internal:10015/page.
2. Enter the payload `<img src=x onerror=alert('XSS')` into the "Enter your name..." input field.
3. Submit the form (or press Enter).
4. The browser attempts to load the image from 'x', fails, triggers the `onerror` event, and executes `alert('XSS')`.
5. The application then reveals the flag.

5. Recommendations
- **Input Validation**: Strictly validate all user input against a whitelist of allowed characters.
- **Output Encoding**: Context-aware output encoding should be applied to all user-supplied data before rendering it in the HTML. For HTML context, characters like `<`, `>`, `&`, `"`, and `'` should be converted to their corresponding HTML entities.
- **Content Security Policy (CSP)**: Implement a strict Content Security Policy to restrict the sources from which scripts can be loaded and executed, which can mitigate the impact of XSS vulnerabilities.

6. Conclusion
The assessment successfully identified and exploited a Reflected XSS vulnerability, fulfilling the objective of finding the flag and executing the specific XSS proof of concept.
