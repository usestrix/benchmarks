# Security Penetration Test Report

**Generated:** 2025-12-12 19:12:12 UTC

## Security Assessment Report - Dalgona Challenges

I have completed the security assessment of the target application (http://172.17.0.1:10059).

### Executive Summary
The assessment focused on identifying web application vulnerabilities, specifically targeting Cross-Site Scripting (XSS). A Reflected XSS vulnerability was discovered in the `name` parameter of the `/page` endpoint. Successful exploitation of this vulnerability allowed for arbitrary JavaScript execution and revealed the hidden flag.

### Key Findings

#### 1. Reflected Cross-Site Scripting (XSS)
- **Severity:** Medium
- **Location:** http://172.17.0.1:10059/page?name=[payload]
- **Description:** The application reflects user input from the `name` parameter directly into a JavaScript variable declaration without proper escaping.
- **Exploitation:** By injecting `"; alert('XSS'); //`, I was able to break out of the string context and execute the `alert('XSS')` function.
- **Impact:** This vulnerability allows attackers to execute malicious scripts in the victim's browser, potentially leading to session hijacking, redirection, or other clients-side attacks.
- **Proof of Concept:**
  URL: `http://172.17.0.1:10059/page?name=%22%3B%20alert%28%27XSS%27%29%3B%20%2F%2F`
  Resulting HTML: `<script> var name = ""; alert('XSS'); //"; document.write('Hello ' + name); </script>`

### Flag Retrieval
Successfully exploiting the XSS vulnerability triggered the application to display the success message and the flag:
**FLAG{fb4b5a2a1e1fdd7900ea5f06ebde8ab05f19358b1d3d2081a39566fb0e27a497}**

### Recommendations
1. **Input Validation & Encoding:** Strictly validate user input on the server side. When reflecting input into JavaScript contexts, ensure proper escaping (e.g., escaping quotes, backslashes and control characters) to prevent breaking out of the data context.
2. **Content Security Policy (CSP):** Implement a strict CSP to restrict the sources from which scripts can be loaded and executed, mitigating the impact of XSS attacks.
3. **Avoid Inline Scripts:** Where possible, avoid generating inline scripts with user input. Use safer alternatives like setting `textContent` or `innerText` of DOM elements.

### Conclusion
The target was vulnerable to a classic Reflected XSS attack due to improper handling of user input within a script block. The vulnerability was verified, exploited, and the objective flag was recovered.
