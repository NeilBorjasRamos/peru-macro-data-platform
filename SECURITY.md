# Security and data handling
Use example credentials only in a disposable local environment.
PostgreSQL is bound to loopback in Compose. Never expose it publicly with sample credentials.
Keep DATABASE_URL, .env, runtime logs and database files out of Git.
Telemetry is disabled for orchestrated dbt and CI.

Integration fixtures intentionally DROP project schemas in TEST_DATABASE_URL.
Use an isolated test database, never production or your only copy of data.

Report suspected vulnerabilities privately via GitHub reporting if enabled.
Do not attach credentials or private data to public issues. No production
response-time commitment, authentication layer or hardened cloud deployment is offered.
