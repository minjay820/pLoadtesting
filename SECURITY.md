# Security Policy

> [!IMPORTANT]
> **Authorized Testing Only Disclaimer**
> This project is designed exclusively for authorized performance, load, and stress testing. Users must only target applications and systems they own or have explicit permission to test. Running unauthorized tests can be interpreted as a Denial of Service (DoS) attack or unauthorized intrusion. Use this ecosystem responsibly and ethically.

## ⚠️ Internet Exposure Warning

The current preview version of `pLoadtesting` is in an early-stage development phase.
* **Do Not Deploy Publicly**: The Control Plane and Worker Agent currently use a shared preview API token model. This is not a production-grade scoped authorization system.
* **Do Not Expose Endpoints**: Do not expose any Control Plane or Worker endpoints to the public internet. Ensure all communications occur within a private, isolated network such as a VPN, VPC, or lab subnet.
* **Use Bounded Targets Only**: The bundled target apps are intended for local, CI, and controlled internal validation. Do not point tests at third-party systems or unapproved targets.

---

## 🔒 Confidentiality & Credentials Safeguards

* **Do Not Commit Secrets**: Never paste secrets, tokens, access credentials, internal database passwords, internal URLs, or customer targets/payloads into public issues, Pull Requests, or comments.
* **Sanitize Inputs**: Before sharing sample performance testing scripts or configuration schemas, verify that all target domains, API keys, and sensitive data payloads are sanitized or replaced with placeholders.
* **Use Placeholders In Docs**: Documentation, examples, and roadmap drafts should use placeholders instead of real deployment values.
* **Review Load Scripts**: Treat contributed k6 scripts, JMeter plans, and runtime parameters as executable inputs that require review before use.

---

## Current Preview Access Boundary

The current Control Plane accepts a shared preview value through either:

* `Authorization: Bearer <preview-token>`
* `X-PLOADTESTING-API-TOKEN: <preview-token>`

The Worker Agent also validates dispatch requests to `/execute` with the shared preview value. This mechanism is suitable for local and controlled preview deployments only. A scoped API access model is planned in [docs/v3/specs/api-token-auth.md](docs/v3/specs/api-token-auth.md).

---

## 🛠️ Planned Security Controls (Roadmap)

To prepare `pLoadtesting` for secure deployment, the following features are planned for future milestones:
* **Scoped API Access**: Separate scopes for reading tasks, creating tasks, reading templates, registering workers, posting results, and administering access.
* **Worker Registration Controls**: Dedicated worker registration and heartbeat scopes for Worker Agents.
* **Target Allowlist**: A Control Plane configuration setting that restricts load-test target URLs to a specified allowlist.
* **Audit Logs**: Comprehensive logging of test runs, configuration changes, and system access.
* **Rate Limits**: Active rate limiting on control plane APIs to prevent resource exhaustion.
* **Network Hardening**: Deployment guidance for private subnets, TLS termination, and restricted Worker-to-target network paths.

---

## ⚠️ Third-Party Engine Safety

* **Third-Party Engines**: Be cautious when running custom Docker images, plugins, or third-party wrappers for k6, JMeter, or LoadRunner. Ensure they are obtained from official or trusted sources.
* **Script Review**: Manually inspect all user-contributed scripts in `engines/` before execution to confirm they do not execute unauthorized files or carry out malicious activities.
* **License Review**: Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing packaged images, scripts, or scenario assets.

---

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please **do not** open a public issue. Instead, report the vulnerability using GitHub private vulnerability reporting if enabled, or contact the maintainer via the email listed on the GitHub profile.

We will acknowledge your report and work to address the issue promptly.
