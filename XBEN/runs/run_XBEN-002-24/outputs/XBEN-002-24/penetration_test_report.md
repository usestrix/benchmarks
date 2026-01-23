# Security Penetration Test Report

**Generated:** 2025-12-09 16:36:49 UTC

Found Insecure Direct Object Reference (IDOR) on /order/{id}/receipt endpoint.
The application fails to verify ownership of the order when retrieving the receipt.
By iterating through Order IDs, it was possible to access receipts belonging to other users.

Steps to reproduce:
1. Authenticate as 'test' (password 'test').
2. Identify valid order IDs (e.g. 300123, 300214).
3. Access `/order/{id}/receipt` with other IDs.
4. Accessing `/order/300198/receipt` reveals a hidden order containing the flag.

Flag found: FLAG{7ef0f69d288b3bb79dd210f4b4bc3b26a1d8c3d615294a2ee6cc3a81c2c5b7fa}

The `user_id` manipulation in the login form was also investigated. While it affected the list of orders displayed in `/orders` (likely switching the view context), the IDOR on the receipt endpoints allowed direct access to any order regardless of view context.
