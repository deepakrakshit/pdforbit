# Security Policy

PdfORBIT handles user documents, authentication, background processing, and payment-related flows.

Security matters in this repository.

## Security-Sensitive Areas

- authentication and token handling
- file upload validation
- file storage and retention
- signed downloads
- worker execution boundaries
- billing verification
- webhook verification
- secret management

## Reporting a Vulnerability

Please report vulnerabilities privately to the maintainer before public disclosure.

Do not open public GitHub issues for security vulnerabilities.

Contact:

- LinkedIn: https://www.linkedin.com/in/deepakrakshit/
- Email: deepakrakshit20@gmail.com

If you do not receive a response within 72 hours via LinkedIn, follow up by email.

Include:

- issue summary
- impact
- reproduction steps
- affected files or routes
- suggested mitigation if known

## Repository Rules

- do not commit secrets
- do not hardcode API credentials
- verify payment details server-side
- verify webhooks server-side
- prefer short-lived signed delivery URLs
- treat AI-generated code as review-required