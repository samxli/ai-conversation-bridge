# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it using [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability). Go to the **Security** tab of this repository and click **Report a vulnerability**.

Please include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

> **Note:** This is a community reference architecture, not a Workday product. Security reports are handled by project maintainers on a best-effort basis.

## Security Considerations

This project handles sensitive data including:

- **OAuth tokens** — LINE WORKS JWT-based authentication
- **API keys** — LLM provider and MCP credentials
- **User messages** — Conversation content from enterprise messaging platforms

### Best Practices

- Never commit `.env` files or API keys to version control (`.gcloudignore` excludes them from Cloud Build source archives)
- Use environment variables or secret managers for all credentials
- Deploy the bridge service behind HTTPS in production
- Restrict MCP server access to the bridge service (and authenticate production MCP endpoints)
- Regularly rotate API keys and tokens
- Use official Workday MCP servers (Agent Gateway) instead of the demo server in production
- Set `LW_API_20_BOT_SECRET` for LINE WORKS signature verification; treat DingTalk's `DINGTALK_ALLOWED_USERS` filter as demo-only without additional ingress controls

For detailed technical hardening recommendations (rate limiting, PII redaction, retry logic, prompt injection defenses, observability, and more), see the [Enterprise Hardening Guide](docs/enterprise-guide.md).

For v0.2.0 channel-auth and in-memory state limits, see [Changelog — Known limitations](CHANGELOG.md#known-limitations).
