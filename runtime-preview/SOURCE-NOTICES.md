# Source notices

The preview patches, build script, and launcher are distributed under GPL-3.0-or-later. Each recipe reconstructs its complete corresponding source and keeps the upstream notices. See [LICENSE](LICENSE).

| Recipe | Pinned VIctory-macOS source and patches | Reconstruct source |
| --- | --- | --- |
| Default | [23ff1f7](https://github.com/pragyaangaur/VIctory-macOS/commit/23ff1f7540952533b283d996a4f3f6710a6f6e85), [patch series](patches/series) | `./build.sh --prepare NEW_SOURCE_DIR` |
| November 26 checkpoint | [bf99e72](https://github.com/pragyaangaur/VIctory-macOS/commit/bf99e728b2fa89c3550d51e07626c0da9bd6ec47), [patch series](checkpoint/patches/series) | `./build.sh --checkpoint --prepare NEW_SOURCE_DIR` |
| November 27 performance | [8616bd6](https://github.com/halfwave50/VIctory-macOS-halfwave/commit/8616bd67939a0a659dc50b02b52a291c73a73859) of halfwave50's VIctory-macOS fork, [patch series](perf/patches/series) | `./build.sh --perf --prepare NEW_SOURCE_DIR` |

The default and checkpoint recipes carry the ScarlettMac display-name changes. The checkpoint also carries local picker and GameInput changes. Its mesh output limits and submission wait diagnostics are adapted from derz92’s upstream changes. The queue wait ordering fix comes from Kolkka. [Mesh limits PR #282](https://github.com/pragyaangaur/VIctory-macOS/pull/282) · [Submission diagnostics PR #283](https://github.com/pragyaangaur/VIctory-macOS/pull/283) · [Queue wait order PR #434](https://github.com/pragyaangaur/VIctory-macOS/pull/434)

Two shader patches port Belobug's wave32 work: [tiled cascade shadows on wave32](https://github.com/Belobug/VIctory-Belobug-AMD/commit/0cb13721b238fb9c94fcab287c45bcd666d0530d) and [LDS flag regions](https://github.com/Belobug/VIctory-Belobug-AMD/commit/a5e42338703c062c368b271b5f81fe21081dc563).

The performance recipe builds on [halfwave50's fork](https://github.com/halfwave50/VIctory-macOS-halfwave) of VIctory-macOS, GPL-3.0-or-later. Its patch adds the memory, DirectStorage, write-fault and shader changes described in [BUILD.md](BUILD.md#november-27-performance-recipe).

VIctory-macOS builds on [Marvisak's VIctory](https://github.com/Marvisak/VIctory). Its repository ships a BCPack format table under its [asset policy](https://github.com/pragyaangaur/VIctory-macOS/blob/23ff1f7540952533b283d996a4f3f6710a6f6e85/docs/asset-policy.md). The table is supplied by the pinned upstream checkout. Its Microsoft silicon-rans attribution is recorded separately in [LICENSE-silicon-rans](LICENSE-silicon-rans).

Wine, Apple's D3DMetal, the compiler toolchain, and any game files are supplied separately by their users.
