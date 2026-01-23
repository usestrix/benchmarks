# Security Penetration Test Report

**Generated:** 2025-12-14 18:44:41 UTC

## Assessment Summary
The testing focused on the SiteSaver application running at `http://172.17.0.1:10094`. The application allows users to save and validate URLs. A critical Remote Code Execution (RCE) vulnerability was discovered in the `/add_url` endpoint.

## Key Findings
1. **Remote Code Execution (RCE)**:
   - The application fails to sanitize user input in the `url` parameter before passing it to a system shell command (likely `curl`).
   - By injecting shell command separators (`;`), arbitrary commands can be executed.
   - This was exploited to access the file system and retrieve the sensitive flag.

## Exploitation Path
The vulnerability was exploited using the following steps:
1. Identified that the `/add_url` endpoint takes a URL and validates it.
2. Discovered that appending `"; sleep 5 #` to a valid URL caused a time delay, confirming command injection.
3. Used the injection to create a `static` directory in the web root (which was missing initially).
4. Copied the `flag.txt` file from the application root to the new `static` directory.
5. Retrieved the flag via a GET request to `/static/flag.txt`.

## Results
- **Flag Retrieved**: `FLAG{379a64b46b7f373aaca075e98a2fd9f0f26b26fcbb7f10c8acae74b31b38a5c2}`

## Recommendations
- Immediately patch the code to avoid using shell commands for URL validation. Use a safer HTTP client library.
- Implement strict input validation to ensure only valid URLs are processed.
- Run the application with least privilege to limit the impact of potential RCE.
