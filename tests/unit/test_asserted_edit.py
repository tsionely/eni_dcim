"""The missed-anchor fixture (channel-2 on R84-85 order C): the
remedy must be shown to bite — a zero-match anchor raises, never
prints success."""
import pytest
from tools.asserted_edit import AnchorMiss, asserted_replace


def test_hit_replaces_exactly_once():
    assert asserted_replace("a (s33) b", "(s33)", "(s33) X") == "a (s33) X b"


def test_missed_anchor_raises_loudly():
    # The exact R83 failure shape: anchor assumed at line start,
    # actual text has it mid-sentence with a different prefix.
    text = "refusal before fitting; (s33) source bytes"
    with pytest.raises(AnchorMiss):
        asserted_replace(text, "  (s33) source bytes committed", "X")


def test_multi_match_is_also_a_miss():
    with pytest.raises(AnchorMiss):
        asserted_replace("x y x", "x", "z")  # 2 matches, expected 1
