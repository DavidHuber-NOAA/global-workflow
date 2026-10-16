##################################
Tier 1: Production-only jobs (GFS)
##################################

Jobs available in the GFS system at this tier. A job may not appear in every configuration.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Job
     - Purpose
   * - ``wavegempak``
     - Create gempak files for wave grids
   * - ``waveawipsgridded``
     - Create AWIPS products for gridded wave output
   * - ``waveawipsbulls``
     - Create AWIPS products for wave bulletins
   * - ``postsnd``
     - Produce forecast model soundings at select locations
   * - ``fbwind``
     - Create aviation products for Hawai'i and other Pacific locations
   * - ``awips_20km_1p0deg``, ``awips``
     - Regrid forecasts to 20-km and 1-deg AWIPS grids
   * - ``npoess_pgrb2_0p5deg``
     - Generate grib files with simulated NPOESS variables
   * - ``gempak``
     - Converts atmosphere forecast output to gempak format
   * - ``gempakmeta``
     - Create gempak meta files for atmosphere gempak files
   * - ``gempakmetancdc``
     - Create gempak meta files for atmosphere gempak over North America
   * - ``gempakncdcupapgif``
     - Generate gempak skew-T diagrams
   * - ``gempakpgrb2spec``
     - Generate gempak files for simulated NPOESS products
