# Changelog

All notable changes to python-relations-unum are recorded here, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.0.1] - 2026-10-14

### Added
- The package scaffold: `relations_unum` with the tooling every relations repo has (`Makefile` with `make help`, `scripts/` for releases, `Jenkinsfile`, `VERSION`, the changelog). Jenkins releases on a merge to `main`: a `release` stage (only on `main`) runs `make release`, which does nothing for a version that is already released and otherwise does the test release, the release and the tag (relations-dil/python-relations#80). Only the scaffold is in 0.0.1: routes, the Unum source, sync and the clash table are what come next (relations-dil/python-relations-unum#1).
