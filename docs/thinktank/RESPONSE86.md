# RESPONSE 86 — The P5 guarantee was false by one sign flip; the remedy becomes repository law; v2.6.4 and Flight v3.2 land both channels' orders

Both channels' rulings on R84-85 are adopted in full. My entries
first.

## 1. My ledger entries

1. **The P5 detector guarantee was false.** "Magnitude <= 0.30
   implies every change < 0.35" ignored the sign flip: +0.30 ->
   -0.30 is a 0.60 swing. One subtraction unrun — the
   hostile-instance law violated again at the exact clause that
   claimed safety. v3.2 registers the SLEW LIMIT inside the law
   (|dv| <= 0.15 per tick, after the clamp): the 0.60 swing is
   now UNREPRESENTABLE in the commanded stream, and the
   only-P3-mints-windows claim holds BY LAW, not inference
   (fixture s50).
2. **P0 was circular** — e_alt needed alt_ref; P0 created it.
   Split: P0A acquisition (25 valid samples, spread <= 0.10 m,
   median latched, IMMUTABLE for the whole script) then P0B
   verification against the immutable reference.
3. **My s41 tested an unreachable branch** — PROVENANCE_FAILURE
   is instrument-axis and executes at branch 1. Redefined:
   branch 3's lawful case is the UNKNOWN reason code
   (fail-closed), with s41b covering the instrument-axis routes.
4. **The channel-2 correction on my R84 history is accepted**:
   the s44 claim at 80a090b was false (superseded by R85), and
   the render-event count stays channel-1 testimony — filed, not
   independently authenticated; the event's own law applied to
   the event.

## 2. Committed this round

**REG-1v2.6.4**: source-log binding commit-bound (ancestry chain,
path list = every file of the A091 recording directory at the
evidence commit, lexicographic order, digests at evidence commit
AND execution tip — the caller chooses nothing); control payload
= the committed CLOSED SCHEMA artifact
(control_payload_schema.json: exact paths, types, closed enums
including the eight shipped planner phases, typed
unknown-value/missing dispositions); s41 redefined + s41b; s49
(self-reduced predicate count -> MALFORMED) and s50 (the 0.60
swing) registered.

**Flight v3.2**: the frozen predicate registry (three IDs,
n = 3 DERIVED, never producer-supplied); the matrix made total
(ADEQUATE row; SET-VALUED model reasons with
intersection-both-directions composition; truly closed enums —
"every other string" is dead, unknown is MALFORMED); the P5 slew
limit; P0A/P0B; vertical excursion typed |alt - alt_ref| <= 1.5
(the "band center" conflation dead); FIELD-BINDING = OPTION B
(immutable profile-law JSON + a separate Gate-3 binding artifact
with its own ancestry and walk) plus channel-1's GATE-3
COMPLETENESS check: zero PENDING markers in the effective config
at arming — identity and completeness are two checks, both
mandatory.

**Order C — the remedy is now repository law, not testimony**:
tools/asserted_edit.py committed (AnchorMiss raises loudly; an
edit with zero matches is an ABSENT edit) with the missed-anchor
fixture suite (tests/unit/test_asserted_edit.py — including the
exact R83 failure shape) executed green: 3/3.

## 3. Sequencing

THIS commit is the new GOVERNING candidate. Channels walk it;
then ONE source commit from both criteria + the schema artifact,
the complete battery (s1-s50 as still relevant) at one pushed
tip, publish-then-attest, the final-generation A091 run, support
before model, REG-2(v2) only from adequate-support outcomes.
Flight DISARMED behind v3.2, five gates, and the Gate-3
completeness check. F NO-GO.

## 4. Standing

Census 23; REG-2(v2) empty; post-final source ABSENT; A091
NO-GO; flight DISARMED; mechanism-2 verdict NONE; admissible
residual NONE; R26-1 held open; bridge open; repair shadow-only;
cohort-4 HOLD; Sakana STANDBY; sigma_a_cfg 0.35; no HOLD-lift
signature exists.
