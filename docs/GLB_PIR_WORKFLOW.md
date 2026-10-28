Historical specification at source commit4dca5f9b. [Current setup](setup.md) and [release status](../RELEASE-STATUS.md) record this derivative’s verified scope.

## GLB PIR Workflow

This workflow converts a mesh-only GLB into a conservative IndoorGML-lite PIR payload
and renders it in a viewer similar to the original IndoorGML demo.

### Why This Exists

The GLB is treated as the canonical geometry container. We attach a PIR-style
semantic graph (rooms, walls, openings) to it so downstream pricing and delta
logic can reference **one** source instead of many images.

### What This Does

- Reads GLB geometry and extracts vertex positions
- Infers a single-room envelope from the mesh bounding box
- Produces IndoorGML-lite JSON (PIR payload)
- Optionally embeds the payload back into the GLB `extras`
- Generates a viewer HTML with the PIR embedded

### Scripts

1) Build PIR from GLB:
```
python3 lean-mvp/backend/scripts/glb_pir_builder.py \
  --glb /root/puedo_casa/docs/reference/scene.glb \
  --out-dir /root/puedo_casa/docs/reference/glb_pir \
  --embed-glb \
  --embed-viewer
```

2) Embed PIR into viewer (standalone):
```
python3 lean-mvp/backend/scripts/embed_glb_pir_viewer.py \
  --pir-json /root/puedo_casa/docs/reference/glb_pir/glb_pir.json \
  --output /root/puedo_casa/docs/reference/glb_pir/glb_pir_viewer.html
```

### Outputs

- `glb_pir.json`: IndoorGML-lite PIR payload (single-room, conservative)
- `glb_pir_meta.json`: bbox + axis inference metadata
- `scene_with_pir.glb`: GLB with embedded PIR in `extras` (if enabled)
- `glb_pir_viewer.html`: Viewer with embedded PIR (if enabled)

### Notes

- This is a **low-confidence** starting point (single room, no openings).
- It is meant to replace image clustering as the canonical reference, not to
  solve full semantic segmentation.
- Further room segmentation can be added later using plane clustering and
  spatial partitioning.
