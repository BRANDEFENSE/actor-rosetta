"""Regression list: names analysts type first. Each line is one group; every name on it must resolve to that group.

A data update that breaks a line is wrong until shown otherwise: either the build lost a name or a primary source
changed, and then the line changes with a note in CHANGELOG.md.
"""
import unittest

import actor_rosetta as ar

SAME_GROUP = [
    ("APT28", "Fancy Bear", "Forest Blizzard", "Strontium", "Sofacy", "Sednit"),
    ("APT29", "Midnight Blizzard", "Cozy Bear", "Nobelium"),
    ("Sandworm Team", "Sandworm", "Seashell Blizzard", "APT44"),
    ("Turla", "Secret Blizzard", "Snake"),
    ("Gamaredon Group", "Aqua Blizzard"),
    ("Star Blizzard", "Callisto", "COLDRIVER"),
    ("Ember Bear", "Cadet Blizzard"),
    ("Lazarus Group", "Diamond Sleet"),
    ("APT38", "BlueNoroff"),
    ("Andariel", "Onyx Sleet"),
    ("Kimsuky", "Emerald Sleet", "Velvet Chollima"),
    ("APT37", "ScarCruft"),
    ("Moonstone Sleet", "Storm-1789"),
    ("APT41", "Brass Typhoon"),
    ("APT40", "Gingham Typhoon"),
    ("APT31", "Violet Typhoon", "ZIRCONIUM", "JUDGMENT PANDA"),
    ("APT27", "Emissary Panda"),
    ("HAFNIUM", "Silk Typhoon"),
    ("Volt Typhoon", "Vanguard Panda"),
    ("Salt Typhoon",),
    ("Mustang Panda", "Twill Typhoon"),
    ("APT10", "Stone Panda"),
    ("APT3", "Gothic Panda"),
    ("APT1", "Comment Crew"),
    ("APT5", "Keyhole Panda"),
    ("BlackTech", "Circuit Panda"),
    ("Earth Lusca", "Charcoal Typhoon"),
    ("Flax Typhoon", "Ethereal Panda"),
    ("Naikon", "Override Panda"),
    ("Tick", "Bronze Butler"),
    ("APT32", "OceanLotus", "Canvas Cyclone"),
    ("Darkhotel", "Dubnium"),
    ("APT33", "Peach Sandstorm"),
    ("APT34", "OilRig"),
    ("Magic Hound", "APT35", "Charming Kitten", "Mint Sandstorm", "Phosphorus"),
    ("MuddyWater", "Mango Sandstorm"),
    ("APT39", "Chafer"),
    ("Agrius", "Pink Sandstorm"),
    ("Transparent Tribe", "APT36", "Mythic Leopard"),
    ("SideCopy",),
    ("Patchwork", "Dropping Elephant"),
    ("Sidewinder", "Rattlesnake"),
    ("Machete", "El Machete"),
    ("Blind Eagle", "APT-C-36"),
    ("Equation", "Equation Group"),
    ("FIN7", "Carbon Spider", "Sangria Tempest"),
    ("FIN8", "Syssphinx"),
    ("Wizard Spider", "Periwinkle Tempest", "Conti"),
    ("Scattered Spider", "Octo Tempest", "UNC3944"),
    ("LAPSUS$", "Strawberry Tempest"),
    ("TA505",),
    ("Indrik Spider", "Evil Corp", "Manatee Tempest", "DEV-0243"),
    ("Lace Tempest",),
    ("Silence", "Whisper Spider"),
    ("Cobalt Group", "Cobalt Spider"),
    ("LockBit", "Bitwise Spider"),
    ("ALPHV", "BlackCat"),
    ("Akira", "Storm-1567"),
    ("Play", "Balloonfly"),
    ("CyberAv3ngers",),
    ("Windshift",),
    ("UNC1151", "Umbral Bison", "Moonscape", "TA445", "UAC-0051"),
    ("APT-C-35", "Viceroy Tiger", "Donot"),
    ("APT21", "Hammer Panda"),
    ("APT14", "Anchor Panda"),
    ("APT9", "Nightshade Panda"),
    ("UNC5174", "Uteus", "Bronze Snowdrop"),
    ("Evil Eye", "Earth Empusa", "Poison Carp", "Sentinel Taurus"),
    ("Calypso", "Bronze Medley"),
    ("Wild Neutron", "Morpho"),
    ("LightBasin", "UNC1945"),
    ("Mummy Spider", "TA542", "Gold Crestwood"),
    ("Sprite Spider", "Gold Dupont"),
    ("Doppel Spider", "Gold Heron"),
    ("Boss Spider", "Gold Lowell", "SamSam"),
    ("Karakurt", "Gold Tomahawk", "Mushy Scorpius"),
    ("Hunters International", "Gold Crescent", "Shifty Scorpius", "World Leaks"),
    ("Renaissance Spider", "UAC-0050", "Fire Cells Group"),
    ("Killnet",),
    ("NoName057(16)", "Bounty Jackal"),
    ("Cyber Army of Russia Reborn",),
    ("Vice Society", "Vice Spider", "Vanilla Tempest"),
    # ransomware brands with one operator resolve to it (CHANGELOG, brand rule)
    ("GOLD WATERFALL", "DarkSide", "BlackMatter"),
    ("GOLD SOUTHFIELD", "REvil", "Sodinokibi", "Pinchy Spider"),
]

NOT_A_GROUP = ["Clop", "Black Basta"]  # ransomware deployed by more than one group: explain() says so, resolve() returns None


class KnownNames(unittest.TestCase):
    def test_each_line_is_one_group(self):
        for line in SAME_GROUP:
            with self.subTest(line=line[0]):
                ids = {}
                for name in line:
                    g = ar.resolve(name)
                    self.assertIsNotNone(g, "%r does not resolve" % name)
                    ids[name] = g.id
                self.assertEqual(len(set(ids.values())), 1, ids)

    def test_lines_are_different_groups(self):
        ids = [ar.resolve(line[0]).id for line in SAME_GROUP]
        self.assertEqual(len(ids), len(set(ids)))

    def test_not_a_group(self):
        for name in NOT_A_GROUP:
            self.assertIsNone(ar.resolve(name))
            self.assertIn(name.casefold(), ar.explain(name).text.casefold())


if __name__ == "__main__":
    unittest.main()
