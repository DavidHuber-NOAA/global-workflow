# Cycle-Specific Forecast Lengths for GFS

## Overview

This feature allows the Global Forecast System (GFS) to run different forecast cycles (00z, 06z, 12z, 18z) to different output lengths. This helps save compute time by running shorter forecasts for some cycles while maintaining longer forecasts for others.

## Configuration

To enable cycle-specific forecast lengths, add the following parameters to your configuration YAML file (e.g., `dev/parm/config/gfs/yaml/defaults.yaml`):

```yaml
base:
  FHMAX_GFS_00: 384  # 16 days for 00z cycle
  FHMAX_GFS_06: 180  # 7.5 days for 06z cycle
  FHMAX_GFS_12: 384  # 16 days for 12z cycle
  FHMAX_GFS_18: 180  # 7.5 days for 18z cycle
```

These values override the default `FHMAX_GFS` for their respective cycles.

## How It Works

### Cycledef Generation

When cycle-specific FHMAX values are defined, the workflow generates separate Rocoto cycledefs for each cycle:
- `gfs_00` - Runs at 00z
- `gfs_06` - Runs at 06z
- `gfs_12` - Runs at 12z
- `gfs_18` - Runs at 18z

The standard `gfs` cycledef is still generated for compatibility.

### Task Generation

Tasks that depend on forecast length automatically detect cycle-specific FHMAX values:

- **Product Generation Tasks** (atmos_prod, ocean_prod, ice_prod):
  - When FHMAX values differ across cycles, separate metatasks are created
  - Example: `gfs_atmos_prod_00`, `gfs_atmos_prod_06`, etc.
  - Each metatask runs only for its designated cycle with appropriate forecast hours

- **UPP Tasks** (atmupp, goesupp):
  - Similar behavior to product tasks
  - Cycle-specific versions created when needed

### Backward Compatibility

When cycle-specific FHMAX values are not defined or are all the same, the system uses the standard implementation with a single metatask, maintaining full backward compatibility.

## Example: Operational-like Setup

16-day forecasts for synoptic cycles (00z, 12z) and 7.5-day forecasts for intermediate cycles (06z, 18z):

```yaml
base:
  INTERVAL_GFS: 6      # Run GFS every 6 hours
  FHMAX_GFS: 120       # Default fallback (5 days)
  FHMAX_HF_GFS: 48     # High-frequency output to 48 hours
  FHMAX_GFS_00: 384    # 16 days for 00z
  FHMAX_GFS_06: 180    # 7.5 days for 06z
  FHMAX_GFS_12: 384    # 16 days for 12z
  FHMAX_GFS_18: 180    # 7.5 days for 18z
```

## Implementation Details

### Code Locations

- **Configuration**: `dev/parm/config/gfs/yaml/defaults.yaml`
- **Cycledef Generation**: `dev/workflow/rocoto/gfs_cycled_xml.py`
- **Forecast Hour Utilities**: `dev/workflow/rocoto/tasks.py`
- **Task Generation**: `dev/workflow/rocoto/gfs_tasks.py`

### Forecast Hour Calculation

For each cycle, forecast hours are determined by:
1. Check if `FHMAX_GFS_<cyc>` exists in configuration
2. If yes, use that value; otherwise fall back to `FHMAX_GFS`
3. Generate forecast hour list using high-frequency and standard intervals

Example for 00z with FHMAX_GFS_00 = 384:
- Hours 0-48: Every 3 hours (high-frequency)
- Hours 48-384: Every 6 hours (standard)
- Total: 73 forecast hours

Example for 06z with FHMAX_GFS_06 = 180:
- Hours 0-48: Every 3 hours (high-frequency)
- Hours 48-180: Every 6 hours (standard)
- Total: 39 forecast hours
