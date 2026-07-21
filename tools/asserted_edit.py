"""Asserted text replacement — the R85 remedy as repository law.

An edit whose anchor matches zero times is an ABSENT edit; printing
success over it is minting a green from an empty set (the R84/R85
missed-anchor incident: two silent no-ops chained across rounds).
Every scripted criterion edit goes through asserted_replace, which
fails loudly on an anchor miss instead of narrating success.
"""


class AnchorMiss(AssertionError):
    pass


def asserted_replace(text: str, old: str, new: str, expect: int = 1) -> str:
    """Replace old->new in text, asserting exactly `expect` matches."""
    n = text.count(old)
    if n != expect:
        raise AnchorMiss(
            f"anchor matched {n} times, expected {expect}: {old[:80]!r}")
    return text.replace(old, new)


def asserted_edit_file(path: str, old: str, new: str, expect: int = 1) -> int:
    # Atomic: a write failure can never leave a partial criterion.
    import os, tempfile
    with open(path, encoding="utf-8") as f:
        src = f.read()
    out = asserted_replace(src, old, new, expect)
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, path)
    return expect
