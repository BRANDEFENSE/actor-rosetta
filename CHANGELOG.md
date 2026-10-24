# Changelog

## 0.1.0 (2026-10-24)

First release.

- `resolve`, `search`, `explain` and the `actor-rosetta` command.
- Short-form rule: `Lazarus` resolves to Lazarus Group (trailing Group, Team, Gang or Crew removed, only when unambiguous).
- Data: groups with verified names, the primary source for each name, related names,
  names that are not aliases, and recorded disagreements between sources.
- Disagreements are recorded only when each side publishes the name itself and rests on a primary source; names are
  deduplicated by folded spelling and self-references are dropped.
- A name that primary sources give to two groups goes to one of them (ATT&CK name first, then the group it was
  coined for, then more distinct primary publishers) with a warning; only a tie is withheld. Every ATT&CK group
  keeps its ATT&CK name. `tests/test_known_names.py` holds the names analysts type first.
- Well-known groups that were missing are added, each name checked on a vendor page that lists it next to another
  name of the group: UNC1151, Donot (APT-C-35), Hunters International, Karakurt, Killnet, NoName057(16), UNC5174 and others.
- Brand rule: a ransomware brand with one operator resolves to it (DarkSide, Conti, REvil, SamSam, DoppelPaymer, Cactus);
  brands several groups deploy stay 'not an alias' (Clop, Black Basta). Duplicate records joined (Vice Spider into Vice Society).
- Hand review before release: 127 one-label groups that could not be vouched for are left out of this release.
