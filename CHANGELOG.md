# Changelog

All notable changes to python-relations-unum are recorded here, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [0.4.1] - 2026-10-23

### Changed
- `Route`, `Scribe` and `Clash` are in the `unum` source, not `unifist`, so their tables are in the `unum` schema, where the app that owns them has them (unum-apps/unifist-unum#3). The `unifist` and `unum` sources are always straight databases and never routed: the app has a plain source of each name, and the routed `Source` is the `pluribus`, whatever this unum is joined with, as the rows that route it are read from `unum`. They are plain models on a new `UnumBase`, not `UnifistBase`, as these records are never shared. `Sequence`, `Slug` and `Journal` stay in `unifist`.

## [0.4.0] - 2026-10-22

### Added
- Members are `Route` rows, read each time they're needed, so joining is inserting a row and leaving is deleting it, with no restart and no configmap. A holder is anyone a row with a `url` names (not this unum), and a unum is a member when its owner's row, with no identifier, model or source (`unum=b, role=owner, holder=b, url=...`), says who holds it. The first row of a holder gives its url. Reading them is one local query for each request, as `matching()` already is for get-by-id (relations-dil/python-relations-unum#11).
- One `RestSource` for each holder, named `<source>-<holder>` (`unum-b`), made when its row's url is new and made again, under the same name, only if the url changes. It is told about the model it is made for, as models made later are told by every source there is.
- With a member row in place get-by-id finds a record of that unum through `route()`: the row matches every id that ends in the unum, so no fallback to the unum in the id is needed (relations-dil/python-relations-unum#10, closed for this).

### Changed
- `members=` when making a `Source` is optional. Given, it is still there, apart from the rows, and wins for a holder both name. `init` reads no rows, as they may not be there yet.
- `journal(source, member)` finds a unum's source from `Source.universe()`, not from `members`.
- `Source.holders` and `Source.reach` are new, the pieces of that, and `Source.sources` takes the model it is for. A route to a holder with no way to reach it is still an error (`KeyError`), not a write or read here.

No auth in v1; the client certs idea on relations-dil/python-relations-unum#8 is for later, and would be a `session` for the holder's `RestSource`.

## [0.3.0] - 2026-10-22

### Added
- Scoped fan-out: a query is for the unums it names with a `unum` criterion (`unum="away"` or `unum__in=[...]`), or all of them if it names none, and each is asked for its own rows alone, with `unum=<that unum>` (this unum's own source, `local`, with `unum=<this unum>`). A query naming only this unum is answered from `local` and goes no further, so a member's API, which runs its own unum `Source`, doesn't fan out again and send the whole Net back. A unum that's neither this one nor a member is never asked, so a query naming only those has no rows. Each unum's source is looked up from the unum (`Source.universe()`), not taken to be it (relations-dil/python-relations-unum#8, part of relations-dil/python-relations#93).
- `count` is the sum of each unum's own count, where it was this unum's alone. A source that can't be reached has none, as it has no rows, and what's synced is counted here alone.
- `Source.named`, `scopes`, `scoped` and `universe`, the pieces of that.

No sync and no scribe rows yet: writes stay local, the Unums just work together live. The id dedupe in `select` stays as a safety net.

### Changed
- Needs relations-unifist 0.3.0, whose models have a `unum` field (relations-dil/python-relations-unifist#8), so each model that's routed here needs `unum = str`. `requirements.txt` has the packages unifist pins (relations-restx, flask and the rest), and the `Dockerfile` and `make setup` use `python:3.13`, as flask 2.1.2 does not run on Python 3.14 and later.
- `make release-check` and `make release` don't run `build`, `test`, `lint` and `setup` again: the Jenkins stages have just run them before the release stage, so it was the same work twice. Run them yourself before checking by hand, as `make release-check` is only the checks and `dist-check` now (relations-dil/python-relations#90).

## [0.2.0] - 2026-10-20

### Added
- `RestSource`, a `relations_rest.Source` for an API that serves its models under `/model` (`/model/{singular}` and `/model/{singular}/<id>`), as relations-unifist does: it adds `/model` to the url it is given, and a model's `ENDPOINT` is relative to it. Apps opt in by making their source from it; `relations_rest.Source` is unchanged and still reads models at the root (relations-dil/python-relations-unum#5).

Needs relations-rest 0.5.5.

## [0.1.0] - 2026-10-18

### Added
- The package scaffold: `relations_unum` with the tooling every relations repo has (`Makefile` with `make help`, `scripts/` for releases, `Jenkinsfile`, `VERSION`, the changelog). Jenkins releases on a merge to `main`: a `release` stage (only on `main`) runs `make release`, which does nothing for a version that is already released and otherwise does the test release, the release and the tag (relations-dil/python-relations#80).
- The tables `Clash` (what broke, with the same id as the journal row it is about, `version:identifier:resource:owner:writer`), `Route` (who has the data that matches, in what role, and where) and `Scribe` (where a write to the data that matches goes), all in the Unifist source with the journal. `Route` and `Scribe` match a record's id, `identifier:model.source:unum`, on its parts, blank meaning any, and `pattern()` shows one like the id with a `*` for any.
- `route(record_id)` returns who has a record's data, owners then writers then readers, the rows that match the most winning for each role, and `scribe(record_id)` the one row that says where a write goes.
- `Source`, a relations source that routes each operation on a record to the source that has it, here (`local`) or another unum's (`members`). A write goes where the scribe says, the owner, the writers in order (the next if one is down) or here. A read by id is from here if this unum holds a copy, else its owner, writers and readers in turn. A query for many is sent to every source and the results merged lazily in the order the query says, a page at a time, a record in more than one only once and a source that is down skipped. `count` is still from here.
- `Source.syncing()`, which keeps writes and reads here while it is open, because what sync applies is a copy.
- `models(*classes)`, the lookup from a journal row's app and block to a model, and `apply(source, row, models)`, which applies another unum's journal row here by making the same write with the row's writer, so the journal row written has the same id and the transaction is the same everywhere. It skips a row that is here already and returns `"applied"`, `"skipped"` or `"clash"`. A row that cannot be applied, because the record is not at the version it was from, is not there, already is, or its model is not known, is recorded as a `Clash` (`version`, `missing`, `exists`, `model`) and left alone until someone sorts it out.
- `journal(source, member)`, another unum's journal, and `sync(source, member, models)`, which applies what it has that this unum does not, oldest first, and returns how many were applied, skipped and clashed.
- A record that clashed is refused by `update` and `delete` unless `force=True` (`ClashError`), by id or by a query, but not while syncing. Reads are not refused, the app decides.

Needs relations-dil 0.6.20 and relations-unifist 0.1.0 (relations-dil/python-relations-unifist#1).
