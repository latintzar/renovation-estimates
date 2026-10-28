Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

# Cluster Panorama Pipeline (M2) — ARCHIVED

**Status:** Archived — panoramas were removed from the pipeline (quality + reliability reasons).

This document remains only as historical context for prior experimentation. The current pipeline does **not** generate, store, or consume cluster panoramas.

This step used to generate one panorama per room cluster and save a manifest to `unified_estimates` under `cluster_panos_v1`.

## Why this exists

The panorama becomes a single "room image" that is:
- easier to reason about than multiple photos
- stable for downstream PIR / delta / image-gen
- anchored to a specific room cluster

## What it does

1. Loads room clusters for a listing (`photo_clusters`)
2. Downloads cluster images
3. Runs DA3 (high-res, no 3DGS) to get `predictions.npz`
4. Renders the tuned panorama (`seam2tune` settings)
5. Writes manifest to disk and DB

## Output

File system:
- `docs/reference/cluster_panos/listing_{listing_id}/{cluster_id}/panorama.jpg`
- `docs/reference/cluster_panos/listing_{listing_id}/cluster_panos_manifest.json`

Database:
- `unified_estimates.package_type = "cluster_panos_v1"`

## Pipeline hook (historical)

The job type used to be `generate_cluster_panos`. This job is no longer enqueued by the pipeline.

To enqueue manually (historical; no longer supported):
```
(removed) scripts/run_cluster_panos.py <listing_id>
```

To run through the pipeline queue, enqueue a run and let the worker pick it up.

## Settings (current default)

```
width=2048
height=1024
stride=1
blend_px=16
seam_band_px=3
edge_protect_percentile=92
mask_smooth_ksize=5
seam_mode=straight_only
seam_force_global_col=true
overlap_winner_takes_all=true
```

## Notes

- DA3 `high_res` needs 4xL4 or similar GPU.
- GS is disabled for stability (not required for panoramas).
