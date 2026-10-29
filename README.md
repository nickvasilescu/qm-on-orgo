# QM on Orgo

Run [QM](https://github.com/yc-software/qm), Y Combinator's open-source multiplayer agent harness, on a single [Orgo](https://orgo.ai) cloud computer. You get QM's core, web UI, admin console, Postgres, and one isolated sandbox container per person or room. Optionally, add a public `https://` URL and email sign-in so your whole team can use it.

> QM's Docker target is designed as a single-host deployment. This template makes it one launch. For a large team, run QM's own Fly or AWS deployment.

## One command: your own QM at your own URL

Once the template is in your account (step 1 below), this launches a dedicated computer, gives it `https://<name>.orgo.dev`, switches QM to that URL, and prints your admin sign-in link:

```bash
export ORGO_API_KEY=sk_live_...     # orgo.ai → Settings → API keys
bash launch.sh acme-qm               # → https://acme-qm.orgo.dev
```

Every user picks their own name. `.orgo.dev` names are shared across all Orgo accounts, so if yours is taken the script adds a short suffix (`acme-qm-7f3a`); run it with no name to get `qm-xxxx`. Each account gets 10 free names.

It needs `bash`, `curl` and `python3`. Your API key stays on your machine and is never copied to the computer. It takes about 4 minutes.

## Quick start (manual)

1. **Get the template into your account.** Templates live in a per-account namespace. If Orgo lists QM among its curated templates, use that ref. Otherwise, publish it from this repo; that needs an Orgo plan that can publish templates.

   ```bash
   npm i -g orgo && orgo login
   git clone https://github.com/nickvasilescu/qm-on-orgo && cd qm-on-orgo
   orgo templates publish template/qm.yaml && orgo templates build default/qm@0.1.7
   ```

2. **Launch** a computer from it:

   ```bash
   orgo templates run default/qm@0.1.7
   ```

   Or use the Orgo dashboard, or `POST /api/computers` with `"template_ref": "default/qm@0.1.7"`.

3. **Wait about 3 minutes.** The first launch pulls QM's images.

4. **Sign in.** Chrome on the computer opens a one-time admin sign-in. If you missed it, open the **QM** terminal tab and run `qm-open`.

5. **Add a model key** in **Admin → Onboarding → Base model**. Anthropic, OpenAI and OpenRouter all work. You can skip this step by setting the `anthropic_api_key` secret at launch.

6. **Chat.** Every person and room gets its own sandbox container, with Claude Code, Codex, `gh`, git, Node and Python preinstalled.

## Public URL (optional)

Every Orgo workspace gets free names under `orgo.dev`. To serve QM at one:

1. Point a public URL at port **18081**, QM's portal and front door:

   ```bash
   curl -X POST https://www.orgo.ai/api/computers/$COMPUTER_ID/public-urls \
     -H "Authorization: Bearer $ORGO_API_KEY" -H "Content-Type: application/json" \
     -d '{"port": 18081, "label": "acme-qm"}'
   # -> {"url": "https://acme-qm.orgo.dev", ...}
   ```

2. Switch QM to that URL. In the computer's **QM** terminal, run:

   ```bash
   qm-public https://acme-qm.orgo.dev
   ```

   Alternatively, set the `qm_public_url` secret when you launch, then do step 1.

QM restarts in production mode behind Orgo's edge, with a Let's Encrypt certificate. Only the portal (port 18081) is reachable from the internet. Core, the web UI and admin stay firewalled. To go back to the private localhost mode, run `qm-public off`.

You can also use a domain you own or buy through Orgo. Attach it with `POST /api/computers/{id}/domains`, then pass that URL to `qm-public`.

## Email sign-in for your team (optional)

Without email, only one-time admin links (`qm-open`) can sign people in. To let teammates sign in with email links, use [Resend](https://resend.com):

```bash
qm-email
```

`qm-email` prompts for four things:

- your Resend API key, entered silently
- a sender address on a domain verified in Resend
- your admin email
- optionally, a domain such as `acme.com`, so anyone @acme.com can sign in

Set up the public URL first, so the sign-in links work outside the computer. You can also provide all of this as launch secrets (see below). To turn email sign-in off again, run `qm-email off`.

## Launch secrets

Every secret is optional. Set them in your Orgo vault; they're injected when the computer is created.

| Secret | What it does |
|---|---|
| `anthropic_api_key` | Base model key, so QM can answer immediately |
| `qm_public_url` | Serve at this https URL, e.g. `https://acme-qm.orgo.dev` (point it at port 18081 after launch) |
| `resend_api_key` | Turns on email sign-in links (needs `qm_email_from`) |
| `qm_email_from` | Sender verified in Resend, e.g. `QM <qm@acme.com>` |
| `qm_admin_email` | Your email, which becomes an org admin who can sign in by email |
| `qm_allowed_email_domain` | Anyone @this domain may sign in |

## Commands on the computer

| Command | Does |
|---|---|
| `qm-open` | Prints, and opens in Chrome, a one-time admin sign-in link valid for 5 minutes |
| `qm-public [url\|off]` | Shows or changes the public URL |
| `qm-email [off]` | Turns email sign-in on or off |
| `qm-start` | Re-applies settings and brings QM up (idempotent) |
| `cd /opt/qm && npm exec qm -- status \| logs core \| down \| up` | QM's own CLI |

Logs are in `/var/log/qm-start.log`. Settings are in `/opt/qm/orgo.env` (mode 600). Per-computer signing secrets are generated on first start and are never part of the template.

## How it works

- `template/qm.yaml` is an [`orgo.ai/v1`](https://docs.orgo.ai/guides/templates/schema) template, generated by `build.py` from `scripts/` and `config/`.
- **Build:**
  1. The build installs Node 24 and Docker, then runs `qm init --target docker` with `@yc-software/qm` pinned.
  2. It switches Docker to the classic `overlay2` store, which roughly halves disk use.
  3. If the build box has room, it pre-pulls QM's images.
- **Launch:**
  1. A launch restores a memory snapshot.
  2. A small watcher (`qm-watch`) notices the clock jump and runs `qm-start`.
  3. `qm-start` mints per-computer secrets, renders the config with `qm-configure`, sets the firewall, runs `qm up`, and opens the admin sign-in.
- **Platform workarounds:**
  - It mounts `cgroup2`, which Orgo computers boot without.
  - It runs Docker as root.
  - It unsets a stale `XDG_RUNTIME_DIR`.
  - It moves QM to ports 18080–18083, because Orgo uses 8080.
- **QM fix:** QM 0.1.15's core never reads `QM_CORE_CONTAINER` into its local-sandbox config, so it dials sandboxes at `127.0.0.1` from inside its own container and every agent command is refused. `qm-start` patches one line into core after each `qm up`. It becomes a no-op once QM fixes this upstream.

### Rebuild and publish

You need an Orgo plan that can publish templates (Scale or above).

```bash
python3 build.py
orgo templates validate template/qm.yaml
orgo templates publish template/qm.yaml
orgo templates build default/qm@0.1.7
```

To bump the pinned QM version, change `QM_VERSION` in `build.py` and bump `VERSION`.

## Security notes

- QM agents can run commands in their sandboxes, and QM's command policy and approvals still apply. Read QM's [SECURITY.md](https://github.com/yc-software/qm/blob/main/SECURITY.md) before giving it real credentials.
- Only port 18081 is exposed, and only in public-URL mode. Sandboxes reach core over Docker's internal network.
- On the local Docker backend, QM can't enforce egress rules for sandboxes. Its admin page says so.
- The one-time admin link is a credential. Don't paste it anywhere public.

## License

MIT. QM itself is MIT-licensed by Y Combinator. This repo is just packaging.
