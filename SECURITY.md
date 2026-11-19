# Security

## Reporting a vulnerability

Please report security problems privately. Use the **Report a vulnerability** button on this repo's
[Security tab](https://github.com/nickvasilescu/qm-on-orgo/security/advisories/new).

Please don't post vulnerabilities in YouTube comments, social media, or public issues. A public post gives
attackers a head start before a fix exists.

Include what you found, how to reproduce it, and what an attacker could do with it. Only the `main` branch is
supported. Responses are best effort; this is a personal open-source project.

## Using it safely

- `launch.sh` uses your Orgo API key on your own machine only; it is never copied to the computer. Even so,
  prefer a workspace-scoped key (`orgo api-keys create --workspace <id>`) over your main account key.
- Leave QM on the localhost test drive until you need a public URL, and restrict who can sign in
  (`QM_ADMIN_EMAIL`, `QM_ALLOWED_EMAIL_DOMAIN`, `QM_ALLOWED_EMAILS`).
- Treat the one-time admin link as a password.
- For vulnerabilities in QM itself, report to QM's maintainers: see
  [QM's SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md).
- Never show API keys on screen, in recordings, in screenshots or in chat logs. If one was shown, revoke it.
