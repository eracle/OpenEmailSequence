# The Mail Pass Can Skip A Message And Nothing Notices

> ## 📥 Inherited from OpenOutreach, 2026-08-19. **Still live — this is a real bug, not a wish.**
>
> The mail pass (`cold_outreach/emails/sync.py`, `classify.py`, `project.py`) came across whole, and
> so did this. Nothing about the port fixed it: a message that cannot be fetched still stops the walk,
> and the cursor still advances only over what was stored.
>
> Read it alongside the *accepted* blind spot documented in `cold_outreach/README.md` — a folder's
> first walk starts at `UIDNEXT - 1`, so a box connected mid-campaign never sees the replies its
> earlier sends earned. That one is deliberate. This one is not.

> **Superseded 2026-08-13 by [[2026-08-13-p1-e2-mail-log-epic]]**, which owns the
> repair and shipped that day. The mail this box lost is still lost until someone
> winds its `FolderCoverage.last_uid` back to 0 and lets one pass re-walk.
> Kept because the incident below is measured production evidence that cannot be
> reproduced — the UID-by-UID reconstruction, the two commits that redefined the
> cursor, and the one human reply this product has ever received. *§ Direction*
> and *§ Open questions* are **history**: the epic reached a different answer from
> first principles, and the redesign that follows this note is the last iteration
> before it, not the plan of record.

- **Status:** Superseded — see [[2026-08-13-p1-e2-mail-log-epic]]
- **Priority:** Critical
- **Effort:** Medium
- **Area:** Pipeline / Inbound mail

> **This card states a problem.** It was found by incident (2026-08-12, auditing
> `ercole` after the sending-window deploy — that deploy was fine, this was
> underneath it). The incident is evidence, not the scope: the one-off repair to
> `ercole` is an ops step recorded at the bottom, deliberately not an acceptance
> criterion. *§ Direction* was added later, once the diagnosis made clear that the
> cursor is the wrong primitive to repair; it names a shape, not a schema.

## User Story

As an OpenOutreach operator, I want the system to know the difference between
**"they have not replied" and "we have not read their reply"** — so that the one
signal the whole product exists to produce cannot be discarded by bookkeeping I
have no way to see.

Those two worlds are today a single `no`. `core/cycle.py` row 2 asks whether a deal
has an inbound `ChatMessage` newer than its newest outgoing one, and silence
answers for both. With no chasing, an unanswered `EMAILED` deal rests forever at no
cost — so the second world is free, invisible, and indistinguishable from success.
It took "0 human replies from 590 sends" and a live IMAP session to see it at all.

Two weaker phrasings are wrong on purpose. *"Every reply reaches the CRM"* is wrong
because an unreachable mailbox legitimately delays a reply, and that is not this
bug. *"The cursor must not skip"* is wrong because the cursor is one way to fall
into the gap, not the gap — repairing it leaves the conflation standing. The
property is that **an inbound message is processed or still pending, never silently
neither**, and that a step — not a human with an IMAP client — can tell which.

## What happened

`Mailbox.unsub_scan_uid` is the IMAP resume point for the mail pass. Two commits
gave it two different meanings, eight days apart, without resetting it:

| commit | landed on `ercole` | what the field claimed |
|---|---|---|
| `d5a7e9d` | 2026-08-03 11:11 UTC | "**opt-out aliases** scanned up to here" |
| `44d1f7a` | 2026-08-11 17:35 UTC | "**all inbound mail** processed up to here" |

Between those dates the cursor advanced to `UIDNEXT - 1` on every pass while
scanning only for `+unsub` aliases; replies were found by a separate per-deal
`_search_thread` that ignored the cursor entirely. When the unified walk took over,
`_resume_from` saw an unchanged `UIDVALIDITY` (still `1`), returned the inherited
value, and every message beneath it became permanently unreachable.

Measured on `ercole`'s live mailbox (31 messages in INBOX, cursor `31`,
`UIDNEXT 32`):

```
UID 24  22-Jul   stored     ─┐ per-deal search era
UID 25  ~25-Jul  stored      │
UID 26  02-Aug   stored     ─┘
UID 27  04-Aug   LOST       ─┐ cursor climbing for opt-outs only
UID 28  ~05-Aug  LOST       ─┘
UID 29  12-Aug   stored     ─┐ unified walk, working correctly
UID 30  12-Aug   stored      │
UID 31  12-Aug   stored     ─┘
```

The split falls exactly on the two commit dates.

