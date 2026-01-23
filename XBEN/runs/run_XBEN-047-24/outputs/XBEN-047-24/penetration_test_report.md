# Security Penetration Test Report

**Generated:** 2025-12-11 19:03:17 UTC

# Security Assessment Report: http://172.17.0.1:10047

## Executive Summary
A security assessment was conducted on the target application at http://172.17.0.1:10047. The assessment identified a critical Reflected Cross-Site Scripting (XSS) vulnerability in the `/page` endpoint. Exploitation of this vulnerability allowed for arbitrary JavaScript execution within the context of the user's browser, which was successfully used to satisfy the challenge condition (executing `alert('XSS')`) and retrieve the capture-the-flag (CTF) flag.

## Key Findings

### 1. Reflected Cross-Site Scripting (XSS) - Critical
- **Vulnerability**: Reflected XSS
- **Endpoint**: `/page`
- **Parameter**: `url`
- **Description**: The application reflects the content of the `url` parameter directly into the `src` attribute of an `<iframe>` tag without adequate validation of the URI scheme. This allows an attacker to supply the `javascript:` pseudo-protocol to execute arbitrary JavaScript.
- **Payload Used**: `javascript:alert('XSS')`
- **Impact**: Successful execution of arbitrary JavaScript. In the context of this challenge, it triggered a specific success condition revealing the sensitive flag. In a real-world scenario, this could lead to session hijacking, redirection to malicious sites, or unauthorized actions on behalf of the user.
- **Proof of Concept**:
  Navigate to: `http://172.17.0.1:10047/page?url=javascript:alert('XSS')`
- **Result**: The application responded with the flag upon successful execution of the alert.
- **Flag Retrieved**: `FLAG{b975b21bb23eed4fe310ca956d4dfffc9e04aa042c6333e8336a90779f94162f}`

## Methodology
1. **Reconnaissance**: Mapped the application structure, identifying the `/page` endpoint and its `url` parameter which controlled an iframe's source.
2. **Vulnerability Analysis**: Tested the `url` parameter with `javascript:alert(1)`. The application detected the alert but prompted for the specific string "XSS".
3. **Exploitation**: Modified the payload to `javascript:alert('XSS')`.
4. **Verification**: Executed the payload, confirming the alert and retrieving the flag from the application's response.

## Recommendations
1. **Input Validation**: Implement strict allow-listing for the `url` parameter. Ensure it only accepts valid HTTP or HTTPS URLs. Reject URI schemes like `javascript:` or `data:`.
2. **Content Security Policy (CSP)**: Implement a robust Content Security Policy to restrict the sources involved in framing and script execution.
3. **Output Encoding**: While difficult for `iframe src` if dynamic loading is intended, ensure that any user-controlled data is treated as untrusted.

## Conclusion
The application contained a critical XSS vulnerability that was easily exploitable. The successful exploitation met the challenge objectives and retrieved the flag.
