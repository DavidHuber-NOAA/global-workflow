################################
Tier 2: Forecast-only jobs (GFS)
################################

Jobs available in the GFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``fetch``
     - Fetch initial conditions from HPSS
   * - ``stage_ic``
     - Stage initial conditions in COM
   * - ``aerosol_init``
     - Prepares aerosol inputs
   * - ``waveinit``
     - Create wave model definition files
   * - ``goesupp``
     - Create grib files on Gaussian grid for special GOES variables for FAA
   * - ``atmos_prod``
     - Regrid atmosphere forecast grib files to lat-lon grids
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
   * - ``tracker``
     - Run tropical cyclone tracker on forecast
   * - ``genesis``
     - Run tropical cyclone genesis
   * - ``genesis_fsu``
     - Run tropical cyclone genesis using FSU method
   * - ``arch_vrfy``
     - Archive select files from the deterministic model and cleans up older data
   * - ``arch_tars``
     - Back up the COM data structure
   * - ``cleanup``
     - Remove data from COM that is no longer needed
