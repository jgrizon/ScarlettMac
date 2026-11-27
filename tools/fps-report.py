#!/usr/bin/env python3
"""fps-report.py - frame pacing, title-memory refresh cost and errors from victory logs.

Reads one or more `victory.exe run` logs (ANSI-coloured "compressed" INFO lines or
plain ones) and prints, per log:

  * the timestamp of every "frame presented ... frame=N" line and a table of the
    segments between consecutive presents (frames advanced, seconds, fps);
  * a summary: total frames, wall time, mean/median/min fps, 10 slowest segments;
  * "title-memory refreshes:" lines aggregated per 10 s window (submissions,
    ranges, MB copied - "N ranges, M bytes");
  * the first and last timestamps, plus every ERROR/error=/panic/unhandled/
    assert/fatal line grouped by message (first 200 chars, counts, repeats).

Extras that the log itself makes free, and that the present lines alone cannot
give (they are emitted on powers of two, so only 11-12 of them per run):

  * "frame waits: N, M of them ended at once" - the engine's own per-window frame
    counter, used for an fps curve in 30 s buckets;
  * "copies per frame:" - the engine's per-frame refresh cost (refreshes, MB,
    moves ms) and the fraction of the frame period it implies.

Standard library only. Read-only: the logs are never modified.
"""

import argparse
import math
import os
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------- log scrubbing

# CSI (colour, dim, italic, reset, ...), OSC (title bars) and two-byte escapes.
ANSI_CSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ANSI_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
ANSI_TWO = re.compile(r"\x1b[@-Z\\-_]")


def strip_ansi(text):
    text = ANSI_OSC.sub("", text)
    text = ANSI_CSI.sub("", text)
    return ANSI_TWO.sub("", text)


TS_RE = re.compile(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z)")
PRESENT_RE = re.compile(r"\bframe=(\d+)")
REFRESH_RE = re.compile(r"title-memory refreshes:\s*(\d+)\s+ranges?,\s*(\d+)\s+bytes")
WAITS_RE = re.compile(r"frame waits:\s*(\d+),\s*(\d+)\s+of them ended at once")
COST_RE = re.compile(
    r"(?P<subs>[\d.]+)\s+submissions.*?"
    r"(?P<refreshes>\d+)\s+refreshes\s+(?P<mb>[\d.]+)\s+MB.*?"
    r"moves\s+(?P<moves>[\d.]+)\s+ms.*?"
    r"preparing:\s+(?P<prep>[\d.]+)\s+ms"
)
ERROR_RE = re.compile(r"ERROR|error=|panic|unhandled|assert|fatal")
NORM_RE = re.compile(r"0x[0-9a-fA-F]+|\b[0-9a-fA-F]{8,}\b|\b\d+(?:\.\d+)?\b")
MB = 1_000_000.0


def parse_ts(text):
    """2026-11-26T17:18:51.624746Z -> aware datetime (UTC)."""
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in text else "%Y-%m-%dT%H:%M:%SZ"
    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)


