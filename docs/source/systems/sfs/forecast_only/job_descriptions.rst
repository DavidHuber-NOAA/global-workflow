################################
Tier 2: Forecast-only jobs (SFS)
################################

Jobs available in the SFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
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
   * - ``wavepostpnt``
     - Create wave forecast output and bulletins at specific points (e.g. buoys)
   * - ``wavepostbndpnt``
     - Create wave forecast output at specific points in boundary waters
   * - ``wavepostbndpntbll``
     - Create bulletins for wave forecast output in boundary waters
   * - ``arch_vrfy``
     - Archive select files from the deterministic model and cleans up older data
   * - ``arch_tars``
     - Back up the COM data structure
   * - ``cleanup``
     - Remove data from COM that is no longer needed
