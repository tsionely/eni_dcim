# RESPONSE 25 — 15B invariants in the build; one honest performance signal

Implemented and pinned (177/177), commit a150ece: exact-exposure
pairing (identical exposure ts, nearest-timestamp joins gone — the S2
fixtures now pair per-image as reality does); consume-once semantics
pinned as kill test P1 (25 polls of one held packet = one row per
source history, one pair); the armed latch (fresh measured detection
≤3.5m arms parallel production for the approach; detector loss and
range bounce never disarm it — the fallback solo budget is bypassed
while armed); fallback-realistic seeding (the tracker's parallel
prior is the believed continuity chain, exactly what it has alone —
answering 15B §2's seeding question in the fallback-realistic
direction; the SIDE metric is pixel-derived regardless).

Honest signal for kill test P4: the armed tracker raised mock loop
overruns to 9.3% in this container's smoke (typical 0.4-2%). The
container is CPU-poor and the mock alone is not the verdict, but the
number goes to the wall-clock replay comparison as specified —
detector-only vs parallel on the same recorded frames, P95/P99 and
feature-delivery age.

QA now owns the decisive run on a150ece: P1-P4 kill tests, the forced
transition replay (§8 semantics: FULL healthy through N, withheld from
N+1; one transition, same epoch/owner, no spike, no phase reset), and
the two-component sigma design (§7: paired-switch residual + the
FULL-withheld maintenance residual, stratified; the release sigma
covers both and never shrinks on correlated same-frame agreement
alone). Cohort 4 holds until the twelve-row list is green.
