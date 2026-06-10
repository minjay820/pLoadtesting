# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please **do not** open a public issue. Instead, report the vulnerability by emailing the maintainers (e.g. security@example.com - placeholder email) or via a private security advisory on GitHub.

We will acknowledge your report and work to address the issue promptly.

---

## 🔒 Confidentiality & Credentials Safeguards

* **Do Not Commit Secrets**: Never paste tokens, credentials, database passwords, internal domain URLs, or target app credentials into issues, Pull Requests, or public comments.
* **Sensitive Target Data**: If a performance/load test requires sensitive production logs or target payloads, sanitize them before publishing sample engine scripts.

---

## ⚠️ Engine & Script Safety Reminders

* **Third-Party Engines**: Be cautious when using customized Docker images, plugins, or wrapper binaries for k6, JMeter, or LoadRunner. Ensure they are sourced from official or trusted registries.
* **Script Review**: Review external user-contributed scripts in `engines/` before running them locally to ensure they do not perform unauthorized file access, data exfiltration, or malicious network requests.

---

## 🛡️ Authorized Load Testing Only

* **Scope**: You must only perform load/stress tests against target applications and infrastructure that you own or are explicitly authorized to test.
* **Compliance**: Running unauthorized load tests can be interpreted as a Denial of Service (DoS) attack. Use this ecosystem responsibly and ethically.
