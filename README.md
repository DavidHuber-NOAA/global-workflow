[![Read The Docs Status](https://readthedocs.org/projects/global-workflow/badge/?badge=latest)](http://global-workflow.readthedocs.io/)
[![shellnorms](https://github.com/NOAA-EMC/global-workflow/actions/workflows/linters.yaml/badge.svg)](https://github.com/NOAA-EMC/global-workflow/actions/workflows/linters.yaml)
[![pynorms](https://github.com/NOAA-EMC/global-workflow/actions/workflows/pynorms.yaml/badge.svg)](https://github.com/NOAA-EMC/global-workflow/actions/workflows/pynorms.yaml)

![Custom badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/emcbot/e35aa2904a54deae6bbb1fdc2d960c71/raw/hera.json)
![Custom badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/emcbot/e35aa2904a54deae6bbb1fdc2d960c71/raw/orion.json)

# global-workflow
Global Workflow currently supporting the Global Forecast System (GFS) with the [UFS-weather-model](https://github.com/ufs-community/ufs-weather-model) and [GSI](https://github.com/NOAA-EMC/GSI)-based Data Assimilation System.

The `global-workflow` depends on the following prerequisities to be available on the system:

* Workflow Engine - [Rocoto](https://github.com/christopherwharrop/rocoto) and [ecFlow](https://github.com/ecmwf/ecflow) (for NWS Operations)
* Compiler - Intel Compiler Suite
* Software - NCEPLIBS (various), ESMF, HDF5, NetCDF, and a host of other softwares (see module files under /modulefiles for additional details)

The `global-workflow` currently supports the following machines at the indicated tier.

| HPC            | Tier | Notes                                      |
| -------------- |:----:|:------------------------------------------:|
| WCOSS2         | 1    | GEFS testing is not regularly performed.   |
| NCO            |      | GFS weakly coupled DA is not currently     |
|                |      | supported.                                 |
| -------------- |:----:|:------------------------------------------:|
| Hera           | 1    |                                            |
| NOAA RDHPCS    |      |                                            |
| -------------- |:----:|:------------------------------------------:|
| Hercules       | 1    | Currently does not support the TC Tracker. |
| MSU            |      |                                            |
| -------------- |:----:|:------------------------------------------:|
| Orion          | 2    | The GSI runs very slowly on Orion.         |
| MSU            |      |                                            |
| -------------- |:----:|:------------------------------------------:|
| Gaea C5/C6     | 3    | Currently non-operational following an OS  |
| RDHPCS         |      | upgrade.  Supported by EPIC.               |
| -------------- |:----:|:------------------------------------------:|
| Jet            | 3    | Supported by NESDIS.  Supports GSI-based   |
| RDHPCS         |      | DA only.                                   |
| -------------- |:----:|:------------------------------------------:|
| S4             | 3    | Currently non-operational following an OS  |
| U of Wisc/SSEC |      | upgrade.  Supported by NESDIS.  Supports   |
|                |      | GSI-based DA only.                         |
| -------------- |:----:|:------------------------------------------:|
| AWS, GCP, Azure| 3    | Supported by EPIC.                         |
| NOAA Parallel  |      |                                            |
| Works          |      |                                            |
| -------------- |:----:|:------------------------------------------:|

Tier Definitions
----------------

1. Fully supported by the EMC global workflow team.  CI testing is regularly performed on these systems, the majority of the global workflow features are supported, and the team will address any platform-specific features, bugs, upgrades, and requests for data.
2. Supported by the global workflow team on an ad-hoc basis.  CI tests are supported on these systems, but not regularly performed.
3. No official support by the global workflow team, but may be supported by other entities (e.g. EPIC).

Documentation (in progress) is available [here](https://global-workflow.readthedocs.io/en/latest/).

# Disclaimer

The United States Department of Commerce (DOC) GitHub project code is provided
on an "as is" basis and the user assumes responsibility for its use. DOC has
relinquished control of the information and no longer has responsibility to
protect the integrity, confidentiality, or availability of the information. Any
claims against the Department of Commerce stemming from the use of its GitHub
project will be governed by all applicable Federal law. Any reference to
specific commercial products, processes, or services by service mark,
trademark, manufacturer, or otherwise, does not constitute or imply their
endorsement, recommendation or favoring by the Department of Commerce. The
Department of Commerce seal and logo, or the seal and logo of a DOC bureau,
shall not be used in any manner to imply endorsement of any commercial product
or activity by DOC or the United States Government.