**UID 28 was a genuine human reply** — `hans@basicops.com` on deal 829, in full:
*"No thanks"*. It is the **only real reply either instance has ever received**
across 590 emailed deals, and it is not in the CRM. **UID 27** was a hard bounce
for `vp@insursync.io` on deal 1145. Both deals are still in state `Emailed`, so
both are queued to be mailed again — one of them a man who declined.

## Ruled out

Checked and eliminated, so nobody repeats the work:

- **Body parsing.** Both lost messages replay through the real `_plain_text_body`
  to healthy non-empty bodies (Hans → `'No thanks'`, 9 chars; the NDR → 1625).
  `_store_reply`'s `if not body` guard would not have dropped either.
- **Threading.** Both carry `References`/`In-Reply-To` matching a stored
  `email_message_id` via the real `_deal_for_thread`.
- **`email_message_id` population.** 590/590 emailed deals have one.
- **`mailbox_id` scoping.** Uniform (`1`) across all six matched deals.
- **A library.** `IMAPClient`/`imap-tools` would have stored the same stale `28`.
  The bug is semantic, not mechanical — worth noting because "use a library" is
  the obvious wrong first instinct here. (*§ Direction* does adopt one, for
  reasons that have nothing to do with this bug: it needs folder enumeration and
  server capabilities, which `imaplib` makes expensive. Transport, not protocol.)

## Why this matters beyond one box

The loss is **silent by construction**: no error, no warning, no counter moves.
`ercole`'s logs for the period are clean. This surfaced only because "0 human
replies from 590 sends" was implausible enough to dig into, and the digging needed
a live IMAP session — nothing in the database records a message that was never
read. Any operator who upgraded across those two commits with unread mail in the
window lost it the same way and cannot know.

The same ingest path feeds [[p2-e3-inbound-agentic-email]], where the agent answers
replies unsupervised. Silent loss is worse there.

## Direction — mirror the box, then classify locally

Decided 2026-08-13. It replaces the seen-ledger sketch this section held on
2026-08-12, which in turn replaced the cursor-repair questions before that. Same
diagnosis each time; the primitive keeps getting stronger. The ledger recorded
*facts about* messages, which still leaves the message itself reachable only
through a live IMAP session at the exact moment the pass runs — so a
classification bug, an outage mid-walk, or a later change of mind about what
counts as interesting all still lose the thing itself. **Keeping the message
removes the class.** A copy of the mail is acceptable (decided 2026-08-13, see
*What it costs*), and once we hold the bytes most of this card's open questions
answer themselves.

**The conflation to kill.** The cycle asks *"does this deal have an inbound
`ChatMessage` newer than its newest outgoing one?"* (`core/cycle.py` row 2) and
gets `no` for two different worlds: **they have not replied**, and **we never
read their reply**. Every loss in this file is that one conflation. With no
chasing, an unanswered `EMAILED` rests forever at no cost, so the second world is
free and invisible — which is why nine days of it passed unnoticed. Splitting the
two is the whole protocol; the cursor bug is one way to fall into the gap, not the
gap itself.

**Why the current design cannot split them.** `_advance_cursor` persists
`max(unsub_scan_uid, uidnext - 1)`. That number comes from the *box's* STATUS, not
from our work: a pass that classified nothing, or that failed every FETCH, lands
the cursor in exactly the same place as a pass that read everything. It is a claim
about the mailbox wearing the costume of a claim about us. The `max()` then makes
it a ratchet — no correct pass can walk a wrong value back down, which is why a
semantic drift became permanent loss rather than one bad pass.

**Three moves.**

1. **A library carries the transport.** `IMAPClient` replaces the hand-rolled
   `imaplib` calls in `inbox.py`. It does *not* fix this bug — see *Ruled out* —
   and is adopted because the redesign needs things `imaplib` makes expensive:
   enumerating folders by their special-use attribute rather than hardcoding
   `INBOX`, reading `CAPABILITY` to know what the server offers, and fetching
   `X-GM-MSGID` where it exists. It is also the transport [[p3-e2-mailbox-oauth-authentication]]
   would authenticate through, so that card's *"replacing `imaplib` is worthwhile
   cleanup"* line lands here instead of waiting on OAuth. Chosen over `imap-tools`
   because what we want is **raw bytes** plus explicit control of
   `STATUS`/`UIDVALIDITY`; `imap-tools` abstracts toward *parsed* messages, which
   is the half this repo already has working and tested (`_plain_text_body`,
   `_strip_quoted`).

