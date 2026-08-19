# Inbound Agentic Email — Hosted Reply Capture + Agent Autopilot (Premium)

> ## 📥 Inherited from OpenOutreach, 2026-08-19 — **and it is the only product idea in this folder.**
>
> Capture replies to outreach, run an agent over them, sell it as a premium tier. It was filed under
> OpenOutreach as a hosted upsell; it is a **sender's** product, and this is now the sender. The
> reply-reading half already exists here (`cold_outreach/emails/steps/reply.py` plus the outreach
> agent, which classifies a reply and picks send / complete / suppress).
>
> **Two inherited judgements to weigh before reviving it, neither of which is mine to overturn:**
>
> - OpenOutreach declined reply outcomes as a *return channel* — they are conversation states, and the
>   conversation belongs to whoever sent the mail. That decision constrains the finder, not this side:
>   here the conversation genuinely *is* ours, so the objection does not transfer. What does transfer
>   is the shape — do not build this by reaching back into a finder's database.
> - `branding/branding.md` flagged it as **the opposite of the OpenOutreach brand on every axis**
>   (commercial SaaS, not free/open/self-hosted) and said it would need **its own brand** rather than
>   being folded into the indie-hacker archetype. That judgement was about not confusing OpenOutreach's
>   positioning, and it survives the move intact.

- **Status:** To Do (gated behind Layer 1 shipping)
- **Priority:** Medium (premium tier; downstream of the affiliate layer)
- **Effort:** High
- **Area:** Product (premium SaaS) / Hub / Pipeline

