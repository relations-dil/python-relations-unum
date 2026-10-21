# Changelog

All notable changes to python-relations-unum are recorded here, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]


### Changed
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
