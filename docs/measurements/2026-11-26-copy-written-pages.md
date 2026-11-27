# Copy only the title pages that were written

The contributor measured on Apple Silicon on November 26, 2026. Both runs
used the same Wine setup, Series build (image hash `b99f876b74d4a77f`),
300-second duration and warm shader cache.

## The change

Before every host submission the runtime refreshes its host copies of title
memory. With fault tracking off (the default under Rosetta) a refresh copies
each tracked range whole: through the loading screens that is about 170 MB per
submission, 10 submissions a second, over 1.7 GB/s spent copying memory the
title mostly did not touch.

Fault tracking marks the pages the title writes, so a refresh copies only
those. It was off by default under Rosetta because Rosetta cannot resume some
256-bit stores midway through a fault. For a build whose plain 256-bit stores
are listed, those stores are already patched, so the patch turns tracking on
by default for that build. `VICTORY_FAULT_TRACKING` and
`VICTORY_PATCH_MASKED` still override it.

## Result

| | before (`20261126-133112-refreshafteroff`) | after (`20261126-135153-verify-track`) |
|---|---|---|
| fault tracking | off | on |
| MB copied per submission (mean) | 170.32 | 1.27 (-99%) |
| submissions per second | 10.33 | 14.74 (+43%) |
| highest frame reached | 2199 | 4775 (+117%) |
| mean fps over the frame spans both runs reached | 21.57 | 22.95 (+6.4%) |
| fps, frames 1024-2048 | 17.97 | 26.28 (+46%) |
| dropped shaders / dropped draws / black frames | 100 / 1 / 4 | 100 / 1 / 4 (same) |

The 180 s baseline from a separate build (`20261126-124043`) copies 169.81 MB
per submission on average (3741 submissions), matching the "before" column.

The picture is unchanged: both runs show the loading artwork, which is what
the title draws at that point. The fix does not change what is drawn.

## What it does not fix

The title still raises its own `ALERT_ERROR_SUPPORT` trap (game image
`+0x23cf683`) when the intro cutscene's streaming list stays in `Prestream`
past its deadline. The verification run above did not hit it inside 300 s,
but a later run on this base did, at 3m28s game time with 740 streaming
requests outstanding (title crash report
`victory-20261126-141944-32.crash.log`). That stall is in the streaming path
and is being investigated separately.
