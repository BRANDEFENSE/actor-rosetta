# actor-rosetta

Resolve any threat-actor group name to the group, all its verified names, the primary source for each name, and where sources disagree.

Python 3.9+, no dependencies, no network access at runtime.

## Why

Vendors name the same activity differently, and public alias lists mix real aliases with other things: names of other groups that only overlap, and names of malware, campaigns or operations.

This package keeps only names that a primary source ties to the group, and records the rest as separate facts (related names, names that are not aliases, disagreements), so a lookup does not hand you a wrong merge without saying so.

What we found when we checked the lists (computed from the verification data when the package is built; see `meta.verification` in the data file):

<!-- stats:start -->
Data version 2026-10-24: 315 groups, 1255 verified names, 244 related names, 593 names that are not aliases, 14 recorded disagreements.

Coverage is thin: 94 of 315 groups (29.8%) have exactly one verified name, so for many groups this is a short list of names, not a complete alias database. It grows as verification adds names.

So far we checked 2782 names that common alias lists attach to 385 groups. These are the priority groups (the best-known and most confused first), not a random sample. 36.2% of the names were confirmed by a primary source. 33.9% turned out to be malware, campaigns, operations, personas, other groups or only overlapping activity. The rest could not be confirmed and are not published.

583 of those names appear only on lead lists (no vendor or agency page carried them in our candidate data): 3.9% of them were confirmed, 96.1% were not.
<!-- stats:end -->

## Install

```
pip install git+https://github.com/BRANDEFENSE/actor-rosetta
```

The PyPI package (`pip install actor-rosetta`) follows shortly.

From source:

```
git clone https://github.com/BRANDEFENSE/actor-rosetta
cd actor-rosetta
pip install .
```

## One minute

Command line:

```
$ actor-rosetta "Cozy Bear"          # names, ATT&CK id, publishers, related names, warnings
$ actor-rosetta --json midnight-blizzard
$ actor-rosetta search "Cozy Baer"   # fuzzy match for typos
$ actor-rosetta explain CL0P         # what the data says about a string, also when it is not a group
$ actor-rosetta list                 # all groups
$ actor-rosetta --version            # code and data version
```

`actor-rosetta <name>` exits with 0 when the name is a published name of a group and 1 when it is not (the message then says what the data knows about the string).

Python:

```python
import actor_rosetta as ar

g = ar.resolve("APT 29")            # exact match after folding; None if the name is not published
g.canonical, g.attack_id            # ('APT29', 'G0016')
g.names                             # all verified names
g.sources["Midnight Blizzard"]      # [Source(publisher=..., url=...)]
g.related, g.not_aliases, g.disputes
g.misp_tag                          # 'misp-galaxy:threat-actor="APT29"'
g.to_dict()

ar.search("Cozy Baer")              # [(Group, score, matched_name), ...]
print(ar.explain("APT38"))          # "'APT38' is a verified name of APT38 ... 'APT38' is not an alias of Lazarus Group: ..."
```

Matching folds names: case-insensitive, Unicode NFKC, and spaces, hyphens, dots and underscores are ignored, so `APT 29`, `apt-29` and `Cozy-Bear` work.

One extra rule: a published name with a trailing "Group", "Team", "Gang" or "Crew" removed also resolves when the short form is unambiguous and not listed as a related or not-alias name of that group, so `Lazarus` finds Lazarus Group. The CLI says when it used this rule. Names that are not published for any group (for example a name we could not verify) do not resolve.

`resolve()` never returns a group for a name that is only related to it or that is not an alias. It returns `None`, and `explain()` tells you why. When primary sources give one name to two groups, the name goes to one group and the other lists it as related; the group that keeps it carries a warning. The name goes to the group whose ATT&CK name it is, else to the group it was coined for, else to the side with more distinct primary publishers. On a tie it is withheld from both. Two records of one group (for example a Microsoft row and its ATT&CK group) are joined when one confirms the other's name and neither calls it a different or overlapping group.

A ransomware brand resolves to the group that runs it when primary sources name one operator (`DarkSide` gives GOLD WATERFALL, `Conti` gives Wizard Spider). A brand that several tracked groups deploy is not an alias of any of them (`Clop`, `Black Basta`); malware families never are. Before release every group was also reviewed by hand; groups the reviewers could not vouch for beyond a single vendor label are left out until a later update checks them.

## Data format

`src/actor_rosetta/data/actors.json`:

```json
{
  "meta": {"version": "...", "counts": {...}, "verification": {...}, "licence": "CC BY 4.0",
           "attribution": "Brandefense Research Team"},
  "groups": [{
    "id": "g0016",
    "canonical": "APT29",
    "attack_id": "G0016",
    "misp_galaxy": {"cluster": "threat-actor", "value": "APT29", "uuid": "...", "tag": "misp-galaxy:threat-actor=\"APT29\""},
    "names": [{"name": "Midnight Blizzard", "sources": [{"publisher": "...", "url": "..."}]}],
    "related": [{"name": "...", "group": {"id": null, "name": "..."}, "sources": [...]}],
    "not_aliases": [{"name": "...", "reason": "malware", "group": null, "sources": [...]}],
    "disputes": [{"type": "shared-name", "names": ["..."], "with": [{"id": "...", "name": "..."}], "sources": [...]}],
    "profile": "https://brandefense.io/knowledge-hub/..."
  }]
}
```

- `names`: verified names. Each has at least one source (publisher and link). No quotes are stored.
- `related`: names the sources call overlapping or associated with this group, not aliases.
- `not_aliases`: names often listed for this group that a primary source ties to another group (`reason: "other group"`) or that are malware, a campaign, an operation, a persona or an umbrella label.
- `disputes`: places where primary sources disagree, for example one name used by two groups. Only recorded when each side rests on a primary source.
- `misp_galaxy`: the matching MISP galaxy entry, only when the MISP value is itself one of the verified names.
- `profile`: the Brandefense Knowledge Hub profile, only when one exists.

## How names are verified

A name is published only when a primary source lists it for the group: the vendor that coined it (its own page), MITRE ATT&CK, or a government text (CISA, NCSC, FBI, CERT-UA and similar). Lead lists (MISP galaxy, Malpedia, ETDA, EternalLiberty, APTmap, community sheets, Wikipedia) and news sites are used to find candidates and are never cited as evidence. Names that fail the check are not published.

Every group is a judgement about what a source means by its own group. Where vendors disagree we do not pick a side: the groups stay apart and the disagreement is recorded.

## What is not included

- Names that could not be verified against a primary source.
- Names a primary source only supports for a different group.
- Content of sources whose terms do not allow redistribution: the data holds links and publisher names only, no quotes or copies of vendor text.

## Updates

New versions are released from time to time, when verification adds names. The data version is in `actor-rosetta --version` and in `meta.version`. If you find a wrong or missing name, open an issue with a link to the primary source.

## Licence and citation

- Code: Apache-2.0 (`LICENSE`).
- Data: CC BY 4.0 (`data/LICENSE-DATA`). Credit "Brandefense Research Team".
- Cite with `CITATION.cff`.

MITRE ATT&CK notice: ATT&CK ids and group names come from MITRE ATT&CK and are used under the MITRE ATT&CK Terms of Use. (c) 2015-2026 The MITRE Corporation. This work reproduces and/or references materials created by The MITRE Corporation. ATT&CK is a registered trademark of The MITRE Corporation. The MISP galaxy (CC0) informed how candidate groups were built. See `NOTICE`.

Maintained by the [Brandefense Research Team](https://brandefense.io/).
