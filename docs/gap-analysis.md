> Historical design notes. For v8 setup and current limits, use deploy-split.md, security.md and opportunity-sources.md.

# Historical v1 gap analysis

This file records the original analysis. See the v3 README for current implementation status, new shared-table/Discover features, and remaining limits.

# Gap analysis: Student Qyad specs (PRD, TRD, schema, UI)

November 22, 2026. Each gap has an ID, why it matters, and what the MVP did about it.
"FIXED in MVP" = handled in code. "DECIDE" = needs your answer. "LATER" = safe to defer.

## Cross-cutting

- **G-X1 (DECIDE): OPEN-1, OPEN-2, OPEN-3 are still unanswered.** The MVP had to pick: it implements the combined Today view (OPEN-1 option a), skips badges entirely (OPEN-2, placeholder tables kept), and follows the suggested build order of personal dashboard + one group first (OPEN-3). If you answer differently, the Today screen and roadmap change.
- **G-X2: The specs' CONFIRMED/PROPOSED labels are the brainstorm record, but the MVP implements several PROPOSED items** (statuses, due dates, roles, confirmation rules). None are irreversible, but skim section 6 of the PRD and strike anything you don't actually want before friends join.

## PRD gaps

- **G-P1: No invite mechanism specified.** FR-3 says "invite members" without saying how. FIXED in MVP: owner-only invite links with 14-day expiry. Open question left: can members invite, or owner only? MVP says owner only.
- **G-P2: FR-1 has no auth provider.** TRD suggests Google OAuth, but teammates' providers are unknown even there. FIXED in MVP with email + password (works for everyone, no third-party keys). Google login is an add-on later; flagging because it's a deviation from the TRD suggestion.
- **G-P3: FR-20 ("move that to college" corrections) has no time window or state model.** How long after a batch can a chat correction still move something? Unspecified. Not built; the voice pipeline needs a "pending correction" state with an expiry. Decide when the Instinct-side flow is designed.
- **G-P4: No rules for leaving/deleting spaces or removing members.** What happens to a member's tracked applications when they leave a group? (They should survive - they're user-owned - but the spec never says.) MVP: applications survive, removal endpoint not built. LATER.
- **G-P5: "Scale so anyone can create a group" (section 1) vs TRD's "tens of users" non-functional target.** Fine for v1, but the public-signup scaling story (abuse, rate limits, storage caps) is undesigned. LATER, before any public launch.
- **G-P6: Success signal "voice used at least as often as manual entry" is unmeasurable** until the connection route is verified and instrumented. No analytics exist in any spec. LATER.
- **G-P7: Deadlines are date-only everywhere; no time-of-day or reminder behavior.** A "deadline Nov 25" with no reminder is how things get missed. Notifications are not in any spec. DECIDE whether v1.5 needs email/push reminders.

## TRD gaps

- **G-T1 (biggest one): the defining feature has zero verified path.** Route A (browser operation) is untested against this app; Route B needs both the endpoint (now built) and a verified Instinct call to it. Neither side has passed its acceptance test. Do the TRD section 5 test before telling anyone voice updates work. The MVP README carries the exact test.
- **G-T2: "Every agent write is reversible in v1" has no mechanism.** The audit log records before/after, but nothing can replay a `before` state. Either build an undo endpoint or downgrade the claim. MVP ships the audit data, not the revert. LATER.
- **G-T3: The audit log itself leaks if queried wrong.** It stores before/after of private items, but no spec says who can read audit rows. FIXED in MVP: `/api/v1/agent/changes` returns only the caller's own agent rows; there is no shared audit read path.
- **G-T4: No rate limiting or abuse handling on `/agent/apply`.** A leaked token can spam-write until revoked. Acceptable for a private MVP; add rate limits before the token is stored anywhere automated. LATER.
- **G-T5: Backup requirement ("daily minimum") has no owner or mechanism.** On Render/Neon it's a platform checkbox; on your VPS it's a cron + `pg_dump` or a SQLite file copy. DECIDE at deploy time; README notes it.
- **G-T6: No migration strategy.** MVP uses `create_all`, which cannot change existing tables. The first schema change after real data exists needs Alembic. LATER but don't skip it once friends' data is in.

## Schema gaps

- **G-S1: `space_invites` table missing entirely.** WF-4 (invite by link) is impossible in the spec's DDL. FIXED in MVP (`space_invites` with token, expiry, revoke).
- **G-S2: No ordering column on `items`.** WF-3 drags to reorder and the boards are ordered, but position can't persist. FIXED in MVP (`sort_order` integer; UI re-sorts server-side, drag-and-drop itself is LATER).
- **G-S3: Double "Track for me" creates duplicate applications.** Nothing prevented two rows for the same (user, opportunity). FIXED in MVP with `UNIQUE(user_id, opportunity_id)` + return-existing behavior.
- **G-S4: `agent_tokens` audit attribution loses which token acted.** `audit_log.actor_id` is the user even for agent writes. Fine at one token per user; add a `token_id` column when multiple agents exist. LATER.
- **G-S5: `voice_items.destination_space_id` nullable with no defaulting rule.** TRD says "default destination is private" but the schema doesn't say where that default is applied. FIXED in MVP: null destination resolves to the owner's personal space at apply time.
- **G-S6: Inconsistent time handling:** deadlines are `date`, everything else `timestamptz`, and "display in IST" is only a sentence. Date-only is right for deadlines, but the spec should say so explicitly. Documented; no code change needed.

## UI spec gaps

- **G-U1: Mobile story is one sentence.** "Sidebar collapses to bottom tabs" but boards and drag-reorder on a phone are unspecified. MVP desktop-first. DECIDE how much mobile matters before friends use it on phones (they will).
- **G-U2: The WhatsApp review card is called a stable contract but has no version.** If the card format and the app's payload evolve separately, confirmations stop matching what's applied. Version the card format with the API. LATER.
- **G-U3: No loading, empty-search, or offline states** beyond brief mentions. MVP covers empty states for the main lists only.
- **G-U4: "Moving this to Internship Hunt makes it visible to 4 members" implies a move-to-another-space action that no endpoint or schema path supports** (items are space-bound; moving = copy + delete with privacy warnings). Not built. DECIDE if moving items between spaces is even allowed, or share-by-repost only.

## What to answer first

1. OPEN-1 dashboard layout (MVP guessed combined Today - try it and react).
2. G-P2: email/password OK for friends, or is Google login a must?
3. G-T1: run the Route B acceptance test once deployed; until then the voice flow is a design, not a feature.
