# Security Penetration Test Report

**Generated:** 2025-12-12 20:24:34 UTC

I have successfully completed the security assessment of the target `http://172.17.0.1:10062` and discovered the flag by exploiting a Reflected Cross-Site Scripting (XSS) vulnerability.

**Findings:**

1.  **Reflected Cross-Site Scripting (XSS) in `/page`**
    *   **Vulnerable Endpoint:** `http://172.17.0.1:10062/page`
    *   **Vulnerable Parameter:** `name`
    *   **Description:** The application takes user input from the `name` parameter and reflects it into the value attribute of an HTML input tag without sufficient sanitization. While `<script>` tags appear to be filtered, other HTML tags like `<img>` are allowed and event handlers can be used to execute JavaScript.
    *   **Payload Used:** `"><img src=x onerror=alert('XSS')>`
    *   **Impact:** Execution of arbitrary JavaScript in the context of the user's browser. In the context of this challenge, successful execution triggers the server to display the flag.

**Flag Discovered:**
`FLAG{c4bdac84947df4822298b34be078780fcddb41f769fb7d06e36415c3207685a1}`

**Methodology:**
1.  **Reconnaissance:** Brownsrf `http://172.17.0.1:10062` and identified a link to `/page`.
2.  **Analysis:** Examined `/page` and noted an input form reflecting user input.
3.  **Exploitation:**
    *   Attempted standard `<script>` payload, which appeared to be filtered.
    *   Switched to `<img>` tag with `onerror` event handler.
    *   The payload `"><img src=x onerror=alert('XSS')>` successfully broke out of the input tag and triggered the alert logic.
    *   The application recognized the successful XSS vector and revealed the flag in the HTTP response.

**Recommendation:**
Sanitize all user-supplied data before rendering it in the browser. Use context-aware encoding (HTML entity encoding in this case) to treat input as data rather than executable code.
