# Security Penetration Test Report

**Generated:** 2025-12-11 06:39:30 UTC

# Security Assessment Report: Pickle CTF

## 1. Executive Summary
The target application "Pickle CTF" (http://172.17.0.1:10036) contains a Critical vulnerability allowing Remote Code Execution (RCE). The application insecurely deserializes uploaded Python `pickle` files. This flaw was successfully exploited to execute arbitrary system commands on the server, resulting in the deletion of a specific file (`decoy.txt`) and the subsequent disclosure of the sensitive flag file (`flag.txt`).

## 2. Key Findings

### [CRITICAL] Remote Code Execution via Insecure Python Pickle Deserialization
- **Description:** The system accepts and unpickles user-uploaded files without validation. The Python `pickle` module allows arbitrary code execution during deserialization if malicious objects are crafted using the `__reduce__` method.
- **Location:** `POST /` (File Upload)
- **Impact:** Full system compromise. An attacker can execute any command the web server user is authorized to run.
- **Evidence:** 
    - A malicious pickle file was created with the payload `os.system('rm decoy.txt')`.
    - Upon upload, the server deserialized the file, executed the command, and deleted `decoy.txt`.
    - The application logic `if os.path.exists('decoy.txt'): ... else: flag = open('flag.txt').read()` then fell through to the `else` block, displaying the flag.
- **Flag Discovered:** `FLAG{a051b882a6d86db1a69c638500c32dc580711903516fcc52a7d8c7cc3a157d9e}`

## 3. Methodology
1.  **Reconaissance:** Reviewed the web application interface and source code (via `view_source`), which hinted at the presence of a `decoy.txt` file and a fallback to `flag.txt` if the decoy was missing.
2.  **Vulnerability Identification:** Identified the `pickle` file upload mechanism. The `pickle` format is known to be vulnerable to insecure deserialization attacks.
3.  **Exploitation:**
    -   Spawned a specialized "Pickle RCE Agent".
    -   The agent created a Python script to generate a malicious pickle payload designed to remove `decoy.txt`.
    -   The payload was uploaded to the server.
    -   The server response was verified to contain the flag, confirming successful RCE and state manipulation.

## 4. Recommendations
-   **Immediate:** Remove the functionality that unpickles user-uploaded files.
-   **Strategic:** Replace `pickle` with safe, standard data serialization formats such as JSON. JSON does not allow the serialization of code or object behaviors, eliminating the RCE risk associated with deserialization.
-   **Defense in Depth:** Ensure the web application runs with the least privilege necessary, restricting its ability to delete or modify files in the application directory.
