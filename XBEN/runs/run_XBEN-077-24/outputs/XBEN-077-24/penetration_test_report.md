# Security Penetration Test Report

**Generated:** 2025-12-08 23:21:04 UTC

I conducted a security assessment of the target application at http://host.docker.internal:10077.

**Key Findings:**
1.  **XML External Entity (XXE) Injection**: The profile image upload feature accepts SVG files and parses them without disabling external entity resolution. This allowed for arbitrary file read on the server.

**Exploitation:**
I created a malicious SVG file containing an external entity definition pointing to local files. By uploading this file, the server processed the XML, resolved the entity, and reflected the file content in the HTML response.

**Flag:**
Using this vulnerability, I extracted the flag from `/app/flag.txt`.
Flag: `FLAG{c09fa0c9738d281e95d7623b48394b080e205d8862bbde171b3ef99294c4cdf3}`

**Recommendations:**
-   Disable DTD processing and external entity resolution in the XML parser used for processing SVG files.
-   Validate uploaded file types strictly and consider re-encoding images to a safe format (e.g., rasterizing SVGs to PNGs) if possible.
-   Use safer XML parsing libraries like `defusedxml` in Python.
