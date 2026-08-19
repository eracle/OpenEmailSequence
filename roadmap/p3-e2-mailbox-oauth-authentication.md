# Mailbox Auth: What OAuth Would Cost, And What Has To Happen First

> ## 📥 Inherited from OpenOutreach, 2026-08-19. **Its trigger now points here, and only here.**
>
> The card is deliberately unscheduled — *"Low today, Critical the day the trigger fires"*, the trigger
> being Google restricting app passwords. `Mailbox`, SMTP and IMAP are all in `cold_outreach/` now, so
> when that day comes it is this project that breaks, not the finder.
>
> **One thing changed on the way over, and it is good news.** This card used to gate OpenOutreach's
> hosted launch: you could not sell a hosted product that asks strangers for an app password. A hosted
> *finder* sends nothing, so that gate is gone and hosted OpenOutreach now needs only signup and
> Stripe. The OAuth question is no longer on anybody's critical path — it is a resilience card for
> whenever this side grows a real BYO-mailbox transport.

- **Status:** To Do — **deliberately not scheduled** (see *Trigger*)
- **Priority:** Low today, Critical the day the trigger fires
- **Effort:** Medium
- **Area:** Onboarding / Email transport

> A research card, not a work item. Researched 2026-08-12; every constraint below
> was verified against Google's live documentation rather than recalled, because
> this area has moved repeatedly and most published advice is stale.

## User Story

As an OpenOutreach operator, I want to connect my mailbox without pasting a
password — so that I am not blocked when my provider retires password auth, and so
that setup does not require me to trust a text field with permanent mailbox access.

## Where we are today

`Mailbox` holds `host / port / username / password`. One app password serves both
`imap.gmail.com:993` (read) and `smtp.gmail.com:587` (send). Setup is ~2 minutes:
enable 2SV, generate, paste. **It works, on every provider.**

## The finding that decides this card

OAuth does **not** require the Gmail API. IMAP and SMTP both support OAuth2 via
SASL `XOAUTH2`, so the generic `Mailbox` model survives:

```python
auth = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
imap.authenticate("XOAUTH2", lambda _: auth.encode())   # imaplib
smtp.auth("XOAUTH2", lambda _: auth)                    # smtplib
```

`XOAUTH2` is also Microsoft's mechanism for Exchange Online, so one auth path
covers both major providers while staying on IMAP. Going Gmail-API-native would
buy narrower scopes but fork the codebase the moment an operator arrives on
Outlook.

### But it forces the widest possible Google scope

IMAP/POP/SMTP OAuth requires `https://mail.google.com/`, which Google classifies
as **restricted**. There is no narrower path: `gmail.send` *cannot* be used over
SMTP. Google's own guidance says apps that do not need the full scope should
"migrate to the Gmail API and use more granular restricted scopes", and that
approval requires demonstrating "full utilization" of it.

### Only one consent flow still exists

| flow | status |
|---|---|
| Device flow (`google.com/device` + code) | **Unavailable** — allowed scopes are `openid`/`email`/`profile`, Drive `appdata`/`file`, YouTube only. No Gmail scope. |
| OOB (show a code, paste it back) | **Dead** — blocked Oct 2022, removed Jan 2023, returns `invalid_request`. |
| Loopback redirect | **The only option.** Supported for desktop apps. |

So the UX is necessarily: print a URL → operator clicks → browser consents →
Google redirects to `127.0.0.1:<port>` → a one-shot local server catches the code.
`google-auth-oauthlib`'s `InstalledAppFlow.run_local_server()` implements it;
`access_type=offline` + `prompt=consent` are required or no refresh token comes
back. `rich` is already a dependency and can render the URL as a real clickable
hyperlink.

## The actual decision: who owns the OAuth client

This is the whole cost question, and it is not a technical one.

**If the operator registers their own client** — no verification, no cost, no cap,
failures are isolated per operator. But setup becomes ~15 minutes of GCP console
work (project → enable API → consent screen → publishing status → Desktop client)
before they send a single email. That is a brutal onboarding step next to a
2-minute app password.

There is also a trap: an External app left in **Testing** has its refresh tokens
**revoked every 7 days** — a daemon that dies weekly. Escape is publishing status
**In Production** (indefinite refresh tokens) or user type **Internal** on
Workspace.

**If OpenOutreach ships one client** — the operator experience is exactly the one
we want: click a link, consent, done. Price:

| | |
|---|---|
| CASA Tier 2 assessment | **mandatory** for restricted scopes |
| cost | ~$540–$1,000/yr via self-serve approved labs (down from $15k–75k) |
| timeline | 4–12+ weeks to approval |
| renewal | annual re-verification |
| unverified fallback | works, but ~100-user cap and a *"Google hasn't verified this app → Advanced → (unsafe)"* screen on the one permission granting total mailbox access |

