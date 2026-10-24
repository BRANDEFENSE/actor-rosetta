"""Data model and lookup logic. Pure standard library, no network access."""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .fold import fold


class NameConflictError(ValueError):
    """The same (folded) name is published for two different groups."""


@dataclass(frozen=True)
class Source:
    publisher: str
    url: str

    def to_dict(self) -> Dict[str, str]:
        return {"publisher": self.publisher, "url": self.url}


@dataclass(frozen=True)
class GroupRef:
    """Pointer to another group: id is None when that group is not in the data."""

    id: Optional[str]
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}


@dataclass(frozen=True)
class Related:
    """A name the sources call overlapping with, or associated with, this group (not an alias)."""

    name: str
    group: Optional[GroupRef]
    sources: Tuple[Source, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "group": self.group.to_dict() if self.group else None,
                "sources": [s.to_dict() for s in self.sources]}


@dataclass(frozen=True)
class NotAlias(Related):
    """A name often listed for this group that a primary source ties elsewhere."""

    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = Related.to_dict(self)
        d["reason"] = self.reason
        return d


@dataclass(frozen=True)
class Group:
    id: str
    canonical: str
    attack_id: Optional[str]
    names: Tuple[str, ...]
    sources: Dict[str, Tuple[Source, ...]]
    related: Tuple[Related, ...] = ()
    not_aliases: Tuple[NotAlias, ...] = ()
    disputes: Tuple[Dict[str, Any], ...] = ()
    misp_galaxy: Optional[Dict[str, str]] = None
    profile: Optional[str] = None

    @property
    def misp_tag(self) -> Optional[str]:
        return self.misp_galaxy["tag"] if self.misp_galaxy else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "canonical": self.canonical,
            "attack_id": self.attack_id,
            "misp_galaxy": self.misp_galaxy,
            "names": [{"name": n, "sources": [s.to_dict() for s in self.sources[n]]} for n in self.names],
            "related": [r.to_dict() for r in self.related],
            "not_aliases": [r.to_dict() for r in self.not_aliases],
            "disputes": list(self.disputes),
            "profile": self.profile,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Group":
        def srcs(rows: Iterable[Dict[str, str]]) -> Tuple[Source, ...]:
            return tuple(Source(r["publisher"], r["url"]) for r in rows)

        def ref(x: Optional[Dict[str, Any]]) -> Optional[GroupRef]:
            return GroupRef(x.get("id"), x["name"]) if x else None

        return cls(
            id=d["id"], canonical=d["canonical"], attack_id=d.get("attack_id"),
            names=tuple(n["name"] for n in d["names"]),
            sources={n["name"]: srcs(n["sources"]) for n in d["names"]},
            related=tuple(Related(r["name"], ref(r.get("group")), srcs(r["sources"])) for r in d.get("related", [])),
            not_aliases=tuple(NotAlias(r["name"], ref(r.get("group")), srcs(r["sources"]), r.get("reason", ""))
                              for r in d.get("not_aliases", [])),
            disputes=tuple(d.get("disputes", [])),
            misp_galaxy=d.get("misp_galaxy"), profile=d.get("profile"),
        )


@dataclass
class Explanation:
    """What the data says about one string."""

    query: str
    group: Optional[Group] = None  # the group the string resolves to, if any
    lines: List[str] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def __str__(self) -> str:
        return self.text

    def to_dict(self) -> Dict[str, Any]:
        return {"query": self.query, "resolves_to": self.group.id if self.group else None,
                "text": self.lines, "sources": [s.to_dict() for s in self.sources]}


_LEET = str.maketrans("01345", "oleas")
_GENERIC_SUFFIXES = ("group", "team", "gang", "crew")


def short_form(name: str) -> Optional[str]:
    """Folded name without a trailing generic word ('Lazarus Group' -> 'lazarus'), else None."""
    words = name.split()
    if len(words) > 1 and words[-1].casefold() in _GENERIC_SUFFIXES:
        f = fold(" ".join(words[:-1]))
        return f if len(f) >= 4 else None
    return None


