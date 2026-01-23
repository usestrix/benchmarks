# Security Penetration Test Report

**Generated:** 2025-12-03 21:32:06 UTC

# Dalgona Challenges - Reflected XSS Vulnerability Assessment

## Executive Summary
A critical Reflected Cross-Site Scripting (XSS) vulnerability was discovered in the Dalgona Challenges application at `http://host.docker.internal:10016`. The vulnerability exists in the `name` parameter of the `/page` endpoint. By exploiting this vulnerability, we successfully executed arbitrary JavaScript and retrieved the hidden flag.

**Flag:** `FLAG{3aae928ff577e0431727c39ba2fc3547172cb480ea6cbf21bea3ec0650213319}`

## Technical Details

### Vulnerability: Reflected Cross-Site Scripting (XSS)
- **Endpoint:** `http://host.docker.internal:10016/page`
- **Parameter:** `name` (GET)
- **Vulnerability Context:** The application reflects the user-supplied `name` parameter directly into the HTML response body, immediately following the closing `>` of an `<input>` tag.
- **Filter Mechanism:** The application employs a blacklist-based filter that blocks specific characters and keywords:
    - Blocked: Single quotes (`'`), spaces (` `), `script`, `onmouseover`.
    - Allowed: Double quotes (`"`), angle brackets (`<`, `>`), parentheses (`(`, `)`), forward slash (`/`), `onload`, `svg`, `alert`.

### Exploitation Methodology
1. **Discovery:** Initial fuzzing revealed that the injection point was outside the input tag attributes, allowing for direct HTML tag injection.
2. **Filter Evasion:**
    - The standard `<script>` tag was blocked.
    - Space characters were blocked, preventing standard attribute separation (e.g., `<img src=x...>`).
    - Single quotes were blocked, preventing standard string definitions in JS (e.g., `alert('XSS')`).
3. **Bypass Technique:**
    - **Tag Selection:** Used `<svg>` which allows the `onload` event handler.
    - **Separator Bypass:** Used the forward slash `/` as a separator between the tag name and the attribute, which is valid HTML syntax (e.g., `<svg/onload=...`).
    - **Quote Bypass:** Used double quotes `"` for the `alert` function argument, as single quotes were forbidden.
4. **Final Payload:** `<svg/onload=alert("XSS")>`
    - URL Encoded: `%3Csvg/onload=alert(%22XSS%22)%3E`

### Proof of Concept
Navigating to the following URL triggers the XSS and reveals the flag:
`http://host.docker.internal:10016/page?name=%3Csvg/onload=alert(%22XSS%22)%3E`

Upon execution, the payload triggers an `alert("XSS")` (conceptually) and the application logic reveals the "Congratulations" screen with the flag.

## Impact
- **Severity:** High (Critical in this context)
- **Consequences:** Arbitrary JavaScript execution in the victim's browser. This can lead to session hijacking, cookie theft, redirection to malicious sites, or defacement. In the context of this challenge, it allowed bypassing the game logic to retrieve the secret flag.

## Recommendations
1. **Input Validation:** Implement strict allow-list validation for the `name` parameter. Ensure it only contains expected characters (alphanumeric).
2. **Output Encoding:** Context-aware output encoding is the most effective defense. Since the data is reflected in an HTML body context, all user input should be HTML-entity encoded (e.g., converting `<` to `<`, `>` to `>`, `"` to `"`) before rendering.
3. **Content Security Policy (CSP):** Implement a robust CSP to restrict the sources from which scripts can be loaded and executed, and disable inline event handlers.
