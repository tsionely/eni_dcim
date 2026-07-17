"""Side-pair identity certificate (think-tank C1 + invariant 6, v1).

Identity is INHERITED, not re-derived: certification happens where it is
cheap and overdetermined — a full detector quad that passed the shipped
scale-consistency + grazing-normal gates — and is then MAINTAINED down
the tracker chain by per-frame invariants on the side pair:

    1. chain      unbroken descent (gaps <= chain_gap_s)
    2. pair scale measured separation vs fx*W/Z_prior within band
    3. bar-ness   both side edges show a bounded red run at bar width,
                  L/R widths agreeing — a banner sheet edge or a
                  floor-to-ceiling pillar has no such partner structure
                  (this is the executioner for the banner-edge impostor
                  pair, whose separation ratio 1.25 PASSES the scale
                  band)
    4. support    both side edges supported over enough of their span

States: CERTIFIED -> full servo authority; PROBATION -> tracking/rate
only, promoted back after `promote_after` consecutive clean frames but
NEVER promoted fresh below the terminal floor (~1.4m — two naked
vertical edges are never certified in the terminal zone, no matter how
good one frame looks); NONE -> the T3 gap policy owns the aircraft.
Time degrades the state on queries: a stale chain is a broken chain.

v1 notes: the expansion probe (log-separation rate vs Z_dot/Z) joins
with the T1 plane filter; invariant 6b's banner-row constant waits for
the A6 geometry decision — both documented in the design contract.
"""
from __future__ import annotations

CERTIFIED = "certified"
PROBATION = "probation"
NONE = "none"


class SidePairCertificate:
    def __init__(self, chain_gap_s: float = 0.15, scale_min: float = 0.65,
                 scale_max: float = 1.5, min_support: float = 0.4,
                 width_agree: float = 0.5, promote_after: int = 3,
                 terminal_floor_m: float = 1.4) -> None:
        self.chain_gap_s = chain_gap_s
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.min_support = min_support
        self.width_agree = width_agree
        self.promote_after = promote_after
        self.terminal_floor = terminal_floor_m
        self._status = NONE
        self._last_ok_ns: int | None = None
        self._clean_streak = 0

    # ------------------------------------------------------------- events

    def on_full_quad(self, ts_ns: int) -> None:
        """A fully-gated detector quad re-anchors certification."""
        self._status = CERTIFIED
        self._last_ok_ns = ts_ns
        self._clean_streak = 0

    def on_relock_or_collision(self) -> None:
        """Epoch change: the certificate never survives a target change."""
        self._status = NONE
        self._last_ok_ns = None
        self._clean_streak = 0

    def update(self, ts_ns: int, z_prior_m: float, sep_pred_px: float,
               sep_meas_px: float, fx_w_px_m: float,
               left_widths: list[float], right_widths: list[float],
               left_support: float, right_support: float) -> str:
        """Feed one tracker frame's side-pair measurements."""
        chain_ok = (self._last_ok_ns is not None
                    and (ts_ns - self._last_ok_ns) / 1e9 <= self.chain_gap_s)
        ratio = sep_meas_px * z_prior_m / fx_w_px_m if fx_w_px_m > 0 else 0.0
        scale_ok = self.scale_min <= ratio <= self.scale_max
        barness_ok = self._barness(sep_meas_px, left_widths, right_widths)
        support_ok = (left_support >= self.min_support
                      and right_support >= self.min_support)
        others = (scale_ok, barness_ok, support_ok)

        if chain_ok and all(others):
            self._last_ok_ns = ts_ns
            if self._status == PROBATION:
                self._clean_streak += 1
                # Terminal rule: below the floor, PROBATION is the ceiling.
                if (self._clean_streak >= self.promote_after
                        and z_prior_m > self.terminal_floor):
                    self._status = CERTIFIED
            # CERTIFIED stays certified; NONE with a live chain cannot
            # happen (chain requires a prior anchor).
        elif all(others):
            # Chain broken but the pair still looks right: quarantine.
            self._last_ok_ns = ts_ns
            self._status = PROBATION
            self._clean_streak = 0
        elif sum(bool(x) for x in others) >= 2 and chain_ok:
            # One marginal invariant: demote, keep tracking.
            self._last_ok_ns = ts_ns
            self._status = PROBATION
            self._clean_streak = 0
        else:
            self._status = NONE
            self._clean_streak = 0
        return self._status

    # ------------------------------------------------------------- queries

    def status_at(self, now_ns: int) -> str:
        """Time degrades the state: a stale chain is a broken chain."""
        if self._last_ok_ns is None:
            return NONE
        age = (now_ns - self._last_ok_ns) / 1e9
        if age > 4 * self.chain_gap_s:
            return NONE
        if age > self.chain_gap_s and self._status == CERTIFIED:
            return PROBATION
        return self._status

    # ----------------------------------------------------------- internals

    def _barness(self, sep_px: float, lw: list[float], rw: list[float]) -> bool:
        if len(lw) < 3 or len(rw) < 3:
            return False
        lm = sorted(lw)[len(lw) // 2]
        rm = sorted(rw)[len(rw) // 2]
        for m in (lm, rm):
            # w_bar measured 0.188m (analyst A4, corrected) =>
            # width/separation ~ 0.118; band [2px, 0.30*sep]
            # keeps margin for bloom while excluding sheets.
            if not (2.0 <= m <= 0.30 * max(sep_px, 1.0)):
                return False      # unbounded run (pillar/sheet) or noise
        hi, lo = max(lm, rm), max(min(lm, rm), 1e-6)
        return (hi - lo) / hi <= self.width_agree