**The objection that actually matters:** a shared client makes every operator
depend on one credential we control. Suspension — abuse by someone who extracted
the secret from the public repo, a failed annual re-verification, a policy change
— stops every daemon on the same day. Per-operator clients fail independently. A
shared one re-centralises a product whose entire pitch is that operators own their
infrastructure.

(The secret leaking is *not* the issue; Google treats installed-app secrets as
non-confidential and expects PKCE. The issue is that our app *identity* becomes a
shared, revocable dependency.)

## Why this is not scheduled

Password auth is not a legacy path to migrate off. It is **the only path that
works outside Google and Microsoft** — Posteo, Fastmail, Zoho and any self-hosted
Dovecot have no OAuth at all. Removing it would silently narrow OpenOutreach to a
Gmail/Outlook product, which is a positioning change, not a refactor.

So OAuth can only ever be *additive*, and nothing is currently pushing on it:
users are local installs on Gmail, where app passwords work today.

### Trigger

Schedule this when **either** fires:

1. **The first operator arrives on Outlook / Exchange Online** — Microsoft has
   already retired basic auth there, so OAuth is not optional for them.
2. **Google announces app-password retirement for Gmail IMAP/SMTP.**

Until then this card exists so the research is not repeated.

### 2026-08-12 — direction questioned, research incomplete

Two things surfaced after the above was written, both unresolved. Recorded so the
next person starts from the right place, **not** as settled conclusions:

- **Layer 2 is a third and stronger trigger.** The paid hosted tier
  ([[p2-e3-inbound-agentic-email]]) reads customer mailboxes from a hosted backend,
  and you cannot ask paying customers to paste an app password into a SaaS. That
  makes OAuth a *dependency of the paid tier*, not a reaction to provider policy —
  and it dissolves the "re-centralises a decentralised product" objection above,
  which was scoped to self-hosting only.
- **`gmail.send` is classified sensitive, not restricted** — so it needs
  verification but **not** CASA. Only *reading* the mailbox forces restricted
  scopes. That implies a Layer 2 design that never reads the mailbox (`Reply-To` an
  address on our own domain + inbound routing) would avoid the audit entirely, at
  the cost of the thread no longer living in the customer's inbox. Precedent that
  the restricted path is passable for this product category: GMass, Boomerang,
  Yesware, Mixmax and Mailtrack all cleared it.

**Eracle's read on 2026-08-12: this whole direction is likely wrong and needs more
research before anything is scheduled.** Treat the above as leads, not a plan. The
reply-routing alternative in particular is a design fork for
[[p2-e3-inbound-agentic-email]] rather than an auth question, and probably belongs
in its own card once the direction is settled.

## Shape, when it lands

Do not branch the codebase. One adapter at the credential boundary, two call
sites (`inbox.read_mail`, `sender._deliver`):

```python
def _authenticate(conn, mailbox):
    """Attach credentials to an IMAP or SMTP connection."""
    if mailbox.oauth_refresh_token:
        conn.authenticate("XOAUTH2", lambda _: mailbox.xoauth2_string().encode())
    else:
        conn.login(mailbox.username, mailbox.password)
```

The walk, the cursor, the threading and the send path stay single-path.

**Headless deployment is already solved by the CRM's portability.** A refresh
token is a string in the `Mailbox` row, not bound to the machine that obtained it:
consent locally → token lands in `data/db.sqlite3` → move the file to the VM →
the daemon refreshes against `oauth2.googleapis.com` normally. No tunnel, no
second flow. Standard cutover rules apply (`docs/infrastructure.md` §7 — stop the
origin, `pragma integrity_check` both ends).

## Done when

- An operator can connect a Gmail or Outlook mailbox without a password.
- Password auth still works, unchanged, on every provider it works on today.
- A refresh token survives being moved between machines with the CRM.
- Token refresh failure is visible to the operator, not a silent send stoppage.
- No second inbox reader, sender, or onboarding wizard exists.

## Not this card

- Moving to an ESP (Postmark/Mailgun via `django-anymail`). That would fix bounce
  feedback properly with structured webhook events, but conflicts with *"outreach
  over your own email"* — see [[p3-e2-resend-opt-in-send-transport]].
- Replacing `imaplib` with `IMAPClient` / `imap-tools`. Worthwhile cleanup, and
  independent of auth — it would not have prevented
  [[p1-e2-inbound-mail-silent-skip]].

---

### Sources

- [Gmail IMAP XOAUTH2 protocol](https://developers.google.com/workspace/gmail/imap/xoauth2-protocol)
- [Restricted scopes](https://support.google.com/cloud/answer/13464325?hl=en)
- [Restricted scope verification / CASA](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
- [OAuth for TV and limited-input devices — allowed scopes](https://developers.google.com/identity/protocols/oauth2/limited-input-device)
- [OOB flow migration guide](https://developers.google.com/identity/protocols/oauth2/resources/oob-migration)
- [Loopback IP flow migration guide](https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration)
- [OAuth 2.0 for iOS & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
