# Comparing ScarlettMac runtime runs

Use the [Runtime Preview instructions](../runtime-preview/BUILD.md) for the
pinned source, build, and Wine launcher. Record the prepared revision, Mac
model, memory, Wine and graphics backend versions, game profile, cache state,
and runtime flags for each test. Capture a visible frame at the point being
compared and save the runtime log.

## Frame timing and title memory

```sh
python3 tools/fps-report.py runs/baseline.log
python3 tools/fps-report.py --compare runs/baseline.log runs/candidate.log
```

The comparison uses frame spans both runs reached. Present log entries appear
at sparse frame intervals, so a gap between entries alone does not establish
a stall. Record the exit status. To show records from the matching Wine crash
log when a run ends early, pass its path with `--crash-log`.

The contributor’s measurements cover the
[initial runtime baseline](measurements/2026-11-26-runtime-preview-baseline.md)
and [written-page copies](measurements/2026-11-26-copy-written-pages.md).
