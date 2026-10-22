import unittest
import unittest.mock

import relations
import relations.unittest

import relations_rest
import relations_unifist

import relations_unum


class TestModule(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.unifist = relations.unittest.MockSource("unifist")

    def test_module(self):

        self.assertIn("Relations Unum", relations_unum.__doc__)

    def test_clashed(self):

        # The clashes a record has, any version and writer, in the clash's id, version:identifier:resource:owner:writer

        self.assertEqual(relations_unum.clashed("1:item.unum:home"), [])

        relations_unum.Clash(id="2:1:item.unum:home:away", what={"error": "version"}).create()
        relations_unum.Clash(id="3:1:item.unum:home:cloud", what={"error": "version"}).create()
        relations_unum.Clash(id="2:11:item.unum:home:away", what={"error": "missing"}).create()

        self.assertEqual([clash.id for clash in relations_unum.clashed("1:item.unum:home")], [
            "2:1:item.unum:home:away", "3:1:item.unum:home:cloud"
        ])
        self.assertEqual([clash.id for clash in relations_unum.clashed("11:item.unum:home")], ["2:11:item.unum:home:away"])
        self.assertEqual(relations_unum.clashed("2:item.unum:home"), [])
        self.assertEqual(relations_unum.clashed("1:item.unum:away"), [])

    def test_journal(self):

        # Another unum's journal, the same as the one here but in the source that unum's records are in

        source = relations_unum.Source("unum", unum="home", local="local", members={"away": "away"})
        journal = relations_unum.journal(source, "away")

        self.assertEqual(journal.SOURCE, "away")
        self.assertEqual(journal.thy().NAME, "journal")
        self.assertEqual(
            {key: value for key, value in journal.thy().define().items() if key != "source"},
            {key: value for key, value in relations_unifist.Journal.thy().define().items() if key != "source"}
        )
        self.assertEqual(relations_unifist.Journal.SOURCE, "unifist")

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
    unum = str
    name = str


class Owned(Base):

    id = str
    version = int, 1
    unum = str
    name = str


class Mine(Base):

    id = str
    version = int, 1
    unum = str
    name = str


class Team(Base):

    id = str
    version = int, 1
    unum = str
    name = str


class Copied(Base):

    id = str
    version = int, 1
    unum = str
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

        self.assertEqual(Item.many(name="a").retrieve().export(), [{"id": item.id, "version": 1, "unum": "home", "name": "a"}])

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

        # A record that clashed isn't to be used, until it's sorted out, or it's said to be used anyway

        relations_unum.Clash(id=f"2:{item.id}:away", what={"error": "version"}).create()

        item.name = "e"

        with self.assertRaisesRegex(relations_unum.ClashError, "item: clashed"):
            item.update()

        self.assertEqual(self.local.data["item"][item.id]["name"], "d")

        again = Item.one(item.id).retrieve()
        again.name = "f"
        again.update(force=True)

        self.assertEqual(self.local.data["item"][item.id]["name"], "f")

        # By a query too, for the ones that clashed, and not for the others

        other = Item(name="g").create()

        self.assertEqual(Item.many(name__in=["g", "f"]).set(name="h").update(force=True), 2)

        relations_unum.Clash(id=f"2:{other.id}:away", what={"error": "version"}).create()

        with self.assertRaisesRegex(relations_unum.ClashError, "item: clashed"):
            Item.many(name="h").set(name="i").update()

        # Not while syncing, where clashes are what's recorded

        with self.source.syncing():
            self.assertEqual(Item.many(name="h").set(name="j").update(), 2)

    def test_delete(self):

        # Goes where the record is written to

        owned = Owned(name="a").create()

        owned.delete()

        self.assertEqual(self.ids(self.away, "owned"), [])

        item = Item(name="b").create()

        item.delete()

        self.assertEqual(self.ids(self.local, "item"), [])

        # A record that clashed isn't to be used, until it's sorted out, or it's said to be used anyway

        clashed = Item(name="c").create()
        relations_unum.Clash(id=f"2:{clashed.id}:away", what={"error": "version"}).create()

        with self.assertRaisesRegex(relations_unum.ClashError, "item: clashed"):
            Item.one(clashed.id).delete()

        with self.assertRaisesRegex(relations_unum.ClashError, "item: clashed"):
            Item.many(name="c").delete()

        self.assertEqual(self.ids(self.local, "item"), [clashed.id])

        self.assertEqual(Item.one(clashed.id).delete(force=True), 1)
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

    def fill(self):

        # local has a, d, g, j, m and p, away b, e, h, k, n and q, cloud c, f, i, l, o and r, so sorted by name
        # they interleave, and away also has a copy of local's first

        Item()

        self.rows = {}

        for number, (source, unum) in enumerate([(self.local, "home"), (self.away, "away"), (self.cloud, "cloud")]):
            for position in range(6):
                id = f"{position + 1}:item.unum:{unum}"
                name = "abcdefghijklmnopqr"[position * 3 + number]
                source.data["item"][id] = {"id": id, "version": 1, "unum": unum, "name": name}
                self.rows[name] = id

        self.away.data["item"]["1:item.unum:home"] = {"id": "1:item.unum:home", "version": 1, "unum": "home", "name": "a"}

    def served(self):

        served = []

        for source in [self.local, self.away, self.cloud]:
            retrieve = source.retrieve

            def counting(model, *args, retrieve=retrieve, **kwargs):
                result = retrieve(model, *args, **kwargs)
                served.append(len(model._models))
                return result

            source.retrieve = counting

        return served

    def test_stream(self):

        self.fill()
        self.source.chunk = 2

        # One member's rows in order, a page at a time and only as they're asked for

        served = self.served()
        stream = self.source.stream("away", Item.many().sort("name"), ["+name"])

        self.assertEqual([next(stream).name for _ in range(3)], ["a", "b", "e"])
        self.assertEqual(served, [2, 2])

        # To the end, where a short page says it's over

        self.assertEqual([row.name for row in stream], ["h", "k", "n", "q"])
        self.assertEqual(served, [2, 2, 2, 1])

        # With what the query filters by, and in the order it says

        self.assertEqual([row.name for row in self.source.stream("away", Item.many(name__in=["b", "k", "q"]).sort("-name"), ["-name"])], ["q", "k", "b"])

    def test_select(self):

        self.fill()
        self.source.chunk = 2

        def names(query):
            return [row.name for row in query.retrieve()]

        # Every member's rows in the order of the query, as if it was one, a record that's in more than one only once

        self.assertEqual(names(Item.many().sort("name")), list("abcdefghijklmnopqr"))
        self.assertEqual(names(Item.many().sort("-name")), list("rqponmlkjihgfedcba"))
        self.assertEqual(names(Item.many()), [name for _, name in sorted((id, name) for name, id in self.rows.items())])

        # With filters and limits

        self.assertEqual(names(Item.many(name__in=["r", "a", "h", "x"]).sort("name")), ["a", "h", "r"])
        self.assertEqual(names(Item.many().sort("name").limit(3)), ["a", "b", "c"])
        self.assertEqual(names(Item.many().sort("name").limit(4, start=5)), ["f", "g", "h", "i"])
        self.assertEqual(names(Item.many().sort("name").limit(page=2, per_page=5)), ["f", "g", "h", "i", "j"])

        # Reading only what's needed, not everything to sort it

        served = self.served()

        self.assertEqual(names(Item.many().sort("name").limit(3)), ["a", "b", "c"])
        self.assertTrue(6 <= sum(served) <= 10)

        # A source that can't be reached just has no rows

        self.down(self.cloud, "retrieve")

        self.assertEqual(names(Item.many().sort("name")), list("abdeghjkmnpq"))

        # Whatever's picked from is still a model of those records

        found = Item.many().sort("name").limit(2).retrieve()

        self.assertEqual(found.export(), [
            {"id": self.rows["a"], "version": 1, "unum": "home", "name": "a"},
            {"id": self.rows["b"], "version": 1, "unum": "away", "name": "b"}
        ])

        found[0].name = "z"
        found[0].update()

        self.assertEqual(self.local.data["item"][self.rows["a"]]["name"], "z")

    def test_universe(self):

        # This unum's source first, then each other's, this unum being a member too changing nothing

        self.assertEqual(self.source.universe(), {"home": "local", "away": "away", "cloud": "cloud"})

        self.source.members["home"] = "elsewhere"

        self.assertEqual(self.source.universe(), {"home": "local", "away": "away", "cloud": "cloud"})

    def test_named(self):

        # No unum criterion names none, which is all of them

        self.assertIsNone(self.source.named(Item.many()))
        self.assertIsNone(self.source.named(Item.many(name="a")))
        self.assertIsNone(self.source.named(Item.many(unum__not_in=["away"])))

        # One or more are named by eq or in

        self.assertEqual(self.source.named(Item.many(unum="away")), {"away"})
        self.assertEqual(self.source.named(Item.many(unum__in=["away", "cloud"])), {"away", "cloud"})

        # Both having to be satisfied, only what's in each is named

        self.assertEqual(self.source.named(Item.many(unum="away", unum__in=["away", "cloud"])), {"away"})
        self.assertEqual(self.source.named(Item.many(unum="home", unum__in=["away", "cloud"])), set())

    def test_scopes(self):

        # Each unum there is, this one's first, when none are named

        self.assertEqual(self.source.scopes(Item.many()), [("home", "local"), ("away", "away"), ("cloud", "cloud")])

        # Only the ones named, in the order of the unums there are, not the order named

        self.assertEqual(self.source.scopes(Item.many(unum="away")), [("away", "away")])
        self.assertEqual(self.source.scopes(Item.many(unum__in=["cloud", "home"])), [("home", "local"), ("cloud", "cloud")])

        # A unum there isn't is never asked, so a query naming only those is for none

        self.assertEqual(self.source.scopes(Item.many(unum__in=["away", "nowhere"])), [("away", "away")])
        self.assertEqual(self.source.scopes(Item.many(unum="nowhere")), [])
        self.assertEqual(self.source.scopes(Item.many(unum="home", unum__in=["away"])), [])

    def test_scoped(self):

        # A copy for one unum, with the query's other criteria and like kept, and whatever it named replaced

        query = Item.many(name__in=["a", "b"], unum__in=["away", "cloud"], unum="away", like="a")
        page = self.source.scoped(query, "cloud")

        self.assertEqual(page._record._names["unum"].criteria, {"eq": "cloud"})
        self.assertEqual(page._record._names["name"].criteria, {"in": ["a", "b"]})
        self.assertEqual(page._like, query._like)

        # The query isn't changed, nor does it share anything with the copy

        self.assertEqual(query._record._names["unum"].criteria, {"in": ["away", "cloud"], "eq": "away"})

        # Naming none is still scoped

        self.assertEqual(self.source.scoped(Item.many(), "away")._record._names["unum"].criteria, {"eq": "away"})

        # And the criteria that aren't for naming are kept

        self.assertEqual(
            self.source.scoped(Item.many(unum__not_in=["away"]), "cloud")._record._names["unum"].criteria,
            {"not_in": ["away"], "eq": "cloud"}
        )

    def test_scoped_select(self):

        self.fill()
        self.source.chunk = 2

        def names(query):
            return [row.name for row in query.retrieve()]

        # A query for a unum is only that unum's rows, so away's copy of home's first isn't there, and others aren't asked

        self.assertEqual(names(Item.many(unum="away").sort("name")), list("behknq"))
        self.assertEqual(names(Item.many(unum="home").sort("name")), list("adgjmp"))

        asked = []

        for source in [self.local, self.away, self.cloud]:
            retrieve = source.retrieve

            def recording(model, *args, retrieve=retrieve, name=source.name, **kwargs):
                asked.append((name, model._record._names["unum"].criteria))
                return retrieve(model, *args, **kwargs)

            source.retrieve = recording

        names(Item.many(unum="away").sort("name"))

        self.assertEqual({name for name, _ in asked}, {"away"})
        self.assertEqual({str(criteria) for _, criteria in asked}, {"{'eq': 'away'}"})

        # Or the ones it names, each asked for its own

        asked.clear()

        self.assertEqual(names(Item.many(unum__in=["away", "cloud"]).sort("name")), list("bcefhiklnoqr"))
        self.assertEqual(sorted({(name, str(criteria)) for name, criteria in asked}), [
            ("away", "{'eq': 'away'}"), ("cloud", "{'eq': 'cloud'}")
        ])

        # With nothing named it's all of them, each asked for its own, the copy only once, as the home's

        asked.clear()

        self.assertEqual(names(Item.many().sort("name")), list("abcdefghijklmnopqr"))
        self.assertEqual(sorted({(name, str(criteria)) for name, criteria in asked}), [
            ("away", "{'eq': 'away'}"), ("cloud", "{'eq': 'cloud'}"), ("local", "{'eq': 'home'}")
        ])

        # A unum there isn't is never asked, and a query naming only those has no rows

        asked.clear()

        self.assertEqual(names(Item.many(unum__in=["away", "nowhere"]).sort("name")), list("behknq"))
        self.assertEqual(names(Item.many(unum="nowhere")), [])
        self.assertEqual({name for name, _ in asked}, {"away"})

        # Rows that sort the same, from every unum, are all there

        self.assertEqual(len(names(Item.many().sort("version"))), 18)

        # What else it filters by is still done, and limits are of the whole

        self.assertEqual(names(Item.many(unum__in=["away", "cloud"], name__in=["b", "c", "q"]).sort("name")), ["b", "c", "q"])
        self.assertEqual(names(Item.many(unum__in=["away", "cloud"]).sort("name").limit(3, start=2)), ["e", "f", "h"])

        # A member's own API runs its own unum source, which a query for just it never gets past

        self.down(self.away, "retrieve")

        self.assertEqual(names(Item.many(unum="away")), [])

    def test_count(self):

        self.fill()

        # Each unum's own rows added up, away's copy of home's first not counted twice

        self.assertEqual(Item.many().count(), 18)
        self.assertEqual(Item.many(name__in=["a", "b", "c"]).count(), 3)

        # Only the ones it names, each asked for its own

        self.assertEqual(Item.many(unum="away").count(), 6)
        self.assertEqual(Item.many(unum="home").count(), 6)
        self.assertEqual(Item.many(unum__in=["away", "cloud"]).count(), 12)
        self.assertEqual(Item.many(unum__in=["away", "cloud"], name__in=["b", "c", "a"]).count(), 2)

        # Never one there isn't

        self.assertEqual(Item.many(unum="nowhere").count(), 0)
        self.assertEqual(Item.many(unum__in=["away", "nowhere"]).count(), 6)

        # A source that can't be reached has none

        self.down(self.cloud, "count")

        self.assertEqual(Item.many().count(), 12)

        # And what's synced is counted here alone, as it's here alone it's written and read

        with self.source.syncing():
            self.assertEqual(Item.many().count(), 6)


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


class TestSync(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.unifist = relations.unittest.MockSource("unifist")
        self.local = relations.unittest.MockSource("local")
        self.away = relations.unittest.MockSource("away")

        self.source = relations_unum.Source("unum", unum="home", local="local", members={"away": "away"})
        self.models = relations_unum.models(Item)
        self.journal = relations_unum.journal(self.source, "away")

        relations_unifist.UnifistModel.UNUM = "home"

    def tearDown(self):

        relations_unifist.UnifistModel.UNUM = None

    def write(self, transaction, when, action, **what):

        self.journal(id=transaction, resource_id=what["id"], when=when, what={"action": action, "app": "unum", "block": "item", **what}).create()

    def test_sync(self):

        five = "5:item.unum:away"
        six = "6:item.unum:away"

        # What away has written, put in out of order, to be applied by when. Record 5 is made, changed and deleted, record 6
        # is made, and then changed by someone else from a version it isn't at

        self.write("3:5:item.unum:away:away", 30, "delete", id=five, before={"id": five, "version": 2, "name": "b"})
        self.write("2:6:item.unum:away:cloud", 25, "update", id=six,
            before={"id": six, "version": 5, "name": "c"}, after={"id": six, "version": 6, "name": "d"})
        self.write("2:5:item.unum:away:away", 20, "update", id=five,
            before={"id": five, "version": 1, "name": "a"}, after={"id": five, "version": 2, "name": "b"})
        self.write("1:6:item.unum:away:away", 15, "create", id=six, after={"id": six, "version": 1, "name": "c"})
        self.write("1:5:item.unum:away:away", 10, "create", id=five, after={"id": five, "version": 1, "name": "a"})

        # They're applied in order, to the copies here, and the journal here has the same rows

        self.assertEqual(relations_unum.sync(self.source, "away", self.models), {"applied": 4, "skipped": 0, "clash": 1})

        self.assertEqual(list(self.local.data["item"]), [six])
        self.assertEqual(self.local.data["item"][six]["name"], "c")
        self.assertEqual(self.away.data["item"], {})
        self.assertEqual(list(self.unifist.data["journal"]), [
            "1:5:item.unum:away:away", "1:6:item.unum:away:away", "2:5:item.unum:away:away", "3:5:item.unum:away:away"
        ])
        self.assertEqual({id: row["what"] for id, row in self.unifist.data["clash"].items()}, {"2:6:item.unum:away:cloud": {"error": "version"}})

        # Again, it's all done already

        self.assertEqual(relations_unum.sync(self.source, "away", self.models), {"applied": 0, "skipped": 4, "clash": 1})
        self.assertEqual(len(self.unifist.data["journal"]), 4)
        self.assertEqual(len(self.unifist.data["clash"]), 1)

        # New rows since are applied, and the rest aren't

        self.write("2:6:item.unum:away:away", 40, "update", id=six,
            before={"id": six, "version": 1, "name": "c"}, after={"id": six, "version": 2, "name": "e"})

        self.assertEqual(relations_unum.sync(self.source, "away", self.models), {"applied": 1, "skipped": 4, "clash": 1})
        self.assertEqual(self.local.data["item"][six]["name"], "e")

        # If away can't be reached it's raised, for the next time, and nothing is done

        def failing(model, *args, **kwargs):
            raise relations.SourceError("away is down")

        self.away.retrieve = failing

        with self.assertRaisesRegex(relations.SourceError, "away is down"):
            relations_unum.sync(self.source, "away", self.models)

        self.assertEqual(self.local.data["item"][six]["name"], "e")


class Answer:
    """
    What a session answers, a status and a body
    """

    def __init__(self, body, status_code=200):

        self.body = body
        self.status_code = status_code

    def json(self):
        """
        The body
        """

        return self.body


class Session:
    """
    A session that records each request and answers from a table of "METHOD url"
    """

    def __init__(self, answers):

        self.answers = answers
        self.calls = []

    def request(self, method, url, **kwargs):
        """
        Records the request and answers it, or fails if it wasn't expected
        """

        self.calls.append((method, url, kwargs.get("json")))
        return Answer(self.answers[f"{method} {url}"])

    def get(self, url, **kwargs):
        """
        GET
        """
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        """
        POST
        """
        return self.request("POST", url, **kwargs)

    def patch(self, url, **kwargs):
        """
        PATCH
        """
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        """
        DELETE
        """
        return self.request("DELETE", url, **kwargs)


class Unit(relations.Model):
    SOURCE = "api"
    id = int
    name = str


class Tested(relations.Model):
    SOURCE = "api"
    ENDPOINT = "tests"
    id = int
    name = str


@unittest.mock.patch("relations.SOURCES", {})
class TestRestSource(unittest.TestCase):

    maxDiff = None

    def test___init__(self):

        source = relations_unum.RestSource("api", "http://test.com", session="sesh")

        self.assertIsInstance(source, relations_rest.Source)
        self.assertEqual(source.name, "api")
        self.assertEqual(source.url, "http://test.com/model")
        self.assertEqual(source.session, "sesh")
        self.assertIs(relations.SOURCES["api"], source)

        # A slash at the end of the url isn't doubled

        self.assertEqual(relations_unum.RestSource("slashed", "http://test.com/", session="sesh").url, "http://test.com/model")

        # Without a session it makes one, with what's left as its attributes, and the url is still only /model

        source = relations_unum.RestSource("made", "http://test.com/app", verify=False)

        self.assertEqual(source.url, "http://test.com/app/model")
        self.assertFalse(source.session.verify)

    def test_models(self):

        # Create, retrieve, update and delete go to /model/{singular}, with the id for an update

        session = Session({
            "POST http://test.com/model/unit": {"units": [{"id": 1}]},
            "GET http://test.com/model/unit": {"units": [{"id": 1, "name": "a"}]},
            "PATCH http://test.com/model/unit/1": {"updated": 1},
            "DELETE http://test.com/model/unit": {"deleted": 1}
        })

        relations_unum.RestSource("api", "http://test.com", session=session)

        unit = Unit("a").create()

        self.assertEqual(unit.id, 1)

        unit = Unit.one(1)

        self.assertEqual(unit.name, "a")

        unit.name = "b"

        self.assertEqual(unit.update(), 1)
        self.assertEqual(Unit.one(1).delete(), 1)

        self.assertEqual([call[:2] for call in session.calls], [
            ("POST", "http://test.com/model/unit"),
            ("GET", "http://test.com/model/unit"),
            ("PATCH", "http://test.com/model/unit/1"),
            ("GET", "http://test.com/model/unit"),
            ("DELETE", "http://test.com/model/unit")
        ])

    def test_endpoint(self):

        # A model's ENDPOINT is relative to /model

        session = Session({
            "POST http://test.com/model/tests": {"testeds": [{"id": 2}]},
            "GET http://test.com/model/tests": {"testeds": [{"id": 2, "name": "a"}]},
            "PATCH http://test.com/model/tests/2": {"updated": 1}
        })

        relations_unum.RestSource("api", "http://test.com", session=session)

        tested = Tested("a").create()

        self.assertEqual(tested.id, 2)

        tested.name = "b"
        tested.update()

        self.assertEqual(Tested.many(name="a").name, ["a"])

        self.assertEqual([call[:2] for call in session.calls], [
            ("POST", "http://test.com/model/tests"),
            ("PATCH", "http://test.com/model/tests/2"),
            ("GET", "http://test.com/model/tests")
        ])
