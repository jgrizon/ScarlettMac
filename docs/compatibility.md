# Compatibility results

Tested on an Apple M3 Max with CrossOver Preview 27.0.0.41073 and D3DMetal 4.0b3.

## November 26 and 27 native window tests

These Series S tests used a local development build of ScarlettMac with four shader fixes, desktop AMD FSR 3.1.6, and a 720p game output profile.

| Test | Observed result |
| --- | --- |
| Prologue pipeline cache | The first scene frame recorded 6,829 draws with the prepared pipeline cache and 503 in the cold run. The warmed run showed the prison yard, watchtower, and people in silhouette. |
| Prologue display layers | Fenced samples from the 720p layer contained color while the 4K layer was black at the sampled points. Selecting the 720p layer as the base picture made the fence and figures clearer in the opening shot. Later frames still washed out before the memory guard stopped the run. |
| Prologue movement tutorial | A Series S replay with the 720p layer as the base reached the prison yard and displayed both movement prompts. After the prompts, the game read opposite right-stick directions, forward left-stick input, and neutral releases. The native window remained overexposed and ran at about 0.7 fps during the test. The images did not establish visible movement from those inputs. The run ended at its 850-second time limit. |
| Gone Fishing save replay | A run with the FSR sampling trace disabled read the save and recorded 22,564 draws on its first heavy 3D frame. The saved frame was almost white. The memory guard stopped the run after 127.4 seconds, before the movement check could start. |

Two earlier runs with the FSR sampling trace enabled read the same Gone Fishing save and stayed on loading artwork. One run reaching the scene with the trace disabled does not establish the cause of the loading stalls. Gameplay remains unavailable.

## Prologue rendering breakthroughs

On November 26, 2026, experimental runtimes on an Apple M3 Max with CrossOver and D3DMetal captured these scenes in the final game image.

| Test | Verified result | Remaining limit |
| --- | --- | --- |
| Local Cool Fox Series S opening | [Frame 2767](../assets/captures/prologue-character-close-up.png) showed a lit character close-up after illustrated loading artwork. | The run hit a read fault at world entry before input could be verified. |
| Series S Prologue with desktop AMD FSR | The title read the 250,880-byte Prologue save data. AMD FSR 3.1.6 upscaled the game from 1280 × 720 to 1920 × 1080. [Frame 3129](../assets/captures/prologue-prison-yard.png) showed a fenced yard and a guard tower. | Lighting was heavily overexposed. The memory guard ended the run at 179 seconds. |
| Series S Prologue with 1080p compositing | A separate run read the same save and reproduced the yard in frame 3205, with people visible near the watchtower. The runtime blended the display layers into a 1080p output. | The memory guard ended the run at 162 seconds, before a controlled camera test. |

These tests establish visible 3D output. Sustained rendering, walking, and camera control in a visible scene remain unverified. The public XCL build's measured milestone remains world loading.

## Cool Fox graphics experiments

These November 26, 2026 tests used a separate, locally adapted Cool Fox build on the same M3 Max and D3DMetal setup.

| Check | Observed result |
| --- | --- |
| Mesh rendering test | Direct dispatch and bounded indirect dispatch both drew a triangle into an 8 × 8 render target. GPU readback returned the expected white and black pixels. |
| First heavy scene | In one guarded run, all 113 logged mesh calls returned at the graphics API. Its last captured frame was black. A separate Series S run showed a character and a lit street with artifacts before the memory guard ended the run at 110 seconds. |
| Memory and synchronization | In another run, texture and staging pools grew by about 2 GiB ahead of the first heavy scene. A separate live stack showed one mesh-recording thread waiting for a read lock. The cause of the rendering stall is still open. |
| Shader export ordering | All 204 enabled shader tests passed. The subsequent native-window trial ended with a read fault. Other Cool Fox crash reports identify the same D3DMetal vertex-buffer binding function. |

## ScarlettMac Runtime Preview checkpoint

The November 26 Series S checkpoint passed its CrossOver configuration and executable inspection checks. In a native-window trial on the M3 Max, the launcher detected the offline picker. GameInput consumed the confirmation and the game moved into story loading. The game later stopped during a timing check.

| Experiment | Result |
| --- | --- |
| Normal GPU submission | Disabling per-list profiling still led to the same timed abort. |
| Round-based GPU atomic locks | Story loading continued with multi-second delays in title-memory preparation. The game hit the same timing check. |
| Full-copy title-memory refresh | This removed the multi-second page-protection delays. The measured heap-texture upload step still took about 5 seconds of wall time in one slow interval, and the game stopped. |

