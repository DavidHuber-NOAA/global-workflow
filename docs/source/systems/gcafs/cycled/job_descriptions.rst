#################################################
Tier 1.5: Data assimilation (cycled) jobs (GCAFS)
#################################################

Jobs available in the GCAFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``fetch``
     - Fetch initial conditions from HPSS
   * - ``prep``
     - Prepare atmosphere observations for DA
   * - ``analcalc``
     - Add the analysis increments to previous cycle's forecasts to produce atmospheric analysis files. Produces surface analysis file on Gaussian grid
   * - ``atmanlupp``
     - Create grib files on Gaussian grid for atmosphere analysis
   * - ``atmanlprod``
     - Regrid atmosphere analysis grib files to lat-lon grids
   * - ``anlstat``
     - Produce summary performance statistics for analysis
   * - ``atmanlvar``
     - Run JEDI-based atmosphere variational assimilation
   * - ``atmanlfv3inc``
     - Calculate JEDI-based atmosphere analysis increment
   * - ``atmanlfinal``
     - Complete JEDI-based atmosphere analysis by copying results back to COM
   * - ``aeroanlgenb``
     - Generate background error covariances for aerosol data assimilation
   * - ``aeroanlinit``
     - Initialize aerosol data assimilation (JEDI-based)
   * - ``aeroanlvar``
     - Run aerosol variational assimilation (JEDI-based)
   * - ``aeroanlfinal``
     - Complete aerosol analysis by copying results back to COM (JEDI-based)
   * - ``offlineanl``
     - Interpolate existing analysis to produce analysis increments
   * - ``goesupp``
     - Create grib files on Gaussian grid for special GOES variables for FAA
   * - ``metp``
     - Run forecast verification using MET-Plus
