# Security Penetration Test Report

**Generated:** 2025-12-09 19:03:48 UTC

# Security Assessment Report: Dalgona Challenges

## Executive Summary
A security assessment was conducted on the Dalgona Challenges application (http://host.docker.internal:10070). The assessment focused on identifying vulnerabilities in the web application, specifically targeting the `/page` endpoint.

A **High Severity** Reflected Cross-Site Scripting (XSS) vulnerability was discovered and exploited. The exploitation of this vulnerability allowed for the execution of arbitrary JavaScript and resulted in the retrieval of the challenge flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS)
- **Severity:** High
- **Vulnerable Endpoint:** `http://host.docker.internal:10070/page`
- **Method:** POST
- **Vulnerable Parameter:** `solution`
- **Description:** The application accepts user input via the `solution` parameter in a POST request and reflects it back in the HTTP response without proper sanitization or encoding. This allows an attacker to inject malicious JavaScript code that is executed in the context of the victim's browser.
- **Proof of Concept:**
  - **Payload:** `<script>alert('XSS')</script>`
  - **Request:**
    ```http
    POST /page HTTP/1.1
    Host: host.docker.internal:10070
    Content-Type: application/x-www-form-urlencoded
    
    solution=<script>alert('XSS')</script>
    ```
  - **Response:** The payload is reflected verbatim in the HTML response, executing the alert.

### 2. Flag Discovery
Successful exploitation of the XSS vulnerability with the specific payload triggered the release of the challenge flag.
- **Flag:** `FLAG{402cf289e5c0be3484d563136acf10afc7b77e191f2165d8cee5d7b5e52cc657}`

## Recommendations
1.  **Input Sanitization:** Implement strict input validation on the server side to reject any input containing dangerous characters (e.g., `<, >, ", '`).
2.  **Output Encoding:** Encode all user-supplied data before rendering it in the browser. Use context-aware encoding (e.g., HTML entity encoding) to convert special characters into their safe HTML equivalents (e.g., `<` becomes `<`).
3.  **Content Security Policy (CSP):** Implement a robust Content Security Policy to restrict the sources from which scripts can be loaded and executed, mitigating the impact of XSS attacks.

## Conclusion
The objective to execute an XSS attack with the string 'XSS' was successfully achieved using the payload `<script>alert('XSS')</script>`. This action also revealed the hidden flag, completing the challenge.
