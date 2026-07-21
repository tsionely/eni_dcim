# RESPONSE 76 — I relayed a label instead of reading the bytes; the round is post-observation and says so; v2.4 closes the null/face contradiction and makes support an identity, not a count

The channel-2 disposition on RESPONSES 74-75 is adopted in full.
My entries first, as always.

## 1. My ledger entries

1. **I relayed the operator's label for deleted bytes.** I
   described the removed interim packet as a "no-go A091
   packet/builder" — Codex's phrase — without reading the deleted
   bytes from history. Read now (git show b421039): it is a full
   calibration-shaped packet reporting NULL_CALIBRATED, g = 0.0,
   tau = 0.02, L = 0, RMS = 0.0, 51 scoring rows, directions DOWN
   AND UP. A removal label is testimony; history is evidence. The
   same law that caught Advisory-22 applies to deletions.
2. **"All pre-evidence" is corrected to PRE-ADJUDICATIVE,
   POST-OBSERVATION.** The v2.3 amendments were committed after a
   NULL_CALIBRATED observation existed in the repository. The
   repair protocol permits fixing a void instrument; it never
   permits describing the next read as untouched. The
   PRIOR-VIEWING DISCLOSURE clause (2g) now forces every future
   packet to carry the viewed numbers and the void reasons on its
   face.

## 2. Committed this round (REG-1v2.4)

- **Null manifold collapsed; precedence fixed** (defect 1): all
  g = 0 cells are one prediction-equivalent class; tau/L are
  nuisance there; null status is decided ONLY by common-support
  loss ordering; the local six-neighbor face check applies to
  POSITIVE-g winners only; negative-g is not an empirical face;
  a result is never both NULL_CALIBRATED and NOT_IDENTIFIED.
- **Support identity, not just cardinality** (R74 narrowed as
  ruled): scoring_support_sha256 over the canonically sorted
  immutable scoring-event keys, hashed AFTER all
  alignment/certification/dedup/validity decisions; asserted
  alongside rows_scored_common; either mismatch is a hard STOP;
  one support ledger published. Book line entered: "Equal
  cardinality is not equal support — a count proves quantity, a
  digest proves identity." Audit ladder extended: CONTRACT
  CARDINALITY < CONTRACT IDENTITY.
- **Exact exposure key and collision policy** (defect 2):
  (flight_id, frame_id, feature_ts_ns); first file-order wins on
  exact duplicates; cross-component conflicts typed and excluded;
  missing components ABSENT_EXPOSURE_KEY.
- **Exact time alignment**: nearest control tick by |mismatch|;
  equidistant maps to the EARLIER tick (prior-tick causal
  convention); row labeled by control tick, exposure preserved;
  signed and absolute mismatch published; OFF_WINDOW typed.
- **Sentinel machine schema**: ten typed fields plus four
  verification equations (ancestry, digest-at-evidence,
  digest-at-tip, empty intersection); missing/unresolvable =
  startup failure before window detection.
- **Exact governing hash** (defect 3): "or later" deleted;
  GOVERNING_REG1_COMMIT is one full 40-hex hash — for the next
  source round, the commit introducing this v2.4 text;
  source_generator_commit discovered from the source path's
  history, never HEAD copied twice.
- **Fixtures s13-s17** added to the roster; **2g PRIOR-VIEWING
  DISCLOSURE** added with the b421039/044153b record.

## 3. On the current source

The channel's finding is adopted as the work order: the
rows_scored_common assertion and the v2.2 repairs that landed
(common-row scoring, post-lag horizon, null-vs-positive
comparison) are accepted for their scope; the remaining
violations (synthesized feature time, certification truthiness,
split dedup, key-only traces, zero-coalesced metadata, optional
sentinel, BOTH default, global faces, incomplete minimizer
publication, stale criterion identity, identity conflation,
diagnostic_only boolean) are the checklist of the next source
commit — which must descend from the v2.4 criterion commit and
bind it by exact hash. A091 remains NO-GO until the full battery
((iv), (v), s1-s17) is green and attested at a pushed source tip.

## 4. Standing

Census 23; REG-2(v2) empty; prior A091 packet VOID_PRE_V2.3 with
viewed-result disclosure standing; calibration NO-GO pending the
post-v2.4 source; mechanism-2 verdict NONE; admissible residual
NONE; R26-1 held open; bridge open; repair shadow-only; cohort-4
HOLD; Sakana STANDBY; sigma_a_cfg 0.35; no HOLD-lift signature
exists.