> Layer 2 of the email-first pivot — see [[p1-e3-email-first-pivot-epic]].
>
> **★ Reframed 2026-06-11 — the free/paid line moved; this card narrows to compose+send only.** Layer 1
> ([[p1-e3-email-agentic-outreach]]) now **reads inbound replies itself** (IMAP-poll, confirmed live),
> records each as a `ChatMessage`, **classifies** it, and **stops / sets `Outcome` / hands the warm ones
> to the human** — all free. What it deliberately does **not** do is **write back**. So this premium card
> is now exactly one capability: **the agent composing and sending the replies — the multi-turn autonomous
> email *conversation*.** The old framing below ("the free client never reads replies"; "re-point the
> mailbox auto-forward to our backend") is **superseded** — capture already happens in Layer 1 via IMAP;
> the upgrade unlocks agentic *response*, not *reading*. Hosted-vs-local execution of the reply agent is
> an open architecture choice (see Hosting note), no longer forced by "only we can read the inbox."

> **★ Architecture settled 2026-06-14 — L1 is outbound-only (NO reading); L2 = the user hands the SaaS
> mailbox access and the backend owns the whole conversation. Supersedes the 2026-06-11 reframe's "Layer 1
> reads inbound itself (IMAP-poll), all free."** There is **no** SMTP/IMAP reading in Layer 1: it sends one
> email, moves the deal to `EMAILED` (quasi-terminal), and never reads replies. This *restores* the
> "by-architecture" moat — the agentic conversation exists only on our backend, nothing to license-gate in
> the OSS client. How L2 takes over (decided with Eracle):
>
> - **Credential handoff = the same IceMail *Export Mailboxes* app-password sheet** the user pasted into the
>   daemon for L1. One app password is both `imap.gmail.com:993` (read) and `smtp.gmail.com:587` (send) —
>   confirmed live 2026-06-10 — so handing it to the SaaS gives the backend the pool's full inbox+outbox.
> - **The mailbox is the thread's source of truth.** The backend reconstructs the whole conversation by
>   IMAP-reading `[Gmail]/Sent Mail` (the L1 outbound) + `INBOX` (the replies) — **no relay from the daemon
>   needed.** Daemon and backend are fully decoupled; they share only the mailbox. A reply that lands before
>   the user upgrades just waits in the mailbox, and the backend backfills history on connect — nothing lost.
> - **Deliverability is already solved (sidesteps the old "deliverability ownership" open question).** The
>   backend replies *through the box's own SMTP, authenticated as that box*, so `From`/threading/SPF/DKIM/
>   DMARC alignment all hold. We are **not** sending from our infra on the user's domain.
> - **Forward-flip is RETIRED.** Shared IMAP credentials replace "re-point the mailbox forward to our
>   endpoint" (which never fired in the 2026-06-10 test). The **Inbound endpoint** design in *What* below is
>   superseded by IMAP-poll-with-shared-creds.
> - **The real integration surface is CONTEXT, not credentials.** The reply agent needs the campaign product
>   docs + the emailed deals' per-lead context (the same inputs `run_follow_up_agent` uses locally) to answer
>   well — that flows daemon → hub, a natural extension of the [[p1-e2-non-eu-lead-collection]] ingestion.
>   Credentials are the easy half.
> - **Campaign correlation key = `Deal.email_message_id`** (banked by L1). A reply's `In-Reply-To`/
>   `References` matches the exact outgoing Message-ID → the exact campaign/deal — the robust disambiguator
>   for a lead emailed in two campaigns from two boxes (recipient address alone can't). It flows up with the
>   context handoff.
> - **Open (UX, non-blocking):** does the local tool reflect "lead replied / agent handling it" back to the
>   user, or does the hub own the conversation view entirely? Leaning hub-owns-it (keeps the daemon dumb).

> **★ Considered and rejected 2026-07-24 — hosted send/receive from *our* domain via Resend (e.g.
> `john@send.openoutreach.app`). Reinforces the 2026-06-14 "send as the operator's own box" decision above.**
> The idea: instead of using the operator's mailbox creds, run all sending through Resend from an
> OpenOutreach-owned domain, minting a per-operator address, and capture replies via Resend's inbound webhook.
> **Technically clean** — verify one subdomain's DKIM/SPF in our Resend account (any local-part is then
> sendable, no per-user setup), MX that subdomain → Resend inbound (catch-all), and a hub webhook demuxes
> replies by `To:` local-part. A dedicated subdomain keeps the root domain's own mail (Google Workspace)
> intact. **Rejected on product grounds, not feasibility:**
> - **Identity loss.** `john@send.openoutreach.app` is our *tool's* domain, not John-at-his-company. A cold
>   B2B recipient reads it as bulk-tool outreach — the exact credibility/deliverability penalty the
>   "send from your own inbox" premise exists to avoid. Sending *as a real person at their own company* is
>   most of why cold email lands.
> - **Shared reputation.** Every operator sending from one shared domain means one operator's spam complaints
>   degrade deliverability for all of them — *worse* than per-operator domains. Isolating it (a subdomain per
>   operator) reintroduces per-user DNS and still isn't their identity.
> - **Wider processor surface.** All outreach *and* replies would flow through and be stored on our infra —
>   the centralization the Cloud retirement stepped away from (see Hosting note).
> The settled path — reply *through the box's own SMTP, authenticated as that box*, reading via shared
> app-password IMAP — keeps `From`/SPF/DKIM/DMARC aligned to a real personal sender and needs no Resend and
> no inbound webhook. Resend's only non-overlapping niche stays: an **opt-in transport for an operator sending
> from a domain *they* own** (verified in *their* Resend, own IMAP mailbox for replies) — scoped in
> [[p2-e2-onboarding-legal-copy-cap-and-integration-scout]], not this hosted tier.

## What

A hosted inbound service. **The agentic email conversation lives only here, by architecture** —
the free self-hosted client never reads replies, so there is no agentic-reply code to give away
or license-gate; you upgrade by changing where replies are routed. In Layer 1 the sending mailbox
**auto-forwards** lead replies to the user's personal inbox; upgrading **re-points that forward** to
our hosted inbound endpoint, where the reply is **stored in our DB** as part of the lead's thread
and our **agent drafts and sends the response** on the user's behalf — fully agentic, the way
direct messages on the professional network are auto-handled today, but more reliable.

Pieces:

1. **Inbound endpoint (decided 2026-06-09: the mailbox forward, re-pointed — not an ESP webhook).**
   The sending mailbox's auto-forward is flipped from the user's inbox to an address we own; our
   endpoint parses the forwarded mail, dedupes, and normalizes it to a thread message. Why forward-flip
   over an ESP inbound webhook: it's **push** with **`From`=`Reply-To`=mailbox** (clean deliverability),
   the Layer-1→2 upgrade is a single setting change, and it doesn't depend on IceMail's missing API.
   *Fallbacks if per-mailbox auto-forward is unavailable:* per-thread Reply-To on our own domain (MX'd
   to us) or IMAP-poll the mailbox pool — see [[p1-e3-email-agentic-outreach]] → Inbound (Layer 2).
2. **Threading + storage.** Match the inbound message to the originating `Lead`/thread
   (Message-ID / References headers, or a per-thread plus-address / subdomain). Persist the
   full conversation server-side.
3. **Agentic reply loop.** Reuse `run_follow_up_agent()` / `FollowUpDecision`
   (`send_message` / `wait` / `mark_completed`) over the stored email thread, with the same
   campaign product docs + per-lead context the outbound side uses.
4. **Human handoff.** Warm/positive replies (booked-call intent, pricing questions) escalate
   to the user instead of being auto-answered — notify + hand the thread over.
5. **Guardrails.** Hard stop on unsubscribe/negative-sentiment; per-lead and per-domain send
   limits; full audit trail of what the agent sent.

## Why

- **It's the monetizable premium.** Layer 1 (affiliate) is side-income; the recurring,
  defensible revenue is *running the outreach for the user*, not just referring tools. "We
  reply to your leads automatically" is a product people pay a subscription for.
- **Removes the last manual step.** Layer 1 still asks the user to read and answer warm
  replies. Layer 2 closes the loop — discovery → email → reply → booked call — with the
  human only pulled in when it matters.
- **Reuses the hard part we already built.** The follow-up agent's decisioning already
  exists; this points it at an email thread we own end-to-end (no `Reply-To` round-trip
  through someone's Gmail).

> **★ Shared engine with the marketing platform, but a *separate product* (decided 2026-06-18).** This
> tier and the agentic email-marketing platform ([[p1-e3-agentic-email-marketing-product]]) share the
> agentic-email **runtime** + hosted backend + hub context ingestion — build it once, driven by **this**
> card first (it's near-term and legally cheap: we're a *processor* acting on the operator's own
> mailbox). They are **not** one product: the platform is *controller*-role profiling over the pooled
> third-party data, gated on the controller relocation + lawyer consult. Fusing them would drag this
> shippable upsell into that far-term gate. See the "shared engine, separate products" section in that
> card for the full reasoning.

## Prerequisites

- **Layer 1 shipped** — enrichment + send + outbound agent over email
  ([[p1-e3-email-agentic-outreach]]). No inbound product without an outbound channel.
- **Follow-up agent must be trustworthy first.** [[p2-e2-followup-identity-backoff-sentiment]]
  documents three live defects (identity mismatch, no `wait` backoff, no sentiment/disqualify
  exit). Auto-replying to real prospects with those bugs is a reputational liability — fix
  them before any agent sends an unsupervised email. This is the "a bit better in terms of
  bugs" bar from the epic.
- **`Reply-To` design from Layer 1 must not paint us into a corner** — the per-thread
  addressing scheme should already anticipate inbound capture.

## Hosting note

This reintroduces a control-plane / hosted component, which the project deliberately stepped
back from when Cloud was retired (see the **Cloud retirement** record in
[[p1-e3-email-first-pivot-epic]]). The distinction: Cloud hosted *the whole daemon
on someone else's machine* (and inherited all of the platform's fragility invisibly). This hosts
*only the inbound mail capture + reply agent* — no session on the platform on our infra, a much
smaller and more robust surface. If the Hub scaffolding is kept "warm" rather than deleted,
parts of it (auth, billing) may serve this tier.

## User Story

**Persona:** Daniel (same operator as [[p1-e3-email-agentic-outreach]]) — runs a 3-person
B2B lead-gen agency. Layer 1 already finds emails and sends the first touches; replies come
to his inbox and he answers them between client calls. The problem: he's the bottleneck.
Replies pile up over a weekend, the warm ones go cold, and the agent can't follow up because
it never sees what the lead said.

---

Daniel upgrades to the premium tier and one setting flips — the sending mailbox's forward now
routes lead replies to OpenOutreach instead of his inbox. Nothing else changes in how he works.

Monday a lead replies: *"Interesting — what does pricing look like for a team of 12?"* It
lands on the inbound endpoint, gets threaded onto that lead's conversation, and the agent —
seeing a clear buying signal — doesn't try to answer the pricing question itself. It flags
the thread as warm and pings Daniel: *"Lead asked about pricing, handed to you."* Daniel
takes that one personally.

Another lead replies *"not right now, maybe Q3."* The agent files it, sets a long backoff,
and schedules a single soft nudge for July — no human touch needed. A third replies with
*"please remove me"*; the agent stops the thread cold and never contacts them again.

By Friday Daniel has answered four warm threads himself and the agent has quietly kept
fifteen others alive, none of which he had to read. His booked-call count is up and his
weekend inbox is empty.

---

**Single-sentence version:** As an operator whose bottleneck is answering replies, I want
inbound email captured by the tool and handled by the same agent that sends it — escalating
only the warm ones to me — so the discovery→email→reply→call loop runs without me babysitting
an inbox.

## Open questions

- **Per-thread addressing:** plus-addressing (`user+threadid@`), per-thread subdomain, or
  header-only (Message-ID/References) matching when forwarded mail lands on our endpoint?
  (Forwarding preserves Message-ID/References, but wrapping can complicate it — confirm.)
- **Auto-forward config — field CONFIRMED 2026-06-09 (exists, domain-level), behavior UNVERIFIED
  live (2026-06-10).** IceMail's domain setup has a **Forwarding Email** field (per-domain — all
  mailboxes forward to it). Layer 1 points it at the user; Layer 2 re-points it at us. **But the
  first live test failed**: with the field set, a real reply stayed in the mailbox and never reached
  the destination — diagnosis ladder + re-test plan in [[p1-e3-email-agentic-outreach]] (handover
  open flag 2). **Also still open: is it editable post-setup?** If the forward stays dead or is
  set-once, fall back to per-thread Reply-To on our domain or **IMAP-poll (confirmed live
  2026-06-10** — the SMTP app password reads `imap.gmail.com:993` too**)**.
- **Where does inbound run** — revived/trimmed Hub, or a small standalone service? Ties to
  the Cloud retirement decision on keeping Hub scaffolding warm ([[p1-e3-email-first-pivot-epic]]).
- **Pricing + name.** Premium working name TBD ("Autopilot"?). Per-seat, per-active-lead, or
  flat? Analytics-style pricing (value-based) beats execution-tool pricing.
- **Deliverability ownership:** replying from our infra on the user's domain needs SPF/DKIM
  alignment via their ESP — document the DNS the user must set.
- **Go-to-market:** the paused Brevo lifecycle campaign ([[p2-e2-brevo-workflow-buildout]])
  gets repointed to sell *this* product when it ships — that's the launch channel into the
  activated base. The framework/bodies are reusable; only the offer + conversion wire change.

## Done when

- The mailbox forward (re-pointed to our endpoint) delivers a lead reply that is verified,
  threaded onto the correct `Lead`, and stored server-side.
- The follow-up agent answers a stored inbound thread using campaign + per-lead context,
  honoring backoff/sentiment/unsubscribe guardrails.
- Warm/high-intent replies escalate to the user instead of being auto-answered.
- A full audit trail records every agent-sent email, and a kill switch can pause autopilot
  per campaign.