def _per(sources: Iterable[Source], limit: int = 2) -> str:
    rows = list(sources)[:limit]
    return "; ".join("%s (%s)" % (s.publisher, s.url) for s in rows)


class Dataset:
    """All groups plus the name indexes."""

    def __init__(self, groups: Iterable[Group], meta: Optional[Dict[str, Any]] = None):
        self.meta: Dict[str, Any] = meta or {}
        self.groups: List[Group] = list(groups)
        self._by_name: Dict[str, Group] = {}
        self._by_id: Dict[str, Group] = {}
        self._related: Dict[str, List[Tuple[Group, Related]]] = {}
        self._not_alias: Dict[str, List[Tuple[Group, NotAlias]]] = {}
        self._short: Dict[str, Optional[Group]] = {}  # short form -> group; None when two groups share it
        for g in self.groups:
            self._by_id[g.id] = g
            for n in g.names:
                f = fold(n)
                prev = self._by_name.get(f)
                if prev is not None and prev.id != g.id:
                    raise NameConflictError(
                        "name %r is published for two groups: %s and %s" % (n, prev.id, g.id))
                self._by_name[f] = g
            for r in g.related:
                self._related.setdefault(fold(r.name), []).append((g, r))
            for r in g.not_aliases:
                self._not_alias.setdefault(fold(r.name), []).append((g, r))
            for n in g.names:
                sf = short_form(n)
                if sf:
                    self._short[sf] = g if self._short.get(sf, g) is g else None
        for sf in list(self._short):
            g = self._short[sf]
            own = {fold(r.name) for r in (g.related + g.not_aliases)} if g else set()
            if g is None or sf in self._by_name or sf in own:
                del self._short[sf]

    @property
    def version(self) -> str:
        return str(self.meta.get("version", "unknown"))

    def get(self, group_id: str) -> Optional[Group]:
        return self._by_id.get(group_id.lower())

    def resolve(self, name: str) -> Optional[Group]:
        """The group that publishes this name, or None. Related and not-alias names never resolve.

        One documented extension: a published name minus a trailing 'Group', 'Team', 'Gang' or 'Crew'
        ('Lazarus' for 'Lazarus Group') also resolves, when that short form is unambiguous.
        """
        f = fold(name)
        return self._by_name.get(f) or self._short.get(f)

    def is_short_form(self, name: str) -> bool:
        """True when resolve(name) only works through the short-form rule."""
        f = fold(name)
        return f not in self._by_name and f in self._short

    def search(self, text: str, limit: int = 5, cutoff: float = 0.75) -> List[Tuple[Group, float, str]]:
        """Fuzzy match on published names: [(group, score, matched_name)], best first, one row per group."""
        q = fold(text)
        if not q:
            return []
        best: Dict[str, Tuple[float, str]] = {}
        for g in self.groups:
            for n in g.names:
                score = self._score(q, fold(n))
                sf = short_form(n)
                if sf:  # 'lazrus' should still find 'Lazarus Group'
                    score = max(score, self._score(q, sf))
                if score >= cutoff and score > best.get(g.id, (0.0, ""))[0]:
                    best[g.id] = (score, n)
        rows = [(self._by_id[i], round(s, 3), n) for i, (s, n) in best.items()]
        rows.sort(key=lambda r: (-r[1], r[0].canonical.casefold()))
        return rows[:limit]

    @staticmethod
    def _score(q: str, f: str) -> float:
        if q == f:
            return 1.0
        sm = difflib.SequenceMatcher(None, q, f)
        if sm.real_quick_ratio() < 0.5 or sm.quick_ratio() < 0.5:
            return 0.0
        score = sm.ratio()
        if len(q) >= 4 and q in f:  # a fragment of a longer name
            score = max(score, 0.7 + 0.25 * len(q) / len(f))
        return min(score, 0.999)

    def explain(self, name: str) -> Explanation:
        """What the data says about this string: published name, related name, or not an alias."""
        f = fold(name)
        g = self._by_name.get(f)
        ex = Explanation(query=name, group=g)
        if g is None and f in self._short:
            g = ex.group = self._short[f]
            full = next(n for n in g.names if short_form(n) == f)
            ex.lines.append("'%s' is taken as the short form of '%s'. It is not itself a published name. "
                            "Source of that name: %s." % (name, full, _per(g.sources[full])))
            ex.sources += list(g.sources[full])
        elif g is not None:
            tag = " (ATT&CK %s)" % g.attack_id if g.attack_id else ""
            shown = next((n for n in g.names if fold(n) == f), name)
            ex.lines.append("'%s' is a verified name of %s%s. Source: %s." % (shown, g.canonical, tag,
                                                                              _per(g.sources[shown])))
            ex.sources += list(g.sources[shown])
        for owner, r in self._related.get(f, []):
            where = " (tracked as %s)" % r.group.name if r.group else ""
            ex.lines.append("'%s' is not treated as an alias of %s. Sources call it overlapping or associated "
                            "activity%s. Source: %s." % (r.name, owner.canonical, where, _per(r.sources)))
            ex.sources += list(r.sources)
        for owner, r in self._not_alias.get(f, []):
            ex.lines.append(self._not_alias_line(owner, r))
            ex.sources += list(r.sources)
        if g is None and ex.lines:
            near = [r for r in self.search(name, limit=3) if r[1] >= 0.7]
            if near:
                ex.lines.append("'%s' is not a published name. Closest published names: %s." % (
                    name, ", ".join("%s (%s)" % (n, gr.canonical) for gr, _, n in near)))
        if not ex.lines:
            alt = self._near_unpublished(f)
            if alt:
                sub = self.explain(alt)
                sub.query = name
                sub.lines.insert(0, "No entry for '%s'. It is close to '%s':" % (name, alt))
                return sub
            near = self.search(name, limit=3)
            if near:
                ex.lines.append("No data for '%s'. Closest published names: %s." % (
                    name, ", ".join("%s (%s, %s)" % (n, gr.canonical, s) for gr, s, n in near)))
            else:
                ex.lines.append("No data for '%s'." % name)
        return ex

    def _near_unpublished(self, f: str) -> Optional[str]:
        """A related or not-alias name that is a near miss of f (cl0p for clop), else None."""
        best, pick = 0.8, None
        for index in (self._related, self._not_alias):
            for key, rows in index.items():
                if len(key) >= 4 and key != f and abs(len(key) - len(f)) <= 2:
                    score = difflib.SequenceMatcher(None, f, key).ratio()
                    if f.translate(_LEET) == key.translate(_LEET):
                        score = max(score, 0.95)
                    if score > best:
                        best, pick = score, rows[0][1].name
        return pick

    @staticmethod
    def _not_alias_line(owner: Group, r: NotAlias) -> str:
        if r.reason == "other group":
            other = r.group.name if r.group else "another group"
            return ("'%s' is not an alias of %s: a primary source tracks it as a separate group (%s). Source: %s."
                    % (r.name, owner.canonical, other, _per(r.sources)))
        kind = r.reason or "not a group name"
        what = {"malware": "malware", "ransomware": "ransomware", "tool": "a tool", "campaign": "a campaign",
                "operation": "an operation", "persona": "a persona", "umbrella label": "an umbrella label",
                "vulnerability": "a vulnerability"}.get(kind, "not a group name")
        if what != "not a group name":
            what += ", not a group name"
        if r.group:
            tail = ("; also listed under %s" % r.group.name if kind == "umbrella label"
                    else "; the group tracked for it is %s" % r.group.name)
        else:
            tail = ""
        return "'%s' is %s, so it is not an alias of %s%s. Source: %s." % (r.name, what, owner.canonical, tail,
                                                                          _per(r.sources))
