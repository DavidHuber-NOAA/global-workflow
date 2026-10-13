#################################
Tier 2: Forecast-only jobs (GEFS)
#################################

Jobs available in the GEFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``stage_ic``
     - Stage initial conditions in COM
   * - ``gen_control_ic``
     - Regrid high-resolution analysis to serve as control member initial conditions
   * - ``prep_emissions``
     - Prepare emissions data as inputs for model
   * - ``waveinit``
     - Create wave model definition files
   * - ``atmos_prod``
     - Regrid atmosphere forecast grib files to lat-lon grids
   * - ``atmos_enstat``
     - Calculate ensemble mean and spread for atmosphere output
   * - ``ocean_prod``
     - Regrid ocean forecast
   * - ``ice_prod``
     - Regrid ice forecast
   * - ``wavepostsbs``
     - Create gridded wave output from forecast
   * - ``wave_stat``
     - Calculate ensemble mean and spread for gridded wave output
   * - ``wave_stat_pnt``
     - Calculate ensemble mean and spread for point wave output
   * - ``extractvars``
     - Filter out less important variables to reduce archival size
   * - ``arch_vrfy``
     - Archive select files from the deterministic model and cleans up older data
   * - ``arch_tars``
     - Back up the COM data structure
   * - ``cleanup``
     - Remove data from COM that is no longer needed
