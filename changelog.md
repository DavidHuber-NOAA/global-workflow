# Changelog

## [Unreleased] - 2026-11-28

### Added
- Experimental UFS-MPAS atmosphere option for GFS forecast-only experiments (`setup_expt.py gfs forecast-only --atm_model mpas`).
  - New `sorc/ufs_mpas_model.fd` submodule (dustinswales/ufs-weather-model `feature/phys2dyn`) and `gfs_mpas` build (`exec/ufs_model_gfs_mpas.x`), excluded from `build_all.sh all`.
  - `build_ufs.sh` options `-c` (CCPP suites), `-s` (source directory), and `-i` (compiler).
  - `ush/forecast_mpas.sh` with `MPAS_predet`, `MPAS_det`, `MPAS_postdet`, `MPAS_nml`, and `MPAS_out`.
  - `parm/ufs/mpas/input_gfs.nml.IN` and `model_configure.IN` based on the UFS `control_gfs_mpas` regression test (120 km mesh `x1.40962`, `MPAS_GFSv17`, TEMPO microphysics).
  - `ATM_MODEL` and `MPAS_MESH` settings in `config.base`, an `--mpas` option in `config.ufs`, and MPAS IC staging (`parm/stage/atmosphere_mpas_cold.yaml.j2`).
  - Atmospheric post-processing and downstream tasks are skipped for MPAS; archive and cleanup depend on the forecast.
  - User guide page `docs/source/user_guide/ufs_mpas.rst`.
