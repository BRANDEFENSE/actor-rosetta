import json
import os
import re
import sys
import unittest
from importlib import resources
from urllib.parse import urlparse

import actor_rosetta as ar
from actor_rosetta.model import Dataset, Group, NameConflictError

DATA = json.loads(resources.files("actor_rosetta").joinpath("data/actors.json").read_text(encoding="utf-8"))
LEAD_HOSTS = ("misp-galaxy.org", "malpedia.caad.fkie.fraunhofer.de", "apt.etda.or.th", "wikipedia.org",
              "andreacristaldi.github.io", "docs.google.com")


def cid(name):
    g = ar.resolve(name)
    assert g is not None, "%s did not resolve" % name
    return g.id


class Folding(unittest.TestCase):
    def test_fold_rules(self):
        self.assertEqual(ar.fold("APT 29"), "apt29")
        self.assertEqual(ar.fold("apt-29"), "apt29")
        self.assertEqual(ar.fold("Cozy-Bear"), "cozybear")
        self.assertEqual(ar.fold("Temp.Veles"), "tempveles")
        self.assertEqual(ar.fold("a_b c"), "abc")
        self.assertEqual(ar.fold("ＡＰＴ２９"), "apt29")  # NFKC full-width forms
        self.assertEqual(ar.fold(""), "")

    def test_resolve_variants(self):
        for q in ("APT29", "APT 29", "apt-29", "Apt_29", "cozy bear", "Cozy-Bear", "COZY.BEAR"):
            self.assertEqual(cid(q), cid("APT29"), q)

    def test_unknown_is_none(self):
        self.assertIsNone(ar.resolve("definitely not a group"))
        self.assertIsNone(ar.resolve(""))


class Search(unittest.TestCase):
    def test_typo(self):
        rows = ar.search("Cozy Baer")
        self.assertTrue(rows)
        group, score, matched = rows[0]
        self.assertEqual(group.id, cid("APT29"))
        self.assertEqual(matched, "Cozy Bear")
        self.assertTrue(0.6 <= score < 1.0)

    def test_exact_scores_one_and_limit(self):
        rows = ar.search("Midnight Blizzard", limit=3)
        self.assertEqual(rows[0][1], 1.0)
        self.assertLessEqual(len(rows), 3)

    def test_one_row_per_group(self):
        ids = [g.id for g, _, _ in ar.search("blizzard", limit=20)]
        self.assertEqual(len(ids), len(set(ids)))


class HardCases(unittest.TestCase):
    def test_apt29_names(self):
        a = cid("APT29")
        for n in ("Cozy Bear", "Midnight Blizzard", "NOBELIUM", "UNC2452"):
            self.assertEqual(cid(n), a, n)

    def test_lazarus_apt38_andariel_apart(self):
        ids = {cid("Lazarus Group"), cid("APT38"), cid("Andariel")}
        self.assertEqual(len(ids), 3)

    def test_apt35_vs_apt42(self):
        self.assertNotEqual(cid("APT35"), cid("APT42"))
        self.assertEqual(cid("APT35"), cid("Charming Kitten"))

    def test_ta505_fin11_clop(self):
        self.assertNotEqual(cid("TA505"), cid("FIN11"))
        self.assertIsNone(ar.resolve("CL0P"))  # ransomware, not a group name
        text = ar.explain("CL0P").text
        self.assertIn("ransomware", text)
        self.assertIn("not an alias", text)

    def test_sandworm_family(self):
        s = cid("Sandworm")
        self.assertEqual(cid("APT44"), s)
        self.assertEqual(cid("Seashell Blizzard"), s)

    def test_related_name_does_not_resolve_to_other_group(self):
        # APT38 is related to / separate from Lazarus: it must not resolve to Lazarus
        self.assertNotEqual(cid("APT38"), cid("Lazarus Group"))
        text = ar.explain("APT38").text
        self.assertIn("not an alias of Lazarus Group", text)

    def test_shared_name_withheld_from_both(self):
        # a name that two groups both publish is withheld, not given to one of them
        self.assertIsNone(ar.resolve("CharmingCypress"))
        self.assertIn("not treated as an alias", ar.explain("CharmingCypress").text)

    def test_near_miss_of_not_alias(self):
        self.assertIn("CL0P", ar.explain("Clop").text)


class ShortForm(unittest.TestCase):
    def test_lazarus_resolves_to_lazarus_group(self):
        self.assertEqual(cid("Lazarus"), cid("Lazarus Group"))
        self.assertTrue(ar.load().is_short_form("Lazarus"))
        self.assertFalse(ar.load().is_short_form("Lazarus Group"))
        self.assertIn("short form of 'Lazarus Group'", ar.explain("Lazarus").lines[0])

    def test_short_form_never_beats_exact_name(self):
        ds = ar.load()
        for sf, g in ds._short.items():
            self.assertNotIn(sf, ds._by_name)
            self.assertIs(ds.resolve(sf), g)

    def test_short_form_not_for_related_names(self):
        ds = ar.load()
        for g in ds.groups:
            own = {ar.fold(r.name) for r in g.related + g.not_aliases}
            for sf, owner in ds._short.items():
                if owner is g:
                    self.assertNotIn(sf, own)


