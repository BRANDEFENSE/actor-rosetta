"""Command line: actor-rosetta <name> | search <text> | list | explain <name> | --version."""
from __future__ import annotations

import json
import os
import sys
from typing import List, Optional

from . import __version__
from .model import Dataset, Group
from .resolver import load

USAGE = """usage: actor-rosetta [--json] <name>
       actor-rosetta [--json] search <text>
       actor-rosetta [--json] list
       actor-rosetta [--json] explain <name>
       actor-rosetta --version

Resolves a threat-actor name to the group, its verified names and the source for each name."""
MAX_INPUT = 200


def _out(text: str) -> None:
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Reader closed the pipe (head, less). Point stdout at devnull so interpreter exit stays quiet.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        raise SystemExit(0)


def _err(text: str) -> None:
    sys.stderr.write(text + "\n")


def format_group(g: Group) -> str:
    head = g.canonical + ("  (ATT&CK %s)" % g.attack_id if g.attack_id else "")
    lines = [head]
    if g.profile:
        lines.append("Profile: " + g.profile)
    if g.misp_tag:
        lines.append("MISP galaxy: " + g.misp_tag)
    lines += ["", "Names (%d)" % len(g.names)]
    for n in g.names:
        lines.append("  %s - %s" % (n, "; ".join(sorted({s.publisher for s in g.sources[n]}))))
    if g.related:
        lines += ["", "Related, not aliases"]
        for r in g.related:
            lines.append("  %s%s - %s" % (r.name, " (%s)" % r.group.name if r.group and r.group.name != r.name else "",
                                          "; ".join(sorted({s.publisher for s in r.sources}))))
    if g.not_aliases:
        lines += ["", "Often listed, not aliases"]
        for r in g.not_aliases:
            other = " -> %s" % r.group.name if r.group else ""
            lines.append("  %s: %s%s - %s" % (r.name, r.reason, other, "; ".join(sorted({s.publisher for s in r.sources}))))
    if g.disputes:
        lines += ["", "Warnings"]
        for d in g.disputes:
            with_ = ", ".join(w["name"] for w in d.get("with", []))
            lines.append("  Sources disagree (%s): %s; also used for %s" % (d["type"], ", ".join(d["names"]), with_))
    return "\n".join(lines)


def _lookup(ds: Dataset, name: str, as_json: bool) -> int:
    g = ds.resolve(name)
    if g is not None:
        short = ds.is_short_form(name)
        if as_json:
            d = g.to_dict()
            if short:
                d["match"] = {"query": name, "type": "short-form"}
            _out(json.dumps(d, indent=2, ensure_ascii=False))
        else:
            if short:
                _out("Note: '%s' is not a published name; taken as the short form of '%s'." % (name, g.canonical))
            _out(format_group(g))
        return 0
    ex = ds.explain(name)
    if as_json:
        _out(json.dumps({"query": name, "group": None, "explanation": ex.to_dict(),
                         "near": [{"id": gr.id, "canonical": gr.canonical, "score": s, "matched_name": n}
                                  for gr, s, n in ds.search(name, limit=3)]}, indent=2, ensure_ascii=False))
    else:
        _err(ex.text)
    return 1


def _search(ds: Dataset, text: str, as_json: bool) -> int:
    rows = ds.search(text)
    if as_json:
        _out(json.dumps([{"id": g.id, "canonical": g.canonical, "attack_id": g.attack_id, "score": s,
                          "matched_name": n} for g, s, n in rows], indent=2, ensure_ascii=False))
    else:
        for g, s, n in rows:
            _out("%.2f  %s  (%s)  matched '%s'" % (s, g.canonical, g.attack_id or g.id, n))
        if not rows:
            _err("No close match for '%s'." % text)
    return 0 if rows else 1


def _list(ds: Dataset, as_json: bool) -> int:
    if as_json:
        _out(json.dumps([g.to_dict() for g in ds.groups], indent=2, ensure_ascii=False))
    else:
        for g in ds.groups:
            _out("%s\t%s\t%d names" % (g.attack_id or g.id, g.canonical, len(g.names)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    rest: List[str] = []
    for a in args:
        if a == "--json":
            as_json = True
        elif a in ("-h", "--help"):
            _out(USAGE)
            return 0
        elif a == "--version":
            _out("actor-rosetta %s (data %s)" % (__version__, load().version))
            return 0
        elif a.startswith("-") and len(a) > 1 and not rest:
            _err("actor-rosetta: unknown option %s\n%s" % (a, USAGE))
            return 2
        else:
            rest.append(a)
    if not rest:
        _err(USAGE)
        return 2
    if len(" ".join(rest)) > MAX_INPUT:
        _err("actor-rosetta: input longer than %d characters; threat-actor names are shorter" % MAX_INPUT)
        return 2
    ds = load()
    cmd, tail = rest[0], " ".join(rest[1:]).strip()
    if cmd in ("list", "search", "explain"):
        if cmd == "list" and tail:
            _err("actor-rosetta: 'list' takes no argument\n" + USAGE)
            return 2
        if cmd != "list" and not tail:
            _err("actor-rosetta: '%s' needs a name or text\n%s" % (cmd, USAGE))
            return 2
    if cmd == "list":
        return _list(ds, as_json)
    if cmd == "search":
        return _search(ds, tail, as_json)
    if cmd == "explain":
        ex = ds.explain(tail)
        _out(json.dumps(ex.to_dict(), indent=2, ensure_ascii=False) if as_json else ex.text)
        return 0
    return _lookup(ds, " ".join(rest), as_json)


if __name__ == "__main__":
    sys.exit(main())
