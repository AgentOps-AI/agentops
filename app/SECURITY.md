# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in AgentOps, please report it responsibly.

### How to Report

1. **Do NOT create a public GitHub issue** for security vulnerabilities
2. **Email us directly** at security@agentops.ai
3. **Include the following information:**
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt of your report within 24 hours
- **Investigation**: We'll investigate and validate the vulnerability
- **Timeline**: We aim to provide an initial response within 72 hours
- **Resolution**: Critical vulnerabilities will be patched within 7 days
- **Credit**: We'll credit you in our security advisories (unless you prefer to remain anonymous)

### Security Best Practices

When deploying AgentOps:

1. **Environment Variables**: Never commit sensitive environment variables to version control
2. **HTTPS**: Always use HTTPS in production
3. **Authentication**: Use strong, unique passwords and enable 2FA where possible
4. **Updates**: Keep dependencies and the platform updated
5. **Access Control**: Follow the principle of least privilege
6. **Monitoring**: Enable logging and monitoring for suspicious activity

### Security Features

AgentOps includes several security features:

- **JWT Authentication**: Secure token-based authentication
- **Role-based Access Control**: Granular permissions system
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against abuse
- **Audit Logging**: Track all user actions
- **Secure Headers**: HTTPS enforcement and security headers

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1**: Acknowledgment sent
3. **Days 1-3**: Investigation and validation
4. **Days 3-7**: Patch development and testing
5. **Day 7**: Security release (for critical issues)
6. **Day 14**: Public disclosure (after users have time to update)

## Security Contacts

- **Security Team**: security@agentops.ai
- **General Contact**: support@agentops.ai

Thank you for helping keep AgentOps secure!
