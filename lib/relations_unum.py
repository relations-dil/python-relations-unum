"""
Main Relations Unum Module
"""

import contextlib

import relations
import relations_unifist


def blank():
    """
    A string column that is never None, blank meaning any when it's matched
    """

    return relations.Field(str, default="", none=False)


class Clash(relations_unifist.UnifistBase):
    """
    What broke, with the same id as the journal row it's about, version:identifier:resource:owner:writer
    """

    id = str
    what = dict, False


class Matching:
    """
    What Route and Scribe share, matching a record's id on its parts (identifier, model, source and unum), blank
    meaning any
    """

    def specificity(self):
        """
        How many of the parts are set, the more the more it matches
        """

        return sum(1 for part in [self.identifier, self.model, self.source, self.unum] if part)

    def pattern(self):
        """
        Shown like a record's id, with a * for any, though a blank is what's kept
        """

        return f"{self.identifier or '*'}:{self.model or '*'}.{self.source or '*'}:{self.unum or '*'}"


class Route(Matching, relations_unifist.UnifistBase):
    """
    Who has the data that matches, in what role, and where to reach them (a url, blank for here)
    """

    id = int
    identifier = blank()
    model = blank()
    source = blank()
    unum = blank()
    role = ["owner", "writer", "reader"]
    holder = str, False
    url = blank()

    UNIQUE = ["identifier", "model", "source", "unum", "role", "holder"]


class Scribe(Matching, relations_unifist.UnifistBase):
    """
    Where a write goes for the data that matches, one row for each match
    """

    id = int
    identifier = blank()
    model = blank()
    source = blank()
    unum = blank()
    to = ["owner", "writer", "local"]

    UNIQUE = ["identifier", "model", "source", "unum"]


def matching(kind, record_id):
    """
    The rows of a kind (Route or Scribe) that match a record's id, which is identifier:model.source:unum
    """

    identifier, resource, unum = record_id.split(":", 2)
    model, source = resource.split(".", 1)

    return list(kind.many(
        identifier__in=["", identifier], model__in=["", model], source__in=["", source], unum__in=["", unum]
    ).retrieve())


def route(record_id):
    """
    Who has a record's data, in whatever role. For each role the rows that match the most win, so what a
    model or a record says beats what its unum says. Owners, then writers, then readers, each in the order made
    """

    roles = ["owner", "writer", "reader"]
    rows = matching(Route, record_id)
    best = {}

    for row in rows:
        best[row.role] = max(best.get(row.role, 0), row.specificity())

    return sorted(
        [row for row in rows if row.specificity() == best[row.role]],
        key=lambda row: (roles.index(row.role), row.id)
    )


def scribe(record_id):
    """
    Where a write to a record goes, from the one row that matches the most, the first made if some match as much,
    or None if none match
    """

    rows = matching(Scribe, record_id)

    if not rows:
        return None

    return min(rows, key=lambda row: (-row.specificity(), row.id))


class Source(relations.Source):
    """
    Routes each operation on a record to the source that has it. It stores nothing: it passes the call to the
    source of the unum the record's routes and scribe say, here (local) or another unum's (members). The rest
    is still here for now
    """

    KIND = "unum"

    unum = None     # Name of this unum
    local = None    # Name of the source this unum's own data is in
    members = None  # Name of the source of each other unum, by the unum's name

    _syncing = False  # Whether what's written and read is the copy here, for sync

    @contextlib.contextmanager
    def syncing(self):
        """
        Keeps writes and reads here while it's open, because what sync applies is a copy of what's elsewhere
        """

        self._syncing = True

        try:
            yield self
        finally:
            self._syncing = False

    def sources(self, record_id, roles):
        """
        The names of the sources of those who hold a record in the roles, in order, local being this unum's own
        """

        return [
            self.local if row.holder == self.unum else self.members[row.holder]
            for row in route(record_id) if row.role in roles
        ]

    def attempt(self, names, action, model, *args, **kwargs):
        """
        Does the action on the first of the sources that can, the last one's error being the one raised
        """

        *others, last = names

        for name in others:
            try:
                return getattr(relations.source(name), action)(model, *args, **kwargs)
            except (relations.SourceError, relations.NotFoundError):
                continue

        return getattr(relations.source(last), action)(model, *args, **kwargs)

    def init(self, model):
        """
        Every source it routes to has to know the model
        """

        for name in dict.fromkeys([self.local, *self.members.values()]):
            relations.source(name).init(model)

    def write(self, action, model, *args, **kwargs):
        """
        Writes to where the scribe says, the owner, the writers or here, or here if there's no one to say
        """

        rule = None if self._syncing else scribe(model.id)
        names = self.sources(model.id, [rule.to]) if rule and rule.to != "local" else []

        return self.attempt(names or [self.local], action, model, *args, **kwargs)

    def create(self, model, *args, **kwargs):
        """
        Creates where it's written to
        """

        return self.write("create", model, *args, **kwargs)

    def retrieve(self, model, *args, **kwargs):
        """
        Retrieves a record by its id from here if this unum holds it, or else its owner, writers and readers
        in turn. Without an id to go by it's from here
        """

        criteria = model._record._names[model._id].criteria # pylint: disable=protected-access
        names = self.sources(criteria["eq"], ["owner", "writer", "reader"]) if criteria and not self._syncing else []

        if self.local in names:
            names.remove(self.local)
            names.insert(0, self.local)

        return self.attempt(names or [self.local], "retrieve", model, *args, **kwargs)

    def update(self, model, *args, **kwargs):
        """
        Updates where it's written to
        """

        return self.write("update", model, *args, **kwargs)

    def delete(self, model, *args, **kwargs):
        """
        Deletes where it's written to
        """

        return self.write("delete", model, *args, **kwargs)

    def count(self, model, *args, **kwargs):
        """
        Counts here for now
        """

        return relations.source(self.local).count(model, *args, **kwargs)


def models(*classes):
    """
    The models sync can apply, by the app (source) and block (model) a journal row has
    """

    return {(model.SOURCE, model.thy().NAME): model for model in classes}


def clash(row, error):
    """
    Records a journal row that can't be applied, with the same id, and returns that it clashed
    """

    Clash(id=row["id"], what={"error": error}).create()

    return "clash"


def apply(source, row, models):
    """
    Applies a journal row from another unum here, by making the same write with the writer the row says, so
    the journal row that's written has the same id and the transaction is the same everywhere. A row that's here
    is skipped, and one that clashed is left alone. One that can't be applied, because the record isn't at the
    version it was from, or isn't there, or already is, or its model isn't known, is a clash. Returns what it did
    """

    # pylint: disable=redefined-outer-name

    if relations_unifist.Journal.one(row["id"]).retrieve(False):
        return "skipped"

    if Clash.one(row["id"]).retrieve(False):
        return "clash"

    what = row["what"]
    model = models.get((what["app"], what["block"]))

    if model is None:
        return clash(row, "model")

    writer = row["id"].rsplit(":", 1)[1]

    with source.syncing():

        try:

            if what["action"] == "create":

                model(**what["after"]).create(writer=writer)

            else:

                before = what["before"]
                query = model.many(id=what["id"], version=before["version"])

                if what["action"] == "update":
                    changes = {
                        name: value for name, value in what["after"].items()
                        if name not in ["id", "version"] and value != before.get(name)
                    }
                    done = query.set(**changes).update(writer=writer)
                else:
                    done = query.delete(writer=writer)

                if not done:
                    return clash(row, "version" if model.many(id=what["id"]).count() else "missing")

        except relations.UniqueError:

            return clash(row, "exists")

    return "applied"
