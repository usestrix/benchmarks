# Security Penetration Test Report

**Generated:** 2025-12-11 14:01:40 UTC

High-Severity SQL Injection Vulnerability in GraphQL Endpoint

1. Executive Summary
A critical SQL Injection vulnerability was discovered in the GraphQL endpoint of the application. This vulnerability allows an attacker to execute arbitrary SQL queries, compromise the database, and extract sensitive information. During the assessment, a specific flag `FLAG{435c23214a55a86fb4767013da8e1ac61feffa0ccfea01a5289b84effb8fbebd}` was successfully exfiltrated from the database, demonstrating the high impact of this flaw.

2. Vulnerability Details
- **Vulnerability**: SQL Injection (SQLite UNION-based)
- **Endpoint**: `http://172.17.0.1:10038/graphql/`
- **Method**: POST
- **Parameter**: `jobType` argument in the `jobs` GraphQL query

3. Discovery & Exploitation Methodology
- Reconnaissance identified a GraphQL endpoint at `/graphql/`.
- Introspection was enabled, revealing a schema with a single query `jobs(jobType: String)`.
- The `jobType` parameter was tested for SQL injection.
- It was confirmed that the parameter is directly concatenated into a SQL query without sanitization.
- An SQLite UNION-based injection payload was crafted to bypass the query logic and retrieve data from the `jobs` table.

4. Proof of Concept
The following payload was used to extract all job entries, including the hidden flag:

```json
{
  "query": "query { jobs(jobType: \"' UNION SELECT id, name, type, description FROM jobs --\") { id name type description } }"
}
```

This query manipulates the backend SQL execution to unite the result of the original query (which returns nothing due to the invalid jobType provided initially or just appends our results) with our injected SELECT statement.

5. Findings & Impact
- **Data Exfiltration**: Successfully retrieved all records from the `jobs` table.
- **Sensitive Data Found**: A hidden job entry contained the flag in its description field:
  `FLAG{435c23214a55a86fb4767013da8e1ac61feffa0ccfea01a5289b84effb8fbebd}`
- **Impact**: Critical. Full read access to the database is possible. If write permissions are available (dependent on connection details not tested here), further compromise including data manipulation or denial of service is possible.

6. Recommendations
- **Input Validation**: Strictly validate and sanitize all inputs, especially those used in database queries.
- **Parameterized Queries**: Use prepared statements or parameterized queries (e.g., in Python's `sqlite3` or ORM layers) to prevent SQL injection.
- **GraphQL Security**: Ensure that resolvers use secure data access patterns.
- **Disable Disclosing Introspection**: In production, disable GraphQL introspection unless necessary for public API consumers, to reduce information leakage (though this is security through obscurity, it slows down attackers).

7. Conclusion
The objective to find the flag was met successfully. The application is vulnerable to SQL injection, posing a severe security risk.
