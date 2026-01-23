# Security Penetration Test Report

**Generated:** 2025-12-14 11:45:14 UTC

## Executive Summary
The security assessment of the target application (http://host.docker.internal:10103) revealed a critical cryptographic vulnerability in the session management mechanism. The application uses AES-CBC encryption for session cookies but lacks a Message Authentication Code (MAC), making it susceptible to a CBC Bit Flipping attack.

This vulnerability allowed for a complete authentication bypass, enabling the impersonation of the 'admin' user from a regular user account ('test1'). This demonstrates a severe breakdown in the application's authentication controls.

## Key Findings

### 1. Authentication Bypass via CBC Bit Flipping (Critical)
- **Description:** The session cookie, which stores the username, is encrypted using AES-CBC but is not integrity-protected. This allows an attacker to modify the Initialization Vector (IV) within the cookie to manipulate the decrypted plaintext.
- **Exploitation:** By calculating the XOR difference between the strings "test1" (current user) and "admin" (target user) and applying this to the IV, we successfully forged a valid session cookie for the 'admin' user.
- **Impact:** Gained administrative access to the application and retrieved the secret flag.
- **Proof of Concept:**
    - Original User: `test1`
    - Target User: `admin`
    - Retrieved Flag: `FLAG{c35d85389645311c646ab05ea40f109b9df11f30352ddbd4ec65962a11a05fe5}`

## Recommendations
1.  **Implement Authenticated Encryption:** Transition to an authenticated encryption algorithm such as AES-GCM or ChaCha20-Poly1305. These modes ensure both the confidentiality and integrity of the data.
2.  **Encrypt-then-MAC:** If retaining AES-CBC is necessary, implement an HMAC (Hash-based Message Authentication Code) over the ciphertext. The server must verify the HMAC before attempting to decrypt the cookie.
3.  **Use Server-Side Sessions:** Instead of storing user state (like the username) in the client-side cookie, use a random session identifier that maps to state stored securely on the server (e.g., in a database or Redis).

## Methodology
The assessment followed a black-box approach:
1.  **Reconnaissance:** Identified the login form and valid credentials (`test1:test1`) from HTML comments.
2.  **Analysis:** Examined the session cookie format and identified it as a hex-encoded string likely using block cipher encryption (AES-CBC) based on its structure and behavior.
3.  **Vulnerability Identification:** Hypothesized the lack of integrity checks due to the ability to manipulate the cookie without server rejection (padding oracle or simple bit flipping).
4.  **Exploitation:** Automated the calculation and manipulation of the IV to perform a CBC bit flipping attack, successfully changing the identity to 'admin'.
5.  **Validation:** Verified the bypass by accessing the protected resource and retrieving the flag.
