# Resend as an opt-in send transport

> ## 📥 Inherited from OpenOutreach, 2026-08-19.
>
> An alternative transport alongside raw SMTP. It belongs wherever sending lives, and sending lives
> here now (`cold_outreach/emails/sender.py`, `smtp.py`).
>
> ⚠️ **One thing to check before building it.** Resend and most ESPs bar non-opt-in lists in their
> terms — the whole reason this project exists is cold outreach, which is exactly what those terms
> exclude. That is a live constraint on the finder side too (a cold list must go to a cold-outreach
> ESP, never to Brevo or Substack). Read the terms before the code.

- **Status:** To Do
- **Priority:** Low
- **Effort:** Medium
- **Area:** Email / Integrations

Split out of [[p2-e2-onboarding-legal-copy-cap-and-integration-scout]] (item 5) on
2026-07-24, carrying that spike's desk findings verbatim. The default stays
**operator-owned SMTP** (`emails/smtp.py`, `emails/sender.py`); this card adds Resend as an
**explicit operator choice** during onboarding that swaps *only* the send path
(`smtp.py` → Resend `POST /emails`). Everything downstream — signature, attribution line,
follow-up agent, IMAP reply loop — is unchanged.

## Scope: the operator-owns-the-domain path, and nothing else

**Hard rule:** Resend send requires the operator still has an **IMAP-reachable mailbox on
the sending domain**. Onboarding must collect and verify that mailbox exactly as today, even
when send goes via Resend, so the reply loop keeps working. That constraint *is* the scope.

**Explicitly deferred / out of scope:**
- **Send-only domains (no receiving mailbox).** The only way to capture replies is Resend's
  native inbound — repoint MX → Resend → `email.received` **webhook**. The daemon runs no
  public web server, so this needs a hub-side webhook receiver and a rewrite of the reply
  path. Larger; not this card.
- **Hosted send from *our* domain** (all operators' mail via Resend from OpenOutreach-owned
  addresses like `john@send.openoutreach.app`, replies via a hub webhook). Technically clean
  but **rejected on identity + shared-reputation grounds** — full reasoning recorded in
  [[p2-e3-inbound-agentic-email]] (considered-and-rejected 2026-07-24).

## Findings (desk/API review 2026-07-24, from official docs)

- **Send:** `POST /emails` (Bearer key, `User-Agent` header required), body
  `from/to/subject/html/text/reply_to/cc/bcc/headers`; batch `POST /emails/batch` (≤100, no
  attachments). Rate limit 10 req/s per team.
- **Sending identity:** Resend **only sends from domains verified in Resend via DNS**
  (DKIM/SPF/DMARC) — not an arbitrary Gmail/Workspace address. So this path is for operators
  sending from a domain they control, not a consumer inbox. Fine as an explicit choice; it
  just can't be the default.
- **Where replies go (the clean path):** the operator keeps a real mailbox on the sending
  domain (MX still at Google/Workspace/etc.), so replies land in a normal inbox and the
  **existing IMAP loop reads them unchanged**. Add Resend's DKIM/SPF records *alongside* the
  existing MX; `From:`/`Reply-To:` = that mailbox. Resend becomes a pure send-transport swap.
- **Pricing:** free 3k/mo (100/day cap, 1 domain); Pro $20/mo → 50k, ~$0.40–0.90/1k; managed
  IP warmup, shared IPs by default.

**Acceptance criteria**
- [ ] An operator can opt into Resend as the send backend during onboarding; the default
  remains operator-owned SMTP and an operator who says nothing is unaffected.
- [ ] Onboarding still collects and auth-checks an IMAP-reachable mailbox on the sending
  domain when Resend is chosen — a send-only setup is refused with a clear reason, not
  half-configured.
- [ ] Only the send call is swapped: `Mailbox.signature`, the `ATTRIBUTION` line, threading
  headers (`Message-ID`/`In-Reply-To`/`References`), the optional operator BCC, and
  `inbox.py`'s reply reading behave identically on both transports.
- [ ] Threading survives the swap end-to-end — a Resend-sent opener gets a reply read over
  IMAP and a follow-up threaded onto it.
- [ ] Per-box daily-cap pacing (`Mailbox.daily_limit`, `headroom_today()`) still governs
  send volume; Resend's own limits don't replace it.
- [ ] The send log stays metadata-only (from/to/subject/Message-ID) — no body, matching SMTP.

**Recommendation from the spike:** viable, small first cut, *provided* the IMAP mailbox is
retained. Low priority — operator-owned SMTP works today and this buys deliverability
convenience, not capability.
