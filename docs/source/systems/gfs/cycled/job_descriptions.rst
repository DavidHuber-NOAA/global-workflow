###############################################
Tier 1.5: Data assimilation (cycled) jobs (GFS)
###############################################

Jobs available in the GFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``fetchatmanlbias``
     - Fetch atmosphere observation bias from HPSS
   * - ``prep_sfc``
     - Prepare surface observations for DA
   * - ``prep``
     - Prepare atmosphere observations for DA
   * - ``prepatmanlbias``
     - Prepare atmosphere observation bias for DA
   * - ``anal``
     - Run GSI analysis for atmosphere
   * - ``analcalc``
     - Add the analysis increments to previous cycle's forecasts to produce atmospheric analysis files. Produces surface analysis file on Gaussian grid
   * - ``atmanlupp``
     - Create grib files on Gaussian grid for atmosphere analysis
   * - ``atmanlprod``
     - Regrid atmosphere analysis grib files to lat-lon grids
   * - ``eobs``
     - Data selection for EnKF update
   * - ``echgres``
     - Regrid forecast to ensemble resolution for EnKF recentering
   * - ``ecen``
     - Recenter ensemble around analysis
   * - ``eupd``
     - Perform EnKF update
   * - ``verfozn``
     - Extract and validate data for the ozone monitor DA package
   * - ``verfrad``
     - Extract and validate data for the radiation monitor DA package
   * - ``vminmon``
     - Extract and validate GSI normalization diagnostic
   * - ``fit2obs``
     - Verify analysis against observations
   * - ``anlstat``
     - Produce summary performance statistics for analysis
   * - ``atmanlvar``
     - Run JEDI-based atmosphere variational assimilation
   * - ``atmanlfv3inc``
     - Calculate JEDI-based atmosphere analysis increment
   * - ``atmanlfinal``
     - Complete JEDI-based atmosphere analysis by copying results back to COM
   * - ``atmensanlobs``
     - Data selection for EnKF update using JEDI
   * - ``atmensanlsol``
     - Run JEDI LETKF in solver mode
   * - ``atmensanlletkf``
     - Run JEDI-based LETKF
   * - ``atmensanlfv3inc``
     - Create FV3 ensemble increments (JEDI-based)
   * - ``atmensanlfinal``
     - Finalize JEDI-based analysis by copying outputs to COM
   * - ``ecen_fv3jedi``
     - Recenter ensemble around analysis using JEDI
   * - ``analcalc_fv3jedi``
     - Add the JEDI-based analysis increments to previous cycle's forecasts to produce atmospheric analysis files
   * - ``aeroanlgenb``
     - Generate background error covariances for aerosol data assimilation
   * - ``aeroanlinit``
     - Initialize aerosol data assimilation (JEDI-based)
   * - ``aeroanlvar``
     - Run aerosol variational assimilation (JEDI-based)
   * - ``aeroanlfinal``
     - Complete aerosol analysis by copying results back to COM (JEDI-based)
   * - ``prepoceanobs``
     - Prepare ocean observations for data assimilation (JEDI-based)
   * - ``marinebmatinit``
     - Initialize background error covariance for marine data assimilation (JEDI-based)
   * - ``marinebmat``
     - Update background error covariance for marine data assimilation (JEDI-based)
   * - ``marineanlinit``
     - Initialize marine data assimilation (JEDI-based)
   * - ``marineanlletkf``
     - Run LETKF phase of marine data assimilation (JEDI-based)
   * - ``marineanlvar``
     - Run variational phase of marine data assimilation (JEDI-based)
   * - ``marineanlecen``
     - Recenter ensemble around marine analysis (JEDI-based)
   * - ``marineanlchkpt``
     - Insert sea ice analysis into restart or creates MOM6 IAU increment
   * - ``marineanlfinal``
     - Complete marine analysis by copying results back to COM (JEDI-based)
   * - ``waveprep``
     - Prepares wave inputs
   * - ``metp``
     - Run forecast verification using MET-Plus
   * - ``earc_vrfy``
     - Archive grib files for ensemble mean verification
   * - ``earc_tars``
     - Archive ensemble member restarts into tarballs