def clock(dt):
    return dt.strftime("%H:%M:%S.") + "%03d" % (dt.microsecond // 1000)


# ------------------------------------------------------------------- log parsing


def read_log(path, ten_second=10.0):
    info = {
        "path": path,
        "bytes": os.path.getsize(path),
        "lines": 0,
        "first_ts": None,
        "last_ts": None,
        "presents": [],      # (t, frame, draws, dispatches)
        "refreshes": [],     # (t, ranges, bytes)
        "waits": [],         # (t, waits, immediate)
        "costs": [],         # (t, subs, refreshes, mb, moves_ms, prep_ms)
        "errors": [],        # (t or None, message)
        "warns": [],         # (t or None, message)
        "max_frame": (0, None),  # highest frame=N seen in any line, with its time
        "refresh_windows": {},  # window index -> [submissions, ranges, bytes]
        "ten": ten_second,
    }

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            info["lines"] += 1
            line = strip_ansi(raw).rstrip("\r\n")
            match = TS_RE.search(line[:64])
            when = parse_ts(match.group(1)) if match else None
            if when is not None:
                if info["first_ts"] is None:
                    info["first_ts"] = when
                info["last_ts"] = when

            any_frame = re.search(r"\bframe=(\d+)\b", line)
            if any_frame and int(any_frame.group(1)) > info["max_frame"][0]:
                info["max_frame"] = (int(any_frame.group(1)), when)

            if "frame presented" in line:
                frame = PRESENT_RE.search(line)
                if frame and when is not None:
                    draws = re.search(r"\bdraws=(\d+)", line)
                    disp = re.search(r"\bdispatches=(\d+)", line)
                    info["presents"].append((
                        when,
                        int(frame.group(1)),
                        int(draws.group(1)) if draws else -1,
                        int(disp.group(1)) if disp else -1,
                    ))
                continue

            if "title-memory refreshes:" in line:
                refresh = REFRESH_RE.search(line)
                if refresh and when is not None:
                    ranges = int(refresh.group(1))
                    nbytes = int(refresh.group(2))
                    info["refreshes"].append((when, ranges, nbytes))
                    if info["first_ts"] is not None:
                        index = int((when - info["first_ts"]).total_seconds() // ten_second)
                        slot = info["refresh_windows"].setdefault(index, [0, 0, 0])
                        slot[0] += 1
                        slot[1] += ranges
                        slot[2] += nbytes
                continue

            if "frame waits:" in line:
                waits = WAITS_RE.search(line)
                if waits and when is not None:
                    info["waits"].append((when, int(waits.group(1)), int(waits.group(2))))
                continue

            if "copies per frame:" in line:
                cost = COST_RE.search(line)
                if cost:
                    info["costs"].append((
                        when,
                        float(cost.group("subs")),
                        int(cost.group("refreshes")),
                        float(cost.group("mb")),
                        float(cost.group("moves")),
                        float(cost.group("prep")),
                    ))
                continue

            if ERROR_RE.search(line):
                message = TS_RE.sub("", line, count=1).strip()
                info["errors"].append((when, message[:200]))
                continue

            if re.search(r"\bWARN\b", line):
                message = TS_RE.sub("", line, count=1).strip()
                info["warns"].append((when, message[:200]))

    return info


# ----------------------------------------------------------------- report pieces


def rule(title):
    print()
    print(title)
    print("-" * len(title))


def present_segments(info):
    """(index, t, frame, dt_seconds, dframes, fps) for each consecutive pair."""
    rows = []
    presents = info["presents"]
    for index in range(1, len(presents)):
        before_t, before_f = presents[index - 1][0], presents[index - 1][1]
        after_t, after_f = presents[index][0], presents[index][1]
        dt = (after_t - before_t).total_seconds()
        dframes = after_f - before_f
        fps = dframes / dt if dt > 0 and dframes > 0 else float("nan")
        rows.append((index, after_t, after_f, dt, dframes, fps))
    return rows


def report_presents(info):
    rule("1. presents")
    presents = info["presents"]
    if not presents:
        print("  (no 'frame presented' lines)")
        return None

    width = max(len(str(p[1])) for p in presents)
    print("  %-3s %-13s %*s %8s %8s %8s %8s %8s"
          % ("#", "timestamp", width, "frame", "draws", "dispatch", "+frames", "+s", "fps"))
    first_t = presents[0][0]
    for index, (when, frame, draws, disp) in enumerate(presents):
        if index == 0:
            print("  %-3d %-13s %*d %8d %8d %8s %8s %8s"
                  % (index + 1, clock(when), width, frame, draws, disp, "-", "-", "-"))
            continue
        prev_t, prev_f = presents[index - 1][0], presents[index - 1][1]
        dt = (when - prev_t).total_seconds()
        dframes = frame - prev_f
        fps = dframes / dt if dt > 0 and dframes > 0 else float("nan")
        print("  %-3d %-13s %*d %8d %8d %8d %8.3f %8.2f"
              % (index + 1, clock(when), width, frame, draws, disp, dframes, dt, fps))

    print("  (the runtime logs a present only when the frame counter reaches a power of two:")
    print("   frames advanced is exact, the per-row interval is only as fine as that scheme)")
    return first_t


def report_summary(info):
    rule("2. summary")
    presents = info["presents"]
    if len(presents) < 2:
        print("  (not enough presents)")
        return None

    first_t, last_t = presents[0][0], presents[-1][0]
    first_f, last_f = presents[0][1], presents[-1][1]
    wall = (last_t - first_t).total_seconds()
    frames = last_f - first_f
    mean_fps = frames / wall if wall > 0 else float("nan")

    rows = present_segments(info)
    fps_values = [r[5] for r in rows if r[5] == r[5]]
    median = statistics.median(fps_values) if fps_values else float("nan")

    print("  total frames presented (counter)   %d  (first %d -> last %d, %d advanced)"
          % (last_f, first_f, last_f, frames))
    print("  wall time between first/last press %8.3f s" % wall)
    print("  mean fps (frames / wall)           %8.2f" % mean_fps)
    print("  median fps over %2d segments         %8.2f" % (len(fps_values), median))
    print("  min fps over segments              %8.2f"
          % (min(fps_values) if fps_values else float("nan")))
    print("  max fps over segments              %8.2f"
          % (max(fps_values) if fps_values else float("nan")))
    if mean_fps == mean_fps:
        print("  mean frame period implied          %8.1f ms" % (1000.0 / mean_fps))
    if info["last_ts"] is not None:
        tail = (info["last_ts"] - last_t).total_seconds()
        print("  last present -> last log line      %8.1f s%s"
              % (tail, "  (no frame after the last present)" if tail > 1.0 else ""))
    max_frame, max_when = info["max_frame"]
    if max_frame > last_f:
        print("  highest frame= seen in any line    %8d  at %s  (the counter reached it, so it"
              % (max_frame, clock(max_when) if max_when else "-"))
        print("    kept rendering after the last present; the next present line would be the"
              " next power of two, %d" % (2 ** max_frame.bit_length()))

    rule("2b. 10 slowest segments")
    print("  %-4s %-13s %9s %9s %9s" % ("to #", "timestamp", "+frames", "+s", "fps"))
    for index, when, frame, dt, dframes, fps in sorted(rows, key=lambda r: r[5])[:10]:
        print("  %-4d %-13s %9d %9.3f %9.2f" % (index + 1, clock(when), dframes, dt, fps))
    return mean_fps, wall, median


def report_refreshes(info):
    rule("3. title-memory refreshes per %g s window" % info["ten"])
    windows = info["refresh_windows"]
    if not windows:
        print("  (no 'title-memory refreshes:' lines)")
        return
    print("  %-9s %-11s %13s %10s %12s %10s %12s"
          % ("window", "starts at", "submissions", "ranges", "MB copied", "MB/subm", "ranges/subm"))
    for index in sorted(windows):
        subs, ranges, nbytes = windows[index]
        start = clock(info["first_ts"] + timedelta(seconds=index * info["ten"]))
        print("  %-9s %-11s %13d %10d %12.1f %10.2f %12.1f"
              % ("%gs" % (index * info["ten"]), start, subs, ranges,
                 nbytes / MB, nbytes / MB / subs, ranges / subs))

    total_subs = sum(w[0] for w in windows.values())
    total_bytes = sum(w[2] for w in windows.values())
    total_ranges = sum(w[1] for w in windows.values())
    span = (info["last_ts"] - info["first_ts"]).total_seconds() if info["first_ts"] else 0.0
    print("  %-9s %-11s %13d %10d %12.1f %10.2f %12.1f"
          % ("total", "", total_subs, total_ranges, total_bytes / MB,
             total_bytes / MB / total_subs, total_ranges / total_subs))
    if span > 0:
        print("  %d submissions in %.1f s = %.1f/s, %.1f MB/s of title memory copied"
              % (total_subs, span, total_subs / span, total_bytes / MB / span))
    steady = [w for w in windows.values() if w[0] >= 30]
    if steady:
        print("  busiest %d windows (>=30 submissions): %.1f submissions and %.1f MB per window"
              % (len(steady), statistics.mean(w[0] for w in steady),
                 statistics.mean(w[2] for w in steady) / MB))


def report_errors(info):
    rule("4. first/last timestamps and errors")
    if info["first_ts"] is not None:
        print("  first timestamp  %s" % info["first_ts"].strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z")
    if info["last_ts"] is not None:
        print("  last  timestamp  %s" % info["last_ts"].strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z")
    if info["first_ts"] and info["last_ts"]:
        print("  log span         %.3f s" % (info["last_ts"] - info["first_ts"]).total_seconds())

    errors = info["errors"]
    print("  error-ish lines  %d  (pattern: ERROR|error=|panic|unhandled|assert|fatal)"
          % len(errors))
    if not errors:
        return

    counts = {}
    for _, message in errors:
        counts[message] = counts.get(message, 0) + 1
    print()
    print("  %-5s %s" % ("count", "message (first 200 chars, timestamp removed)"))
    for message, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-5d %s" % (count, message))

    repeated = [(c, m) for m, c in counts.items() if c > 1]
    print("  repeats: %d message(s) seen more than once, %d line(s) in total"
          % (len(repeated), sum(c for c, _ in repeated)))

    if len(counts) > 5:
        print()
        print("  same, with hex addresses and numbers collapsed (what repeats):")
        kinds = {}
        for _, message in errors:
            kind = NORM_RE.sub("#", message)
            kinds[kind] = kinds.get(kind, 0) + 1
        for kind, count in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])):
            print("  %-5d %s" % (count, kind))
        print("  %d distinct kinds over %d lines" % (len(kinds), len(errors)))

    warns = info["warns"]
    if warns:
        print()
        print("  WARN lines (not part of the pattern above, but these are what repeat): %d"
              % len(warns))
        counts = {}
        for _, message in warns:
            counts[message] = counts.get(message, 0) + 1
        for message, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print("  %-5d %s" % (count, message))


def frame_at(presents, when):
    """Frame counter interpolated between the bracketing presents."""
    for index in range(1, len(presents)):
        if presents[index][0] >= when:
            t0, f0 = presents[index - 1][0], presents[index - 1][1]
            t1, f1 = presents[index][0], presents[index][1]
            span = (t1 - t0).total_seconds()
            if span <= 0:
                return float(f1)
            return f0 + (f1 - f0) * ((when - t0).total_seconds() / span)
    return float(presents[-1][1])


def report_curve(info, bucket):
    """30 s fps curve from the present counter, plus the engine's waits/s."""
    presents = info["presents"]
    if len(presents) < 2:
        return
    rule("5. fps curve in %g s buckets (from the present counter)" % bucket)
    first_t, last_t = presents[0][0], presents[-1][0]
    step = timedelta(seconds=min(bucket, (last_t - first_t).total_seconds()))

    edges = []
    edge = first_t
    while edge < last_t:
        edges.append(edge)
        edge = edge + step
    edges.append(last_t)

    print("  %-10s %10s %10s %9s" % ("starts at", "frames", "seconds", "fps"))
    for index in range(1, len(edges)):
        start, end = edges[index - 1], edges[index]
        span = (end - start).total_seconds()
        frames = frame_at(presents, end) - frame_at(presents, start)
        fps = frames / span if span > 0 else float("nan")
        print("  %-10s %10.0f %10.1f %9.2f" % (clock(start), frames, span, fps))

    waits = info["waits"]
    if waits:
        print()
        print("  frame waits (engine counter; each entry covers the gap to the previous entry):")
        print("  %-10s %7s %8s %10s" % ("at", "waits", "at once", "waits/s"))
        for index in range(1, len(waits)):
            when, count, immediate = waits[index]
            span = (when - waits[index - 1][0]).total_seconds()
            print("  %-10s %7d %8d %10.2f"
                  % (clock(when), count, immediate, count / span if span > 0 else float("nan")))
        total_span = sum((waits[i][0] - waits[i - 1][0]).total_seconds()
                         for i in range(1, len(waits)))
        total_waits = sum(w[1] for w in waits)
        print("  %d waits over %.1f s = %.1f waits/s; note this is not fps - the runtime"
              % (total_waits, total_span, total_waits / total_span))
        print("  makes about two waits per presented frame here, and 'N of them ended at once'"
              " is the share that did not block")


def report_cost(info, mean_fps, steady_fps):
    costs = info["costs"]
    if not costs:
        return
    rule("6. refresh cost per frame (engine's 'copies per frame')")
    period = 1000.0 / steady_fps if steady_fps else float("nan")
    print("  steady frame period: %.1f ms (median segment fps %.2f); %s"
          % (period, steady_fps, "%.1f ms if every frame is counted over the whole run"
             % (1000.0 / mean_fps if mean_fps else float("nan"))))
    print("  %-10s %10s %10s %10s %10s %9s"
          % ("timestamp", "refreshes", "MB/frame", "ms/frame", "%period", "prep ms"))
    for when, subs, refreshes, mb, moves, prep in costs:
        print("  %-10s %10d %10.1f %10.2f %9.0f%% %9.2f"
              % (clock(when) if when else "-", refreshes, mb, moves,
                 100.0 * moves / period, prep))

    moves = [c[4] for c in costs]
    mb = [c[3] for c in costs]
    refreshes = [c[2] for c in costs]
    mean_moves = statistics.mean(moves)
    print("  mean over %d samples: %.1f MB/frame, %.2f ms/frame (median %.2f, max %.2f)"
          % (len(costs), statistics.mean(mb), mean_moves, statistics.median(moves), max(moves)))
    print("  => %.0f%% of the steady frame period, %.0f%% of wall time"
          " (%.2f ms x %.2f frames/s over the run)"
          % (100.0 * mean_moves / period if period else float("nan"),
             100.0 * mean_moves * mean_fps / 1000.0 if mean_fps else float("nan"),
             mean_moves, mean_fps))
    print("  per engine refresh: %.2f ms (%.2f ms/frame / %.1f refreshes/frame), %.1f MB"
          % (mean_moves / statistics.mean(refreshes), mean_moves, statistics.mean(refreshes),
             statistics.mean(mb) / statistics.mean(refreshes)))

    lines = info["refreshes"]
    if lines:
        sizes = sorted(b for _, _, b in lines)
        mean_mb = statistics.mean(sizes) / MB
        print("  per submission (log lines): %d lines, median %.1f MB, mean %.1f MB"
              % (len(sizes), sizes[len(sizes) // 2] / MB, mean_mb))
        half = lines[len(lines) // 2:]
        span = (half[-1][0] - half[0][0]).total_seconds() if len(half) > 1 else 0.0
        if span > 0:
            rate = (len(half) - 1) / span
            print("  submissions in the 2nd half of the log: %.2f/s, %.1f GB/s copied"
                  % (rate, rate * statistics.mean(sizes) / 1e9))
    print("  (assumption: 'moves ... ms' is host-thread copy time inside the frame, so it"
          " blocks the present; copystat's 'preparing' equals it to within 0.1 ms)")


# ------------------------------------------------------------------- crashes

def read_crashes(path):
    """[(when, process, message)] from a crashes.log (unix seconds)."""
    entries = []
    when = None
    process = None
    try:
        handle = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return entries
    with handle:
        for line in handle:
            match = re.match(r"unix time (\d+), process (\d+)", line)
            if match:
                when, process = int(match.group(1)), int(match.group(2))
                continue
            if when is not None and line.startswith("VIctory: "):
                entries.append((when, process, line.strip()))
                when = None
    return entries


def report_crashes(info, path):
    if not path:
        return
    rule("0. crash records in this run's time window")
    entries = read_crashes(path)
    if not entries:
        print("  no crash entries in %s" % path)
        return
    first, last = info["first_ts"], info["last_ts"]
    window = []
    for when, process, message in entries:
        seen = datetime.fromtimestamp(when, tz=timezone.utc)
        # Runs now queue back to back, so the window must not reach into the
        # previous run (a fault cannot precede this run's first line; the
        # crash file stamps whole seconds) nor far into the next one (the
        # title's own dump writer faults within seconds of the first fault).
        if first and last and (first - timedelta(seconds=2)) <= seen <= (last + timedelta(seconds=45)):
            window.append((seen, process, message))
    if window:
        for seen, process, message in window:
            print("  crash record at %s (pid %d): %s" % (clock(seen), process, message[:160]))
    else:
        newest = datetime.fromtimestamp(entries[-1][0], tz=timezone.utc)
        print("  no crash inside this run's window (newest entry in the file: %s)"
              % clock(newest))


def report(path, bucket, refresh_window, crash_log):
    info = read_log(path, refresh_window)
    print("=" * 78)
    print("%s  (%d bytes, %d lines)" % (path, info["bytes"], info["lines"]))
    print("=" * 78)
    report_crashes(info, crash_log)
    report_presents(info)
    summary = report_summary(info)
    report_refreshes(info)
    report_errors(info)
    report_curve(info, bucket)
    if summary:
        report_cost(info, summary[0], summary[2])
    return info


# ------------------------------------------------------------------- comparison

# What a change must move, one number each, so two runs are judged on the same
# quantities. Dropped work is counted from the lines that report it, never
# inferred from a missing line.
def metrics(info):
    presents = info["presents"]
    values = {
        "frames presented": 0.0,
        "mean fps": float("nan"),
        "median fps": float("nan"),
        "MB per submission": float("nan"),
        "submissions per s": float("nan"),
        "highest frame seen": 0.0,
        "dropped shaders": 0.0,
        "dropped draws": 0.0,
        "black frames": 0.0,
        "unordered views the host cannot store": 0.0,
        "depth bounds ignored": 0.0,
        "slow submissions": 0.0,
        "hangs": 0.0,
    }
    if len(presents) >= 2:
        first_t, last_t = presents[0][0], presents[-1][0]
        wall = (last_t - first_t).total_seconds()
        frames = presents[-1][1] - presents[0][1]
        values["frames presented"] = float(frames)
        if wall > 0:
            values["mean fps"] = frames / wall
        rows = present_segments(info)
        fps = [r[5] for r in rows if r[5] == r[5]]
        if fps:
            values["median fps"] = statistics.median(fps)
    values["highest frame seen"] = float(info["max_frame"][0])

    lines = info["refreshes"]
    if lines:
        values["MB per submission"] = statistics.mean(b for _, _, b in lines) / MB
    if info["first_ts"] and info["last_ts"] and lines:
        span = (info["last_ts"] - info["first_ts"]).total_seconds()
        if span > 0:
            values["submissions per s"] = len(lines) / span

    counts = {
        "dropped shaders": "shader does not translate",
        "dropped draws": "without a host pipeline",
        "black frames": "black frame",
        "unordered views the host cannot store": "unordered view in a format the host cannot store",
        "depth bounds ignored": "no depth bounds test",
        "slow submissions": "slow host submission",
        "hangs": "host GPU hang",
    }
    for name, needle in counts.items():
        values[name] = float(
            sum(1 for _, m in info["errors"] + info["warns"] if needle in m))
    return values


def span_fps(info):
    """{(from_frame, to_frame): fps} from consecutive present lines.

    Presents are logged only at power-of-two frame counts, so these spans are
    the finest common ground two runs have: a run killed at frame 273 and one
    killed at 3952 can still be compared over 1-256.
    """
    rows = {}
    presents = info["presents"]
    for index in range(1, len(presents)):
        before_t, before_f = presents[index - 1][0], presents[index - 1][1]
        after_t, after_f = presents[index][0], presents[index][1]
        span = (after_t - before_t).total_seconds()
        if span > 0 and after_f > before_f:
            rows[(before_f, after_f)] = (after_f - before_f) / span
    return rows


def report_compare(base, other, base_name, other_name):
    before, after = metrics(base), metrics(other)
    print("=" * 78)
    print("compare: %s  ->  %s" % (base_name, other_name))
    print("=" * 78)
    print("  %-38s %12s %12s %10s" % ("", "before", "after", "change"))
    for name in before:
        b, a = before[name], after[name]
        if b != b and a != a:
            continue
        if b == a:
            change = "same"
        elif b != b or a != a:
            change = "n/a"
        elif name in ("MB per submission", "dropped shaders", "dropped draws",
                      "black frames", "unordered views the host cannot store",
                      "depth bounds ignored", "slow submissions", "hangs"):
            change = "%+.0f%%" % (100.0 * (a - b) / b) if b else "new"
        else:
            change = "%+.1f%%" % (100.0 * (a - b) / b) if b else "new"
        if b == b and abs(b - round(b)) < 1e-9:
            print("  %-38s %12.0f %12.0f %10s" % (name, b, a, change))
        else:
            print("  %-38s %12.2f %12.2f %10s" % (name, b, a, change))

    # The same frame spans in both runs: the honest comparison when one run
    # died earlier than the other.
    spans_before, spans_after = span_fps(base), span_fps(other)
    common = sorted(set(spans_before) & set(spans_after))
    if common:
        print()
        print("  fps over the same frame spans (both runs reached them):")
        print("  %-17s %10s %10s %10s" % ("frames", "before", "after", "change"))
        for span in common:
            b, a = spans_before[span], spans_after[span]
            print("  %-17s %10.2f %10.2f %9.1f%%"
                  % ("%d-%d" % span, b, a, 100.0 * (a - b) / b if b else 0.0))
        mb, ma = statistics.mean(spans_before[s] for s in common), statistics.mean(
            spans_after[s] for s in common)
        print("  %-17s %10.2f %10.2f %9.1f%%"
              % ("mean of those", mb, ma, 100.0 * (ma - mb) / mb if mb else 0.0))
    print()
    print("  A change is a win only if the metric it targets moved and the image did not")
    print("  regress; higher is better for fps and frames, lower for everything else.")


def interval(text):
    try:
        seconds = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("enter an interval in seconds") from None
    if not math.isfinite(seconds) or seconds < 1e-6:
        raise argparse.ArgumentTypeError("interval must be finite and at least 0.000001 seconds")
    return seconds


def main(argv):
    parser = argparse.ArgumentParser(
        description="Report frame pacing, title-memory refresh cost and errors from victory logs.")
    parser.add_argument("logs", nargs="+", metavar="LOG",
                        help="one or more victory run logs (ANSI or plain)")
    parser.add_argument("--bucket", type=interval, default=30.0,
                        help="fps curve bucket in seconds (default 30)")
    parser.add_argument("--refresh-window", type=interval, default=10.0,
                        help="title-memory refresh aggregation window in seconds (default 10)")
    parser.add_argument("--compare", metavar="BASELINE",
                        help="compare BASELINE against each LOG instead of reporting them")
    parser.add_argument("--crash-log", metavar="PATH",
                        help="read crash records from an explicitly supplied Wine crash log")
    args = parser.parse_args(argv)

    missing = [p for p in args.logs if not os.path.isfile(p)]
    if args.compare and not os.path.isfile(args.compare):
        missing.append(args.compare)
    if args.crash_log and not os.path.isfile(args.crash_log):
        missing.append(args.crash_log)
    if missing:
        for path in missing:
            print("fps-report: no such file: %s" % path, file=sys.stderr)
        return 2

    if args.compare:
        base = read_log(args.compare, args.refresh_window)
        for path in args.logs:
            if os.path.abspath(path) == os.path.abspath(args.compare):
                continue
            report_compare(base, read_log(path, args.refresh_window), args.compare, path)
        return 0

    for path in args.logs:
        report(path, args.bucket, args.refresh_window, args.crash_log)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
