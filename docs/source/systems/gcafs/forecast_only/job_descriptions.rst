##################################
Tier 2: Forecast-only jobs (GCAFS)
##################################

Jobs available in the GCAFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``stage_ic``
     - Stage initial conditions in COM
   * - ``prep_emissions``
     - Prepare emissions data as inputs for model
   * - ``aerosol_init``
     - Prepares aerosol inputs
   * - ``atmos_prod``
     - Regrid atmosphere forecast grib files to lat-lon grids
   * - ``atmos_enstat``
     - Calculate ensemble mean and spread for atmosphere output
   * - ``extractvars``
     - Filter out less important variables to reduce archival size
   * - ``arch_vrfy``
     - Archive select files from the deterministic model and cleans up older data
   * - ``arch_tars``
     - Back up the COM data structure
   * - ``cleanup``
     - Remove data from COM that is no longer needed
