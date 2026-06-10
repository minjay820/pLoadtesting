# Security Policy

> [!IMPORTANT]
> **Authorized Testing Only Disclaimer**
> This project is designed exclusively for authorized performance, load, and stress testing. Users must only target applications and systems they own or have explicit permission to test. Running unauthorized tests can be interpreted as a Denial of Service (DoS) attack or unauthorized intrusion. Use this ecosystem responsibly and ethically.

## ⚠️ Internet Exposure Warning

The current preview version of `pLoadtesting` is in an early-stage development phase.
* **Do Not Deploy Publicly**: Currently, there are no authentication, authorization, or access control mechanisms implemented in the Control Plane or Worker Agent APIs.
* **Do Not Expose Endpoints**: Do not expose any Control Plane or Worker endpoints to the public internet. Ensure all communications occur within a private, isolated network (e.g. VPN, VPC).

---

## 🔒 Confidentiality & Credentials Safeguards

* **Do Not Commit Secrets**: Never paste secrets, tokens, access credentials, internal database passwords, internal URLs, or customer targets/payloads into public issues, Pull Requests, or comments.
* **Sanitize Inputs**: Before sharing sample performance testing scripts or configuration schemas, verify that all target domains, API keys, and sensitive data payloads are sanitized or replaced with placeholders.

---

## 🛠️ Planned Security Controls (Roadmap)

To prepare `pLoadtesting` for secure deployment, the following features are planned for future milestones:
* **Authentication**: API key and JWT (JSON Web Token) authentication for all Control Plane REST and WebSocket endpoints.
* **Role-Based Access Control (RBAC)**: Fine-grained access privileges for managing workers, creating test scenarios, and executing runs.
* **Worker Registration Tokens**: Secure registration tokens to authorize new worker agents connecting to the Control Plane.
* **Target Allowlist**: A Control Plane configuration setting that restricts load-test target URLs to a specified allowlist.
* **Audit Logs**: Comprehensive logging of test runs, configuration changes, and system access.
* **Rate Limits**: Active rate limiting on control plane APIs to prevent resource exhaustion.

---

## ⚠️ Third-Party Engine Safety

* **Third-Party Engines**: Be cautious when running custom Docker images, plugins, or third-party wrappers for k6, JMeter, or LoadRunner. Ensure they are obtained from official or trusted sources.
* **Script Review**: Manually inspect all user-contributed scripts in `engines/` before execution to confirm they do not execute unauthorized files or carry out malicious activities.

---

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please **do not** open a public issue. Instead, report the vulnerability by emailing the maintainers (e.g. security@example.com - placeholder email) or via a private security advisory on GitHub.

We will acknowledge your report and work to address the issue promptly.