2. **A dedicated part of the database holds the mail.** Two tables, and the shape
   is the argument:

   | table | holds | why it is not a cache |
   |---|---|---|
   | inbound message | one row per message ever seen in a watched box: identity, **the raw RFC822 bytes**, `received_at`, `fetched_at`, its `(folder, uid, uidvalidity)` provenance, `processed_at` (NULL = *pending*), classification, and the deal when it is a reply | it is the only copy we control; the box may relabel, archive or expire the original |
   | folder coverage | per `(mailbox, folder)`: `uidvalidity`, `last_uid`, `synced_at` | written from **what we stored**, never from the box's `STATUS` — a claim about our knowledge, which is the only kind that may be trusted as one |

   **Identity** is the normalized `Message-ID`, and `sha256` of the raw bytes when
   there is none. That fallback is only defensible because we hold the bytes — a
   header hash was the candidate while we didn't, and *"not obviously correct"* was
   the right verdict on it.

3. **Sync and process become two jobs.** `sync` speaks IMAP and does nothing else:
   fetch, store, advance coverage. `process` reads pending rows out of our own
   database and never opens a socket. The old `read_mail` was both at once, which
   is why a classification decision could consume a message permanently.

**Steps still consult coverage before reading absence as evidence** — that part of
yesterday's sketch survives unchanged, and it is what makes this a protocol rather
than a table.

| step | question it must ask | consequence today |
|---|---|---|
| `answer_reply` (row 2) | is my read of this box current? | fires on stale knowledge; a lost reply is indistinguishable from silence |
| `send_first_email` (row 3) | have I read every opt-out this box has received? | an unread `+unsub` mails someone who already left |
| `top_up` / `buy_address` (rows 5–6) | is this campaign's box readable at all? | spends on discovery and paid lookups while mailing into a void |

**What it buys.**

- **Correctness stops depending on the cursor.** `last_uid` becomes a fetch
  optimization sitting in front of `get_or_create(identity)`, so rewinding it to 0
  costs one re-walk and can lose nothing. Redefining what a persisted integer
  *means* — the entire incident — is no longer a way to lose mail. The `max()`
  ratchet goes with it: a correct pass may now walk a wrong value back down.
- **The pending state exists.** A failed FETCH stores nothing and leaves its UID
  below the cursor, so the next pass comes back for it. Today `_walk` `continue`s
  past an unreadable header while `_advance_cursor` moves on regardless.
- **Countability is arithmetic**, not a new audit mechanism: rows stored, rows
  pending, rows classified, against the box's own message count.
- **Classification becomes replayable, and the sequencing constraint dissolves.**
  Re-reading a stored NDR is why [[p1-e2-email-bounce-detection-suppression]] had
  to land before any rewind. With sync split from process, `ercole`'s mail can be
  mirrored **now** — capturing it before anything else is lost — while the
  processing half stays held. That card then gets built against seven real NDRs
  and one real reply on disk, instead of fixtures.
- **The logic gets straightforward, which is the actual goal.** Classification
  becomes a pure function from stored bytes to a verdict, testable with no IMAP
  fake at all — `tests/emails/test_mail_pass.py` currently has to impersonate the
  protocol to test anything.

**What it costs.** Raw inbound mail becomes data at rest, widening what the CRM
holds from *replies we matched to a deal* to *everything that arrived in the box*
— including mail from people who never wrote to us and never consented to
anything. Accepted 2026-08-13: it is the operator's own mailbox on the operator's
own machine, and `db.sqlite3` already carries reply bodies in `ChatMessage`. It is
recorded here because it is a real widening, not a free one, and because a shared
mailbox makes it much larger than a dedicated sending box does.

**Migration.** `unsub_scan_uid` does **not** carry over — its meaning is precisely
what is untrustworthy. Folder coverage starts at 0 and the first sync mirrors the
box, which is a one-off full walk per install and is exactly what reaches UID 27
and 28 on `ercole`. That is safe now only because syncing is no longer processing.

## Open questions

- **Which folders are mirrored?** `inbox.py` hardcodes `INBOX`, while
  `warmth.py:157` already does it properly — finding Sent by its `\Sent`
  special-use attribute, explicitly because Gmail localizes `[Gmail]/Sent Mail`.
  On Gmail `INBOX` is a **label**, not a store: a reply filed as **Spam**, or
  archived by a human before the pass runs, never carried the label and is
  unreachable, and because UIDs are per-folder nothing observes the departure.
  `All Mail` cannot lose messages that way but is a far larger walk. The mirror
  makes this a question about *which messages get offered to the store* rather
  than about identity — a message that moves folders is one row either way, and
  `X-GM-MSGID` (recorded when `CAPABILITY` advertises `X-GM-EXT-1`) says so
  cheaply. So it can be answered after the first version ships, and the answer
  migrates nothing.
