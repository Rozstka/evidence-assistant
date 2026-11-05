# Security and scope

Local, single-operator portfolio MVP. Synthetic examples only; `synthetic=true` / `SYN-` is an operator declaration, not a detector of personal data.
API endpoints require a generated bearer token (except health and API documentation). Token comparison is constant-time.
`.env`, databases and downloaded data are ignored by Git and Docker. `scripts/configure.py` refuses to overwrite secrets and creates a private file.
Docker binds the API to localhost; PostgreSQL has no host port. Application runs as a non-root user.
Request body, document length, image size and provider output are bounded. Provider calls time out and failures are explicit, never silently replaced by plausible answers.
Ollama base URL is operator configuration, never supplied by a user or tool. No cloud requests are made in demo mode.

This MVP has no multi-tenant authorization, per-user reviewer accounts, distributed rate limits, retention scheduler or encryption at rest.
Do not expose it publicly or load real patient/business data without adding those controls, TLS, monitored backups and an appropriate operational review.
SQLAlchemy `create_all` initializes a fresh schema; versioned migrations are needed before evolving a deployed database.
The shared API token identifies one operator/service. An audit actor is a token fingerprint, not a verified human identity.
Rotate the token by editing `.env` and restarting. Delete a local demo database only when its data are no longer needed.
Never commit `.env` or put credentials in README, images, issue reports or tool traces.
