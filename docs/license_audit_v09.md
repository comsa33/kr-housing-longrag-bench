# Source License Audit (for one-download redistribution decision)

Goal: determine which of the 20 manifest sources may be redistributed so the
benchmark can ship as a single "download-and-run" package (data + reconstructed
context bundles + code) instead of requiring domestic-only reconstruction. The
final legal call rests with the authors/institution; this file records the
observable license evidence.

## Verified redistributable (live-checked 2026-07-11)

| Source(s) | Basis | Evidence |
|---|---|---|
| `lh-sale-announcements` (data.go.kr 15112255) | 공공데이터 | page shows **이용허락범위 제한 없음** (live fetch) |
| `lh-third-new-town-...` (15088432) | 공공데이터 | **이용허락범위 제한 없음** (live fetch) |
| `hug-sale-history` (15057686) | 공공데이터 | **이용허락범위 제한 없음** (live fetch) |
| `molit-apt-trade-detail` (15126468) | 공공데이터 | **이용허락범위 제한 없음** (live fetch) |
| `molit-apt-official-price` (3073746) | 공공데이터 | data.go.kr fileData entry (re-confirm marking) |
| `law-*` (3 statutes) | 저작권법 제7조 | laws/ordinances/rules excluded from copyright |
| `kogl-license-guide`, `public-data-portal-use-policy` | policy reference | official policy pages |

→ Public data (data.go.kr, "제한 없음"), statutes (Art. 7), and policy refs are
redistributable. Note the government itself registered an **LH announcement
dataset** (15112255) as open data with no restriction.

## Needs one confirmation

`lh-sale-announcements-v04` and the 10 provider-announcement sources
(`sh/gh/ih/jpdc/bmc/cbdc/dgdc/dtco/gjuco-announcements`) are the actual
announcement documents fetched from each provider's apply portal, currently
labelled `public_official_announcement_internal_use` ("official-notice posture,
raw kept internal" — a conservative choice, not a stated legal bar).

Two open points for the authors:
1. **Is data.go.kr `15112255` (fileData, "제한 없음") the same content as the raw
   apply.lh.or.kr PDFs?** If yes, the LH announcement files are themselves open
   data. (Check what 15112255 actually serves — 5 min.)
2. **제7조 scope:** Article 7 covers 국가/지방자치단체 고시·공고. LH and the
   지방공사 are 공공기관/지방공사, not strictly 국가/지자체, so Art. 7 is not a
   clean fit; their works more likely fall under 공공누리(KOGL). Confirm each
   provider portal's 공공누리 marking.

## Redistribution posture that sidesteps the risk

Ship the **extracted-text context bundles**, not the raw PDF/HWP binaries:
- The bundles carry extracted official-notice text + open public-data tables +
  statutory text — the parts the benchmark actually uses.
- Raw PDFs may embed third-party media (renderings, photos, maps) whose
  copyright is separate from the notice text; shipping extracted text avoids
  that exposure.
- This keeps "we do not redistribute the raw source binaries" true while making
  the runnable context openly available.

## Recommendation

- **Public release / camera-ready:** ship data + extracted-text bundles + code as
  one HF/Zenodo package (download-and-run); keep raw PDFs un-redistributed.
- **Review:** provide the same bundle package via an anonymized link (e.g. OSF
  anonymized view) so foreign reviewers—who cannot obtain data.go.kr/HUG keys or
  reach the domestic portals—can reproduce without reconstruction.
- **Reconstruction code** remains the path for domestic/key-holding users who
  want to rebuild from primary sources.
