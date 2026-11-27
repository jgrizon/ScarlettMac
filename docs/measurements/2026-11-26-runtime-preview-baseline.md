# Runtime preview baseline, 26 November 2026

Measured on the development Mac (Apple M3 Pro, 18 GB, 4K display) with the
November 26 checkpoint runtime, Wine 11 and Apple D3DMetal. The contributor
ran one title instance at a time and confirmed the offline picker using a
local marker.

## Runs

| Run | Log | Seconds | Presents | Mean fps | Median segment fps |
| --- | --- | --- | --- | --- | --- |
| A | `runs/20261126-123001.log` | 44 | 256 | 8.66 | 30.00 |
| B | `runs/20261126-124043.log` | 176 | 2048 | 19.41 | 24.79 |

Run B used a planned 180-second window. To analyze a saved log, run
`python3 tools/fps-report.py path/to/runtime.log` from the repository root.

## What the baseline shows

- The title presents through the opening and the illustrated loading artwork
  only. No 3D world and no gameplay frame was captured in either run.
- The 30 fps cap holds in the menus (A measured 30.00 fps over six segments).
  Run B spends most of its time between 23 and 26 fps, below the cap, because
  the host, not the cap, is the limit.
- Presents are logged only when the frame counter reaches a power of two, so a
  missing present line is not proof that presents stopped. The frame counter
  reached 3273 in run B, 65 s after the last present line; the next present line
  would have been frame 4096.
- Title-memory refresh is the largest CPU cost: 3741 submissions in 176.5 s,
  9287 ranges, 635 GB copied, 169.8 MB per submission, 3.6 GB/s. Fault tracking
  is off, so a whole copy is refreshed rather than the pages the title wrote.
- Dropped work is counted, not inferred: 81 shader translation refusals
  (`shader does not translate`), 4 black frames, 1 unordered view the host
  cannot store, 1 ignored depth-bounds test, 4 slow host submissions.

## Shader translation, not the present path, is what stalls the run

Run B translated 574 shaders, 126 of them for the first time in this run
(`cached=false`, 126 distinct hashes) and 448 from the cache. The 126 first
translations account for 266.8 s of caller wait and 783.4 s of user CPU inside a
176 s run, with 206.3 s of kernel time. By stage they are 542 compute, 16 vertex
and 16 pixel shaders, so this is almost entirely the compute work that builds
the world.

| Caller wait per shader | Shaders | Total wait | Total user CPU |
| --- | --- | --- | --- |
| under 100 ms | 52 | 2.1 s | 7.6 s |
| 100-500 ms | 11 | 1.8 s | 4.9 s |
| 1-3 s | 24 | 55.0 s | 172.3 s |
| 3-10 s | 39 | 207.9 s | 598.6 s |

The 26.35 s hitch between frame 128 and 256 contains 25 first translations
summing 51.4 s of wait, so about two are in flight at once. The hitch is a
translation storm, and the run never reaches the world because it spends its
budget translating.

This changes where a fix pays: making a refused shader translatable adds a
multi-second first-use cost, so coverage work and translation cost have to move
together.

## Comparing runs

`tools/fps-report.py --compare BASELINE LOG` prints one number per quantity for
both runs with the change, including the counts of dropped work above. A change
counts as a win only when the quantity it targets moves and the presented image
does not regress.

## Correction: the world is reached, the runs were too short

The first version of this page said no 3D world had been captured on this
track. That was a run-length artifact, and the title's own state dump disproves
it. A run on the same build reached the Prologue intro and then crashed; its
dump (`victory-20261126-122527-648.crash.log` in the Wine prefix) records:

| Field | Value |
| --- | --- |
| Game running time | 0h:3m:50s |
| Frame | 1379 |
| Game state | Game Running |
| Mission | fbk_stry000_FBK_STRY000_INTRO |
| Streaming requests | 899, TileHeap 3442 MB of 6236 MB |
| World content | 8520 buildings, 244 vehicles, 87 peds, 630 lights |
| Player position | <1828.58, 139.66, 2.80> |

The exception was `0xc0000005` at game image `+0x23cf683`, a write to address
0, followed by a second fault inside `dbghelp.dll` while the runtime reported
it. So the run stops presenting because the process dies.

Consequences for measurement: runs must last at least 300 s to reach the world,
screenshots must be taken at 220-270 s, and every run's last frame number has to
be reported, because a crash makes fps totals incomparable.
