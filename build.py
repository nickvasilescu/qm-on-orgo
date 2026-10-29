#!/usr/bin/env python3
"""Render template/qm.yaml (an orgo.ai/v1 template) from scripts/ and config/.

    python3 build.py            # writes template/qm.yaml
    orgo templates validate template/qm.yaml
    orgo templates publish template/qm.yaml && orgo templates build default/qm@<version>
"""
from pathlib import Path

import yaml

VERSION = "0.1.7"
QM_VERSION = "0.1.15"  # @yc-software/qm, pinned
ROOT = Path(__file__).parent

SECRETS = [
    ("anthropic_api_key", "ANTHROPIC_API_KEY",
     "Anthropic API key for the agents. Optional: an admin can add any Anthropic, OpenAI or OpenRouter key in Admin > Onboarding instead.",
     "sk-ant-...", "https://console.anthropic.com/settings/keys"),
    ("qm_public_url", "QM_PUBLIC_URL",
     "Serve QM at this https URL, e.g. https://acme-qm.orgo.dev. Point it at port 18081 after launch (README). Leave unset for a private localhost test drive.",
     "https://acme-qm.orgo.dev", None),
    ("resend_api_key", "RESEND_API_KEY",
     "Resend key for email sign-in links, so teammates can sign in. Needs qm_email_from.",
     "re_...", "https://resend.com/api-keys"),
    ("qm_email_from", "QM_EMAIL_FROM",
     "Sender address verified in Resend.", "QM <qm@yourdomain.com>", None),
    ("qm_admin_email", "QM_ADMIN_EMAIL",
     "Your email. Becomes an org admin who can sign in by email.", "you@yourdomain.com", None),
    ("qm_allowed_email_domain", "QM_ALLOWED_EMAIL_DOMAIN",
     "Anyone with an email at this domain may sign in.", "yourdomain.com", None),
]

SCRIPTS = ["qm-env", "orgo-dockerd", "qm-configure", "qm-bake", "qm-start", "qm-watch",
           "qm-open", "qm-public", "qm-email"]

README_ON_BOX = """\
# QM on Orgo

QM (YC's multiplayer agent harness) runs here as a single-host Docker deployment:
core, web UI, admin, Postgres, and one sandbox container per person or room.

  qm-open                 fresh one-time admin sign-in link (5 minutes)
  qm-public https://...   serve QM on a public https URL (point it at port 18081 first)
  qm-public off           back to the private localhost test drive
  qm-email                turn on email sign-in for teammates (Resend)
  cd /opt/qm && npm exec qm -- status | logs core | up | down

Startup log: /var/log/qm-start.log   Settings: /opt/qm/orgo.env
Docs and source: https://github.com/nickvasilescu/qm-on-orgo
"""


class Literal(str):
    pass


yaml.add_representer(Literal, lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", v, style="|"))


def main():
    files = [{"to": "/etc/docker/daemon.json", "mode": "0644", "when": "build",
              "inline": Literal((ROOT / "config/daemon.json").read_text())}]
    for name in SCRIPTS:
        mode = "0644" if name == "qm-env" else "0755"
        files.append({"to": f"/usr/local/bin/{name}", "mode": mode, "when": "build",
                      "inline": Literal((ROOT / "scripts" / name).read_text())})
    files.append({"to": "/opt/qm-template/README-ORGO.md", "mode": "0644", "when": "build",
                  "inline": Literal(README_ON_BOX)})

    t = {
        "api_version": "orgo.ai/v1",
        "template": {
            "name": "qm",
            "version": VERSION,
            "description": "YC's QM multiplayer agent harness, self-hosted on one computer. "
                           "Optional public https URL and email sign-in.",
            "license": "MIT",
            "homepage": "https://github.com/nickvasilescu/qm-on-orgo",
            "source": "https://github.com/yc-software/qm",
        },
        "hardware": {"cpu": 4, "ram_gb": 16, "disk_gb": 60, "resolution": "1280x800x24"},
        "secrets": [dict({"name": n, "description": d, "example": e, "optional": True},
                         **({"docs_url": u} if u else {})) for n, _, d, e, u in SECRETS],
        "env": {var: {"secret": n} for n, var, *_ in SECRETS},
        "build": {
            "apt": ["iptables", "kmod", "openssl", "jq", "curl", "ca-certificates", "git", "python3"],
            "run": [
                "curl -fsSL https://deb.nodesource.com/setup_24.x | bash -",
                "DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs",
                "npm install -g npm@latest",
                "curl -fsSL https://get.docker.com | sh",
                "mkdir -p /opt/qm",
                f"cd /opt/qm && git init -q && npm exec --yes --package=@yc-software/qm@{QM_VERSION} -- "
                "qm init . --org orgo --target docker </dev/null",
                "cp /opt/qm-template/README-ORGO.md /opt/qm/README-ORGO.md",
                "cd /opt/qm && npm install --no-audit --no-fund",
                "/usr/local/bin/qm-bake",
            ],
        },
        "files": files,
        "apps": [
            {"name": "docker", "title": "Docker Engine",
             "description": "Runs QM's services and one isolated container per agent scope.",
             "services": [{"name": "dockerd", "run": "/usr/local/bin/orgo-dockerd", "user": "root",
                           "restart": "always", "log": "/var/log/dockerd.log"}]},
            {"name": "qm", "title": "QM",
             "description": "YC's multiplayer agent harness. Portal on port 18081.",
             "requires": ["docker"], "data": ["/opt/qm"],
             "services": [{"name": "qm-watch", "title": "QM launcher",
                           "description": "Starts QM on each launch of this template.",
                           "run": "/usr/local/bin/qm-watch", "user": "root",
                           "restart": "always", "log": "/var/log/qm-watch.log"}],
             "ports": [{"internal": 18081, "protocol": "http", "public": False,
                        "description": "QM portal (sign-in, web chat, admin)"}]},
        ],
        "terminal": [{"name": "qm", "title": "QM", "cwd": "/opt/qm",
                      "run": "cat /opt/qm/README-ORGO.md; tail -n 20 -F /var/log/qm-start.log"}],
        # Kept for when Orgo fires on_resume; qm-watch is what actually triggers today.
        "hooks": {"on_resume": "setsid /usr/local/bin/qm-start </dev/null >/dev/null 2>&1 &\n"},
    }
    out = ROOT / "template" / "qm.yaml"
    out.parent.mkdir(exist_ok=True)
    header = ("# Generated by build.py from scripts/ and config/. Edit those, then rebuild.\n"
              "# yaml-language-server: $schema=https://www.orgo.ai/api/template-schema\n")
    out.write_text(header + yaml.dump(t, sort_keys=False, width=120, allow_unicode=True))
    print(f"wrote {out} (qm@{VERSION})")


if __name__ == "__main__":
    main()
