A project for object dimension measurement from point clouds captured by an Orbbec depth camera or loaded from saved `.npz` files.
 
## What the project does
 
- Detects a support plane (table/floor) in a point cloud.
- Extracts the target object relative to that plane.
- Computes `Length`, `Width`, and `Height` (upright) in millimeters.
- Returns intermediate cloud layers for visualization (`raw`, `downsampled`, `table`, `filtered`, `object`).
 
## Current features
 

- `CLI` mode: run from Orbbec camera input.
- `CLI` mode: replay from `.npz` (directory or single file).
- `GUI` mode (PySide6): real-time point cloud visualization.
- `GUI` mode (PySide6): processing layer switcher.
- `GUI` mode (PySide6): algorithm parameter editing, reset, and save to `src/config.py`.
- `GUI` mode (PySide6): `USE` mode supports averaging over multiple frames.
- Data recording utility: save point clouds to `.npz` via `src/utility/point_data_record.py`.
- Data recording utility: custom output file name via `--name`.
 

## Quick start
 

## Roadmap

### Done

- [x] Core point-cloud pipeline for upright dimensions.
- [x] CLI support for camera and `.npz` replay.
- [x] GUI with real-time visualization and layer selection.
- [x] Runtime parameter editing and saving to `src/config.py`.
- [x] Multi-frame averaging for measurements in `USE` mode.
- [x] Point-cloud recording utility with custom output name.

### Future

- [ ] Improve robustness for severe occlusion and large object dominance.
- [ ] Add features to create a point cloud from a depth frame with the known intrinsics
- [ ] Add data recording in the GUI
- [ ] Improve robustness with big objects
 
## Validation table
 
| Object | Ground truth | Measurments | Difference |
|---|---|---|---|