The [source checkpoint](../runtime-preview/BUILD.md#november-26-source-checkpoint) includes Metal mesh-output validation, GPU wait diagnostics, and optional GameInput tracing. The trace can verify the stick values returned to the game. A rendered response to those values remains to be verified.

## Recent development tests

| Area | Observed on M3 Max |
| --- | --- |
| Opening and input | The experimental runtime rendered the live 3D opening. A separate guarded run verified pause and resume input. Player movement and camera control remain unverified. |
| Memory | With four expanded pools, the host presented at least 130 frames after the first visible 3D frame. Neither earlier game assertion recurred before the host memory guard ended the test. |
| Shader translation | The runtime translated two previously unsupported pixel shaders, created their D3DMetal pipelines, and used both during the live run. |

In the November 25, 2026 native-window shader test, the host presented at least 270 frames after the first frame with 3D draws. The trial reached its 20-minute time limit without repeating either earlier game assertion.

| Capture | Observed on Mac |
| --- | --- |
| [Skyline, frame 2982](../assets/captures/development-skyline.png) | The skyline was partially rendered. Both repaired pixel shaders had already been used in this run. |
| [Pause menu, frame 2929](../assets/captures/development-pause-menu.png) | The pause menu opened over the cinematic during a separate native-window test. The opening resumed after closing it. |

The opening showed severe rendering artifacts and performance below 1 FPS. Gameplay remains unavailable.

<a name="victory-opening-cinematic"></a>

## ScarlettMac opening cinematic

This test used a private experimental ScarlettMac runtime based on VIctory. It ran Xbox Series build 1.0.2.1 with the Series X device profile on an M3 Max with 48 GB of unified memory, CrossOver Preview, and D3DMetal 4.0 beta 3. Each image is a 1920×1080 offscreen capture from that run.

| Stage | Capture | Observed on Mac |
| --- | --- | --- |
| Rendered 3D opening | [Frame 2421](../assets/captures/opening-cinematic.png) | The camera moved through several rendered shots, including the car and driver shown here. Visual artifacts remain. |
| Opening title card | [Frame 2383](../assets/captures/opening-title-card.png) | The opening title appeared after the game moved past the loading artwork. |
| World loading | [Frame 2340](../assets/captures/world-loading.png) | The loading artwork appeared while the game streamed assets for the opening scene. |

The safety monitor ended the capture run after 397.6 seconds when macOS reported memory pressure.

## GTA VI verification

These milestones track the public XCL build. The separate experimental opening replay is documented below.

<picture>
  <source media="(max-width: 480px) and (prefers-color-scheme: dark)" srcset="../assets/gta-launch-milestones-mobile-dark.svg">
  <source media="(max-width: 480px) and (prefers-color-scheme: light)" srcset="../assets/gta-launch-milestones-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="../assets/gta-launch-milestones-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="../assets/gta-launch-milestones-light.svg">
  <img alt="Four of seven GTA VI launch stages reached on Apple M3 Max. The test reached world loading. A visible 3D scene, in-world controls, and the first mission are open." src="../assets/gta-launch-milestones-dark.svg">
</picture>

[Setup menus and world-loading captures](../README.md#captured-on-mac)

<details>
<summary>What each milestone measures</summary>

- **Offline boot** was verified with network access disabled.
- **Intro graphics** rendered during startup.
- **Setup and menus** accepted controller input and ran at about 30 FPS.
- **World loading** began. The game showed loading artwork and read world assets.
- A **visible 3D scene** is the next milestone. It requires a rendered frame of the game world.
- **In-world controls** remain open. Verification requires movement and camera input.
- The **first mission** remains open. Verification requires playing the opening mission to completion.

</details>

## Measured changes

An XCL Series X replay captured a black frame after 150 seconds. GPU submissions continued and D3DMetal reported up to **16.8 GiB** of video memory.

Selecting the main display plane restored the Series S account screen and loading artwork. The last visible capture showed that artwork at 182 seconds. The title’s GPU watchdog triggered at 217 seconds while a compute shader was still in preparation.

Both late Series S compute shaders compiled offline and produced two D3DMetal pipelines. The warmed replay exited at a game assertion before it requested either pipeline. Its last capture still showed loading artwork.

| Measurement | Earlier | Later |
| --- | ---: | ---: |
| Shaders using fallback, same 723 variants | 88 | 4 |
| Failed game-data reads in two runs | 494 of 87,151 | 0 of 87,242 |
| Time to prepare the same two GPU pipelines offline | 25.1 s | 0.3 s with a warm cache |

<details>
<summary>Technical test history</summary>

| Area | What we measured | What we're testing |
| --- | --- | --- |
| Shader translation | Structured loops reduced fallback from 88 to 4 across the same 723 shader variants. Packed tables let both large compute pipelines finish on the Mac. The larger D3DMetal build took 42.6 seconds. | Trace the rendering wait that persists after both pipelines complete. [Structured loops](https://github.com/ivall/xcl/commit/b8b1f491ea5e075a82293f6ebefd8eceffc74de7) · [Packed tables](https://github.com/ivall/xcl/pull/1448) |
| Render scheduling | The Wait64 ordering regression passed on Windows WARP and CrossOver D3DMetal. With the fix disabled on WARP, the first copy timed out. In a 168-second offscreen run, the game drew black after the loading artwork and logged 2,962 PresentX calls in total. All 16 sampled pipeline builds and 16 sampled binds returned. | Capture the native queue calls at the world-load stall. [XCL ordering change](https://github.com/xcl-dev/xcl/pull/851) |
| Pipeline creation | In two cold CPU-only comparisons on the same three world-loading shaders, descriptor-heap memory windows reduced mean DXC compile time from 46.8 to 42.4 seconds and total DXIL size by 8.8%. | Measure D3DMetal's native pipeline build time separately. [XCL change](https://github.com/xcl-dev/xcl/pull/680) |
| Pipeline cache | In a generated compute benchmark, D3DMetal took about 5.1 seconds on the first creation and 2 to 3 ms in later processes. Precompiling three selected GTA VI compute pipelines took 44.5 seconds. The next game run logged 3,208 presents and 89,065 storage requests with zero reported storage failures. The last captured frame was black. | Compare driver compile times with descriptor-heap memory windows enabled and disabled in the same build. [Windows warm-cache result](https://github.com/xcl-dev/xcl/issues/534#issuecomment-7138554827) |
| World-load shaders | Five shader variants from the trace precompiled into D3DMetal pipelines in 18.8 seconds. The warmed run reached 3,498 PresentX calls and its last capture showed loading artwork. The later Rosetta-fixed run logged bind times of up to 19.6 seconds for graphics and 13.6 seconds for compute. | Identify which compile stages account for the late bind delays. |
| Late compute cache | Prepared six shaders offline in 18.9 seconds. A repeat loaded all six cached results in 0.1 seconds. The warmed offscreen game run still reached the watchdog at 167.0 seconds on loading artwork. A separate compute pipeline took 15.55 seconds for shader preparation and 13.3 ms for native creation during that run. | Cover more of the shaders requested during world loading. |
| Graphics shader preparation | In the warmed game run, a sampled pixel shader took 2.35 seconds to prepare. Native graphics pipeline creation stayed below 3.8 ms across the traced graphics pipelines. The paired offline precompiler filled two missing shader entries. A subsequent test reused all 22 cached shaders in a pack of 11 pairs from the trace. | Test the larger cache during another offscreen world load. |
| Pipeline preload priority | All 15 selected pipelines were ready before account selection in the offscreen game run. The prior 26.9 seconds of waits on those keys did not recur in the traced window. Cache contents and scheduling both changed. Five different graphics binds waited a combined 14.7 seconds. The last capture still showed loading artwork. | Retest with the additional five pipelines cached. |
| Guest semaphore publication | In the 20-pipeline run, five delayed guest values were written 21 to 145 ms after their native fences were observed complete. Submissions still stopped after those stores. | Check the later compute pipeline stalls. |
| Late compute pipelines | Two compute pipelines that previously stalled world loading were ready before account selection. In the latest replay they built in 90 ms and 84 ms. The preload worker built all 22 selected pipelines before account selection. | Check other pipelines requested during the first world render. |
| World-load memory | The earlier memory guard stopped the offscreen run at 169.2 seconds. The latest replay tracked 9,412 MiB of texture pages in use with no whole free texture heaps at its last memory sample. | Track texture residency through world loading. |
| Series S profile | Selecting the 4K display plane restored account selection and world loading. The run logged 80,222 storage requests with zero reported failures. A separate offline test prepared two late compute pipelines in 38.9 seconds. | Trace the game assertion that stopped the warmed replay before the pipelines were used. |
| macOS memory reporting | A title query treated about 255 GiB of reserved virtual address space as private usage. The corrected Series S query reported 5.6 GiB in use against an 8 GiB budget. An isolated CrossOver test verified reservation and resident-memory accounting. | Track usage during world loading. [Wine process counters](https://raw.githubusercontent.com/wine-mirror/wine/master/dlls/ntdll/unix/process.c) |
| Ray-tracing memory | In a synthetic D3DMetal test, a shader read both successive CPU writes through the coherent shadow. An opt-in build routed a 2,199 MiB retail allocation through the same path. The 194-second run logged the Rosetta float-to-half store error before GPU submissions stopped on loading artwork. | Test the replacement store during world loading. |
| DirectStorage | A focused CPU test reproduced a read starting before its destination page list was ready. The queue change passed the byte-for-byte check. A combined shader and storage build logged zero failures across 87,082 requests and still stopped on loading artwork. | Verify that the fix holds across repeated world loads. [Upstream queue fix](https://github.com/ivall/xcl/pull/549) |
| DirectStorage on D3DMetal | Fixed a valid fence being rejected. In a separate 64 KiB zlib test, an early-queued GPU command read stale bytes with shadow synchronization disabled and the correct bytes with it enabled. The retail test streamed assets, then Rosetta stopped at a float-to-half memory store. | Verify the first rendered world frame with the corrected memory path. |
| Rosetta float-to-half stores | The build replaced 70 stores, including the one that repeatedly stopped the title. Three CrossOver tests passed, including write-watch recovery across two pages. The offscreen retail run advanced beyond that failure and reached the game's GPU watchdog at 167.6 seconds. | Identify the GPU dependency that stalls world loading. |

</details>

## Xbox system checks

Three runs of XCL's synthetic test title returned 43, 44, and 43 passes out of 50. 43 checks passed in all three runs. One varied and six failed in all three.

| Check | Subsystem | Observed result |
| --- | --- | --- |
| 11 | Window handling | Windows reported that the console window was uncloaked. |
| 37 | DMA and title memory | The copy read the title's memory in one of three runs. |
| 38 | GPU command list | Reading back a bottom-of-pipe 32-bit write returned zero. |
| 39 | Sparse GPU memory | The GPU saw a stale value after a CPU write to a mapped buffer. |
| 40 | Coherent memory | Reading back two values from the write-back buffer returned zeros. |
| 41 | Sparse uploads | The first ring-buffer upload returned different bytes than expected. |
| 46 | DirectStorage | The read did not signal the test's D3D12 fence. |

## Mullion fallback

Mullion v0.5-alpha.4 ran in a separate CrossOver bottle. It passed 48 of 50 synthetic checks and let the GPU read XCL's imported host memory directly. After fixes for command-list creation and console render-target descriptors, the title advanced to black offscreen captures through frame 290. A Metal GPU write fault then caused device removal. [Mullion release](https://github.com/dttdrv/mullion/releases/tag/v0.5-alpha.4)

## Parallels fallback

The retail launcher read the game from a read-only SSD share in Windows 11 Arm. This VM exposed neither the required CPU instruction set nor the 32- or 64-lane shader waves required by XCL. Its WARP adapter reported 4-lane waves. The launch stopped at those checks.

## Reproduce the compatibility checks

Build XCL's synthetic Xbox Series test title from source and run it in the same bottle. Each test run gets fresh state because the fixture exercises file deletion. The process exits with the number of failed checks. Our clean runs exited with 6 or 7 failures, with one intermittent GPU-memory check accounting for the difference.

```sh
scripts/build.sh --test-title
scripts/run.sh --test-title
```

## Reproduce the TuxBox Lanes replay

Build Lanes from the pinned TuxBox revision and place `lanes.exe` and the original `MicrosoftGame.config` in their own directory. Use the TuxBox build requirements to produce the executable. ScarlettMac supplies the Xbox interfaces for this run. [TuxBox Lanes source and build guide](https://github.com/brcly/TuxBox/tree/3086e0b0451aafb7d74dac44b1ebf7786bea06d4/examples/lanes)

```sh
scripts/build.sh --lanes
scripts/run.sh --lanes /path/to/lanes/lanes.exe -- --replay
```

The replay runs without a window and reports `course=16/16 win=16/16 safe-miss=1 collision=1 frames=2 input=gameinput` on success. The Lanes build enables host compute and native committed buffers for this test.
