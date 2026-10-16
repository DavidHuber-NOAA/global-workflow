#####################################
GFS configuration and output products
#####################################

.. _gfs_config_files:

===================
Configuration Files
===================

GFS configuration is primarily managed through the config files in the ``dev/parm/config/gfs`` directory. Core settings and those related to job flow are located in ``config.base``, with the most common settings additionally parameterized to be filled in at experiment creation time. Job resources (cores, memory, etc.) are defined in ``config.resources`` with machine-specific overrides in the corresponding version for the machine. Beyond those, each job (or class of jobs) has its own config file for that job's settings.

===============
Output Products
===============

* Early and late analysis at model resolution
* EnKF ensemble to provide background errors and initial conditions for GEFS
* Data assimilation verification diagnostics
* grib2 gridded atmosphere forecast on various grids
* forecast model soundings
* NetCDF marine gridded forecast
* wave gridded and point forecasts
* MET-plus-based forecast verification
