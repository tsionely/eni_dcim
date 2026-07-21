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


def test_no_committed_script_bypasses_the_asserted_path():
    """Universal-use scan (channel-2 on R86 §7): no committed tool
    may call bare .replace on criterion files. The asserted path is
    the only lawful editor of docs/criteria."""
    import pathlib
    offenders = []
    for p in pathlib.Path("tools").glob("**/*.py"):
        if p.name == "asserted_edit.py":
            continue
        text = p.read_text(encoding="utf-8")
        if "docs/criteria" in text and ".replace(" in text:
            offenders.append(str(p))
    assert not offenders, f"bare .replace on criteria in: {offenders}"


def test_chained_anchor_on_never_existed_text_raises():
    """F5 companion (ADVISORY-32): the R84 no-op's exact shape — an
    edit anchored on text a PRIOR failed edit was supposed to create.
    Zero matches must raise, breaking the fabrication chain at link
    two."""
    import pytest as _pytest
    from tools.asserted_edit import AnchorMiss, asserted_replace
    file_text = "roster ends at (s33) here"
    never_created = "(s43) missing or inconsistent profile"
    with _pytest.raises(AnchorMiss):
        asserted_replace(file_text, never_created, "X")