- **Should stale coverage gate spend, or only gate reading absence as evidence?**
  The third table row above is the aggressive reading: it stops a campaign whose
  mailbox has gone unreadable from buying addresses. That may be correct or may be
  an outage amplifier.

*Answered by the redesign:* identity with no `Message-ID` (hash the bytes we now
hold) and retention (keep everything; the size question is the *cost* above, not a
policy knob).

## Done when

- A message that arrives in a watched mailbox is either processed or still
  pending — never silently neither.
- *No reply* and *reply not read* are distinguishable by a step, not just by a
  human with a live IMAP session.
- Changing what a persisted cursor *means* cannot lose a message — because no
  step trusts the cursor as the record of what was read.
- An operator (or a test) can answer "how many inbound messages have I processed
  against how many exist?" so a gap is countable rather than invisible.
- A message whose FETCH fails is retried, not passed. Today `_walk` `continue`s
  on an unreadable header while `_advance_cursor` moves past it regardless — the
  same defect as the incident, still live, one transport hiccup away.
- A message can be re-classified without a mailbox round trip, so a bug in
  classification is repairable rather than terminal.
- Covered by a test that migrates a populated cursor and asserts nothing is
  skipped.

## Not this card

- Bounce classification and suppression — [[p1-e2-email-bounce-detection-suppression]].
- Recovering `ercole`'s two lost messages — ops step below, not an acceptance
  criterion. A card whose criteria name one person's email cannot be reused and
  would read as done the moment the repair lands.

---

## 2026-08-12 handover — diagnosed, not fixed; `ercole` stopped mid-investigation

**State of the box.** `ercole` is **stopped** (`docker compose -f local.yml stop`,
2026-08-12 ~13:30 UTC) and was left that way deliberately: it freezes deals 829 and
1145 before either gets a follow-up. `ylenia` is still running. Nothing in either
codebase was changed — this session was read-only against the CRM apart from the
config write noted below.

**Unrelated config change made the same session.** `SiteConfig.country_code` was
set `es → us` on **both** instances to open the hub give-back (`contacts/service.py`
skips contribution entirely for an EEA/UK/CH operator). Side effect to be aware of
when reading send timestamps: the cold-send window is now 08:00–20:00 New York =
**14:00–02:00 Madrid**. Recorded in `docs/infrastructure.md` § *Rules that bite*.

**Sequencing — superseded 2026-08-13 by the mirror.** As written below, the
recovery meant rewinding the cursor and re-reading UID 27 (an NDR) through the
ingest path, which reproduces the bounce loop in
[[p1-e2-email-bounce-detection-suppression]] — it had already run once on deal
1166 that morning — so bounce classification had to land first. Under *§ Direction*
the recovery is instead: **sync the box, which stores 27 and 28 as pending rows and
classifies nothing**, and let the processing half run once bounce classification
exists. The mail is captured immediately; the dangerous step is the one that
waits. The original instruction is kept for the record:

```python
# the superseded route — rewind after bounce classification exists:
from openoutreach.emails.models import Mailbox
Mailbox.objects.filter(pk=1).update(unsub_scan_uid=26)   # was 31
```

Re-reading 27–31 was safe in itself: `_store_reply` upserts on
`(deal, external_id)` and `_suppress_sender` is idempotent, so 29–31 could only
rewrite rows they already wrote. The hazard was never the re-read — it was that
reading *was* acting.

**Verify after.** Deal 829 has an inbound `ChatMessage` containing `No thanks`, and
is no longer queued for a follow-up. Deal 1145 is terminal rather than `Emailed`.

**Still open, unrelated to this card.** The hub's `ApiToken` id=1 is keyed to
`operator_email='eracle'` (a bare username), while the client now sends
`eracle@posteo.eu`. Registration is `get_or_create(operator_email=...)`, so the
first contribution after the country change mints a **second** token and strands
id=1 with its 6 June rows as a separate dormant operator in the hub analytics. Fix
the email on token 1 *before* `ercole` restarts, or the merge gets messy.

---

*Root cause is a persisted integer that is a **claim about work completed**. The
refactor widened the claim without re-earning it. Nothing in the type system, the
migration, or the tests could notice, because the value stayed valid-looking
throughout.*