class Disputes(unittest.TestCase):
    def test_no_phantom_iridium_on_magic_hound(self):
        for name in ("APT35", "Sandworm"):
            for d in ar.resolve(name).disputes:
                self.assertNotIn("iridium", {ar.fold(n) for n in d["names"]}, name)

    def test_disputes_are_clean(self):
        for g in DATA["groups"]:
            own = {ar.fold(n["name"]) for n in g["names"]} | {ar.fold(g["canonical"])}
            for d in g["disputes"]:
                folded = [ar.fold(n) for n in d["names"]]
                self.assertEqual(len(folded), len(set(folded)), (g["id"], d["names"]))
                self.assertTrue(d["with"], g["id"])
                for w in d["with"]:
                    self.assertNotIn(ar.fold(w["name"]), own, (g["id"], w))
                self.assertTrue(d["sources"], (g["id"], d["names"]))


class DataIntegrity(unittest.TestCase):
    def test_no_name_for_two_groups(self):
        seen = {}
        for g in DATA["groups"]:
            for n in g["names"]:
                f = ar.fold(n["name"])
                self.assertNotIn(f, seen, "%r in %s and %s" % (n["name"], seen.get(f), g["id"]))
                seen[f] = g["id"]

    def test_dataset_rejects_name_in_two_groups(self):
        def mk(i):
            return Group.from_dict({"id": i, "canonical": "X " + i, "names": [
                {"name": "Shared Name", "sources": [{"publisher": "p", "url": "https://example.org/" + i}]}]})
        with self.assertRaises(NameConflictError):
            Dataset([mk("a"), mk("b")])

    def test_no_competitor_strings(self):
        raw = resources.files("actor_rosetta").joinpath("data/actors.json").read_text(encoding="utf-8")
        self.assertIsNone(re.search("|".join(("soc" + "radar", "prod" + "aft", "threat" + "mon")), raw, re.I))

    def test_no_lead_list_urls(self):
        for g in DATA["groups"]:
            urls = [s["url"] for k in ("names", "related", "not_aliases") for r in g[k] for s in r["sources"]]
            urls += [s["url"] for d in g["disputes"] for s in d["sources"]]
            for u in urls:
                host = urlparse(u).netloc.lower()
                self.assertFalse(any(host == h or host.endswith("." + h) for h in LEAD_HOSTS), u)
                self.assertNotIn("eternalliberty", u.lower())
                self.assertNotIn("misp-galaxy", u.lower())

    def test_every_name_has_a_source_and_no_quotes(self):
        for g in DATA["groups"]:
            self.assertTrue(g["names"], g["id"])
            for n in g["names"]:
                self.assertTrue(n["sources"], n["name"])
                for s in n["sources"]:
                    self.assertEqual(set(s), {"publisher", "url"})
                    self.assertRegex(s["url"], r"^https?://")
            for k in ("related", "not_aliases"):
                for r in g[k]:
                    self.assertTrue(r["sources"], r["name"])

    def test_profile_urls_are_brandefense_knowledge_hub(self):
        for g in DATA["groups"]:
            if g["profile"]:
                self.assertTrue(g["profile"].startswith("https://brandefense.io/knowledge-hub/"))

    def test_canonical_is_a_published_name(self):
        for g in DATA["groups"]:
            self.assertIn(ar.fold(g["canonical"]), {ar.fold(n["name"]) for n in g["names"]}, g["id"])

    def test_meta_counts_match(self):
        c = DATA["meta"]["counts"]
        gs = DATA["groups"]
        self.assertEqual(c["groups"], len(gs))
        self.assertEqual(c["names"], sum(len(g["names"]) for g in gs))
        self.assertEqual(c["related"], sum(len(g["related"]) for g in gs))
        self.assertEqual(c["not_aliases"], sum(len(g["not_aliases"]) for g in gs))
        self.assertEqual(c["disputes"], sum(len(g["disputes"]) for g in gs))
        self.assertEqual(DATA["meta"]["licence"], "CC BY 4.0")
        self.assertEqual(DATA["meta"]["attribution"], "Brandefense Research Team")

    def test_misp_tag_form(self):
        tagged = [g for g in ar.all_groups() if g.misp_tag]
        self.assertTrue(tagged)
        for g in tagged:
            self.assertRegex(g.misp_tag, r'^misp-galaxy:[a-z0-9-]+=".+"$')

    def test_group_to_dict_roundtrip(self):
        g = ar.resolve("APT29")
        d = g.to_dict()
        self.assertEqual(Group.from_dict(d).to_dict(), d)
        json.dumps(d)


if __name__ == "__main__":
    unittest.main()
