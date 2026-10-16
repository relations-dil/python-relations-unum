import unittest

import relations
import relations.unittest

import relations_unifist

import relations_unum


class TestModule(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.unifist = relations.unittest.MockSource("unifist")

    def test_module(self):

        self.assertIn("Relations Unum", relations_unum.__doc__)

    def test_models(self):

        # The models sync can apply, by the app (source) and block (model) a journal row has

        self.assertEqual(relations_unum.models(Item, Owned), {("unum", "item"): Item, ("unum", "owned"): Owned})
        self.assertEqual(relations_unum.models(), {})

    def test_route(self):

        # Nothing is nothing

        self.assertEqual(relations_unum.route("42:item.local:home"), [])

        # Whoever has a record's data in whatever role, from rows that match it. Blank matches anything, and for each role
        # the rows that match the most win, so a model's or a record's own say beats its unum's

        relations_unum.Route(unum="home", role="owner", holder="away", url="https://away").create()
        relations_unum.Route(unum="home", model="item", role="writer", holder="home").create()
        relations_unum.Route(unum="home", model="item", identifier="42", role="reader", holder="cloud", url="https://cloud").create()
        relations_unum.Route(unum="home", model="item", role="reader", holder="attic").create()

        def holders(record_id):
            return [(route.role, route.holder) for route in relations_unum.route(record_id)]

        self.assertEqual(holders("42:item.local:home"), [("owner", "away"), ("writer", "home"), ("reader", "cloud")])
        self.assertEqual(holders("7:item.local:home"), [("owner", "away"), ("writer", "home"), ("reader", "attic")])
        self.assertEqual(holders("7:thing.local:home"), [("owner", "away")])
        self.assertEqual(holders("7:item.local:cloud"), [])

        # And where to reach them

        self.assertEqual(relations_unum.route("42:item.local:home")[2].url, "https://cloud")
        self.assertEqual(relations_unum.route("42:item.local:home")[1].url, "")

    def test_scribe(self):

        # Nothing is nothing

        self.assertIsNone(relations_unum.scribe("42:item.local:home"))

        # Where a write goes, from the one row that matches the most, blank matching anything

        relations_unum.Scribe(to="local").create()
        relations_unum.Scribe(unum="home", to="owner").create()
        relations_unum.Scribe(unum="home", model="item", to="writer").create()
        relations_unum.Scribe(unum="home", model="item", identifier="42", to="local").create()

        self.assertEqual(relations_unum.scribe("42:item.local:home").to, "local")
        self.assertEqual(relations_unum.scribe("7:item.local:home").to, "writer")
        self.assertEqual(relations_unum.scribe("7:thing.local:home").to, "owner")
        self.assertEqual(relations_unum.scribe("7:item.local:cloud").to, "local")

        # Rows that match as much as each other, the first made wins

        relations_unum.Scribe(unum="home", source="local", to="owner").create()
        relations_unum.Scribe(unum="home", source="local", model="thing", to="local").create()

        self.assertEqual(relations_unum.scribe("7:item.local:home").to, "writer")
        self.assertEqual(relations_unum.scribe("7:other.local:home").to, "owner")
        self.assertEqual(relations_unum.scribe("7:thing.local:home").to, "local")
        self.assertEqual(relations_unum.scribe("7:other.remote:home").to, "owner")


class TestClash(unittest.TestCase):

    maxDiff = None

    def test_define(self):

        definition = relations_unum.Clash.thy().define()
        fields = {field["name"]: field for field in definition["fields"]}

        # In the Unifist source with the journal, and with the same id as the journal row it's about,
        # version:identifier:resource:owner:writer, so the two go together without another field

        self.assertTrue(issubclass(relations_unum.Clash, relations_unifist.UnifistBase))
        self.assertEqual(relations_unum.Clash.SOURCE, relations_unifist.UnifistBase.SOURCE)
        self.assertEqual(definition["name"], "clash")
        self.assertEqual(definition["id"], "id")
        self.assertEqual([field["name"] for field in definition["fields"]], ["id", "what"])
        self.assertEqual([field["kind"] for field in definition["fields"]], ["str", "dict"])
        self.assertEqual(definition["unique"], {})
        self.assertFalse(fields["what"]["none"])

        # Made with the id of the journal row, and what's wrong with it

        clash = relations_unum.Clash(id="2:42:item.local:away:away", what={"error": "version"})

        self.assertEqual(clash.id, "2:42:item.local:away:away")
        self.assertEqual(clash.what, {"error": "version"})


class TestRoute(unittest.TestCase):

    maxDiff = None

    def test_define(self):

        definition = relations_unum.Route.thy().define()
        fields = {field["name"]: field for field in definition["fields"]}

        # Who has the data, in what role and where, matched on the parts of a record's id, in the id's order, blank being anything

        self.assertTrue(issubclass(relations_unum.Route, relations_unifist.UnifistBase))
        self.assertEqual(definition["name"], "route")
        self.assertEqual(definition["id"], "id")
        self.assertEqual([field["name"] for field in definition["fields"]], [
            "id", "identifier", "model", "source", "unum", "role", "holder", "url"
        ])

        for name in ["identifier", "model", "source", "unum", "url"]:
            self.assertEqual(fields[name]["kind"], "str")
            self.assertEqual(fields[name]["default"], "")
            self.assertFalse(fields[name]["none"])

        self.assertEqual(fields["role"]["options"], ["owner", "writer", "reader"])
        self.assertFalse(fields["holder"]["none"])
        self.assertEqual(definition["unique"], {"identifier-model-source-unum-role-holder": [
            "identifier", "model", "source", "unum", "role", "holder"
        ]})

    def test_pattern(self):

        # Shown like a record's id, with a * for anything, though a blank is what's kept

        self.assertEqual(relations_unum.Route(unum="home", role="owner", holder="away").pattern(), "*:*.*:home")
        self.assertEqual(relations_unum.Route(unum="home", model="item", identifier="42", role="reader", holder="a").pattern(), "42:item.*:home")
        self.assertEqual(relations_unum.Route(role="owner", holder="away").pattern(), "*:*.*:*")
        self.assertEqual(relations_unum.Route(unum="home", source="local", model="item", identifier="7", role="owner", holder="a").pattern(), "7:item.local:home")


class TestScribe(unittest.TestCase):

    maxDiff = None

    def test_define(self):

        definition = relations_unum.Scribe.thy().define()
        fields = {field["name"]: field for field in definition["fields"]}

        # Where a write goes, matched the same way, one row for each match

        self.assertTrue(issubclass(relations_unum.Scribe, relations_unifist.UnifistBase))
        self.assertEqual(definition["name"], "scribe")
        self.assertEqual(definition["id"], "id")
        self.assertEqual([field["name"] for field in definition["fields"]], [
            "id", "identifier", "model", "source", "unum", "to"
        ])

        for name in ["identifier", "model", "source", "unum"]:
            self.assertEqual(fields[name]["kind"], "str")
            self.assertEqual(fields[name]["default"], "")
            self.assertFalse(fields[name]["none"])

        self.assertEqual(fields["to"]["options"], ["owner", "writer", "local"])
        self.assertEqual(definition["unique"], {"identifier-model-source-unum": ["identifier", "model", "source", "unum"]})

    def test_pattern(self):

        self.assertEqual(relations_unum.Scribe(unum="home", to="owner").pattern(), "*:*.*:home")
        self.assertEqual(relations_unum.Scribe(unum="home", model="item", identifier="42", to="local").pattern(), "42:item.*:home")
        self.assertEqual(relations_unum.Scribe(to="local").pattern(), "*:*.*:*")


class Base(relations_unifist.UnifistModel):

    SOURCE = "unum"


class Item(Base):

    id = str
    version = int, 1
    name = str


class Owned(Base):

    id = str
    version = int, 1
    name = str


class Mine(Base):

    id = str
    version = int, 1
    name = str


class Team(Base):

    id = str
    version = int, 1
    name = str


class Copied(Base):

    id = str
    version = int, 1
    name = str


class TestSource(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.unifist = relations.unittest.MockSource("unifist")
        self.local = relations.unittest.MockSource("local")
        self.away = relations.unittest.MockSource("away")
        self.cloud = relations.unittest.MockSource("cloud")

        self.source = relations_unum.Source("unum", unum="home", local="local", members={"away": "away", "cloud": "cloud"})

        relations_unifist.UnifistModel.UNUM = "home"

        # Item has no rows, so it's written here. Owned is written to its owner, who's away. Mine is the same
        # but the owner is this unum. Team is written to its writers, away first, then cloud. Copied is owned away
        # but this unum reads it, so a copy here, from sync, is read before the owner's

        relations_unum.Scribe(unum="home", model="owned", to="owner").create()
        relations_unum.Route(unum="home", model="owned", role="owner", holder="away").create()
        relations_unum.Scribe(unum="home", model="mine", to="owner").create()
        relations_unum.Route(unum="home", model="mine", role="owner", holder="home").create()
        relations_unum.Scribe(unum="home", model="team", to="writer").create()
        relations_unum.Route(unum="home", model="team", role="writer", holder="away").create()
        relations_unum.Route(unum="home", model="team", role="writer", holder="cloud").create()
        relations_unum.Scribe(unum="home", model="copied", to="owner").create()
        relations_unum.Route(unum="home", model="copied", role="owner", holder="away").create()
        relations_unum.Route(unum="home", model="copied", role="reader", holder="home").create()

    def tearDown(self):

        relations_unifist.UnifistModel.UNUM = None

    def ids(self, source, name):

        return sorted(source.data[name])

    def down(self, source, action):

        def failing(model, *args, **kwargs):
            raise relations.SourceError(f"{source.name} is down")

        setattr(source, action, failing)

    def test_init(self):

        # Every source it routes to has to know the model

        Item()

        for source in [self.local, self.away, self.cloud]:
            self.assertEqual(source.data["item"], {})

    def test_create(self):

        # With nothing saying otherwise a record is written here

        item = Item(name="a").create()

        self.assertEqual(item.id, "1:item.unum:home")
        self.assertEqual(self.ids(self.local, "item"), ["1:item.unum:home"])
        self.assertEqual(self.ids(self.away, "item"), [])

        # To its owner, who's away

        owned = Owned(name="b").create()

        self.assertEqual(owned.id, "1:owned.unum:home")
        self.assertEqual(self.ids(self.local, "owned"), [])
        self.assertEqual(self.ids(self.away, "owned"), ["1:owned.unum:home"])

        # Or here, when the owner is this unum

        Mine(name="c").create()

        self.assertEqual(self.ids(self.local, "mine"), ["1:mine.unum:home"])

        # To the first of its writers

        Team(name="d").create()

        self.assertEqual(self.ids(self.away, "team"), ["1:team.unum:home"])
        self.assertEqual(self.ids(self.cloud, "team"), [])

        # Or the next, if that one is down

        self.down(self.away, "create")

        Team(name="e").create()

        self.assertEqual(self.ids(self.cloud, "team"), ["2:team.unum:home"])

        # Or nothing, if they all are

        self.down(self.cloud, "create")

        with self.assertRaisesRegex(relations.SourceError, "cloud is down"):
            Team(name="f").create()

    def test_retrieve(self):

        # From here, when that's where it is

        item = Item(name="a").create()

        self.assertEqual(Item.one(item.id).retrieve().name, "a")

        # From its owner, when that's where it is

        owned = Owned(name="b").create()

        self.assertEqual(self.ids(self.local, "owned"), [])
        self.assertEqual(Owned.one(owned.id).retrieve().name, "b")

        # From its writers, the first that has it

        team = Team(name="c").create()

        self.assertEqual(Team.one(team.id).retrieve().name, "c")

        # From here first, when this unum holds a copy though it's not the owner

        copied = Copied(name="e").create()
        self.local.data["copied"][copied.id] = {"id": copied.id, "version": 1, "name": "copy"}

        self.assertEqual(self.away.data["copied"][copied.id]["name"], "e")
        self.assertEqual(Copied.one(copied.id).retrieve().name, "copy")

        # Or the next, when the first doesn't have it, because it was down when it was written, or is down now

        self.down(self.away, "create")

        other = Team(name="d").create()

        self.assertEqual(self.ids(self.cloud, "team"), [other.id])
        self.assertEqual(Team.one(other.id).retrieve().name, "d")

        self.down(self.away, "retrieve")

        self.assertEqual(Team.one(other.id).retrieve().name, "d")

        # A record with no id to go by is looked for here

        self.assertEqual(Item.many(name="a").retrieve().export(), [{"id": item.id, "version": 1, "name": "a"}])

    def test_update(self):

        # Goes where the record is written to

        owned = Owned(name="a").create()

        owned.name = "b"
        owned.update()

        self.assertEqual(self.away.data["owned"][owned.id]["name"], "b")
        self.assertEqual(self.ids(self.local, "owned"), [])

        item = Item(name="c").create()

        item.name = "d"
        item.update()

        self.assertEqual(self.local.data["item"][item.id]["name"], "d")

    def test_delete(self):

        # Goes where the record is written to

        owned = Owned(name="a").create()

        owned.delete()

        self.assertEqual(self.ids(self.away, "owned"), [])

        item = Item(name="b").create()

        item.delete()

        self.assertEqual(self.ids(self.local, "item"), [])

    def test_syncing(self):

        # Writes and reads stay here while syncing, whatever the routes say, because what's synced is a copy

        relations_unum.Scribe(unum="away", model="item", to="owner").create()
        relations_unum.Route(unum="away", model="item", role="owner", holder="away").create()

        with self.source.syncing():
            item = Item(id="5:item.unum:away", name="a").create()

        self.assertEqual(self.ids(self.local, "item"), ["5:item.unum:away"])
        self.assertEqual(self.ids(self.away, "item"), [])

        with self.source.syncing():
            self.assertEqual(Item.one(item.id).retrieve().name, "a")

        # And not after

        Item(id="6:item.unum:away", name="b").create()

        self.assertEqual(self.ids(self.away, "item"), ["6:item.unum:away"])

    def test_count(self):

        # Everything else is still here for now

        Item(name="a").create()
        Item(name="b").create()

        self.assertEqual(Item.many().count(), 2)


class TestApply(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.unifist = relations.unittest.MockSource("unifist")
        self.local = relations.unittest.MockSource("local")
        self.away = relations.unittest.MockSource("away")

        self.source = relations_unum.Source("unum", unum="home", local="local", members={"away": "away"})
        self.models = relations_unum.models(Item)

        relations_unifist.UnifistModel.UNUM = "home"

        # The records away owns are written to away, but sync writes the copies here

        relations_unum.Scribe(unum="away", model="item", to="owner").create()
        relations_unum.Route(unum="away", model="item", role="owner", holder="away").create()

    def tearDown(self):

        relations_unifist.UnifistModel.UNUM = None

    def row(self, id, action, **what):

        return {"id": id, "resource_id": "5:item.unum:away", "what": {
            "action": action, "app": "unum", "block": "item", "id": "5:item.unum:away", **what
        }}

    def journal(self):

        return list(self.unifist.data["journal"])

    def clashes(self):

        return {id: row["what"] for id, row in self.unifist.data["clash"].items()}

    def test_apply(self):

        created = self.row("1:5:item.unum:away:away", "create", after={"id": "5:item.unum:away", "version": 1, "name": "a"})
        updated = self.row("2:5:item.unum:away:away", "update",
            before={"id": "5:item.unum:away", "version": 1, "name": "a"}, after={"id": "5:item.unum:away", "version": 2, "name": "b"})
        deleted = self.row("3:5:item.unum:away:away", "delete", before={"id": "5:item.unum:away", "version": 2, "name": "b"})

        # A create is made here, not to the owner, and its journal row is the one it came with, so the transaction is the same

        self.assertEqual(relations_unum.apply(self.source, created, self.models), "applied")
        self.assertEqual(self.local.data["item"]["5:item.unum:away"]["name"], "a")
        self.assertEqual(self.away.data["item"], {})
        self.assertEqual(self.journal(), ["1:5:item.unum:away:away"])

        # An update too, from the version it was

        self.assertEqual(relations_unum.apply(self.source, updated, self.models), "applied")
        self.assertEqual(self.local.data["item"]["5:item.unum:away"]["name"], "b")
        self.assertEqual(self.local.data["item"]["5:item.unum:away"]["version"], 2)
        self.assertEqual(self.journal(), ["1:5:item.unum:away:away", "2:5:item.unum:away:away"])

        # One that's already here is skipped, whatever it was, so syncing twice does nothing

        self.assertEqual(relations_unum.apply(self.source, created, self.models), "skipped")
        self.assertEqual(relations_unum.apply(self.source, updated, self.models), "skipped")
        self.assertEqual(self.local.data["item"]["5:item.unum:away"]["version"], 2)

        # As is a delete

        self.assertEqual(relations_unum.apply(self.source, deleted, self.models), "applied")
        self.assertEqual(self.local.data["item"], {})
        self.assertEqual(self.journal()[2], "3:5:item.unum:away:away")

        # Nothing broke

        self.assertEqual(self.clashes(), {})

        # An update from a version it isn't at is a clash, and the record is left as it is. So is a delete

        with self.source.syncing():
            Item(id="6:item.unum:away", name="c").create()
            Item.many(id="6:item.unum:away").set(name="d").update()

        stale = self.row("2:6:item.unum:away:cloud", "update",
            before={"id": "6:item.unum:away", "version": 1, "name": "c"}, after={"id": "6:item.unum:away", "version": 2, "name": "e"})
        stale["what"]["id"] = "6:item.unum:away"
        late = self.row("2:6:item.unum:away:cloud", "delete", before={"id": "6:item.unum:away", "version": 1, "name": "c"})

        self.assertEqual(relations_unum.apply(self.source, stale, self.models), "clash")
        self.assertEqual(self.local.data["item"]["6:item.unum:away"]["name"], "d")
        self.assertEqual(self.clashes(), {"2:6:item.unum:away:cloud": {"error": "version"}})

        # Once it's a clash it's left alone, until someone sorts it out

        self.assertEqual(relations_unum.apply(self.source, late, self.models), "clash")
        self.assertEqual(len(self.clashes()), 1)

        # Changing a record that isn't here is one too

        gone = self.row("2:7:item.unum:away:away", "update",
            before={"id": "7:item.unum:away", "version": 1, "name": "f"}, after={"id": "7:item.unum:away", "version": 2, "name": "g"})
        gone["what"]["id"] = "7:item.unum:away"

        self.assertEqual(relations_unum.apply(self.source, gone, self.models), "clash")
        self.assertEqual(self.clashes()["2:7:item.unum:away:away"], {"error": "missing"})

        # And so is making one that is

        with self.source.syncing():
            Item(id="8:item.unum:away", name="h").create()

        twice = self.row("1:8:item.unum:away:cloud", "create", after={"id": "8:item.unum:away", "version": 1, "name": "i"})
        twice["what"]["id"] = "8:item.unum:away"

        self.assertEqual(relations_unum.apply(self.source, twice, self.models), "clash")
        self.assertEqual(self.clashes()["1:8:item.unum:away:cloud"], {"error": "exists"})
        self.assertEqual(self.local.data["item"]["8:item.unum:away"]["name"], "h")

        # Or a model that isn't known

        unknown = self.row("1:9:nope.unum:away:away", "create", after={"id": "9:nope.unum:away", "version": 1})
        unknown["what"]["block"] = "nope"

        self.assertEqual(relations_unum.apply(self.source, unknown, self.models), "clash")
        self.assertEqual(self.clashes()["1:9:nope.unum:away:away"], {"error": "model"})
