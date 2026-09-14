# Security policy

Job Hunter is a single-user local application. The supported tester setup is a separate installation per person, with the default localhost-only ports and live submission disabled. Public hosting, shared instances and untrusted local users are outside the supported security boundary.

Report suspected security issues privately using the repository's GitHub **Security → Report a vulnerability** option if available. If that option is unavailable, contact the maintainer privately before sending reproduction material. Do not post credentials, resumes, profiles or exploit details containing personal data in public issues.

Include the commit/version, OS, installation method and a minimal reproduction using fictitious data. The project has no guaranteed security-response SLA during the tester phase.

The latest bounded review and known limitations are recorded in [docs/SECURITY_REVIEW.md](docs/SECURITY_REVIEW.md). A passing dependency scan is not proof that the software has no vulnerabilities.
