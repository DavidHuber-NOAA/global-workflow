#################################
Running a cycled GCAFS experiment
#################################

GCAFS can be run in 'cycled' mode. The meteorological analysis in cycled mode is taken
from the GDAS (either from an HPSS archive or a location stored on disk) using the ``fetch``,
``stage_ic`` and ``offlineanl`` tasks. The aerosol analysis is optional and controlled by setting
``USE_AERO_ANL`` to "YES".

The cycled workflow has two runs: ``gcdas`` (the cycling run, which performs the analysis and
forecast needed to continue the cycle) and ``gcafs`` (the product forecast run). The ``gcdas``
run executes, in order: ``stage_ic``, ``fetch``, ``offlineanl``, ``sfcanl_gcycle``, the aerosol
analysis tasks (``aeroanlgenb``, ``aeroanlinit``, ``aeroanlvar``, ``aeroanlfinal``), ``prep``,
``analcalc``, ``atmanlupp``, ``atmanlprod``, ``anlstat``, ``prep_emissions``, ``fcst``, ``atmupp``,
``atmos_prod``, ``arch_vrfy``, ``arch_tars`` and ``cleanup``. The ``gcafs`` run executes the
forecast and product tasks, plus the optional ``goesupp`` and ``metp`` tasks.

.. note::

   Hybrid ensemble variational assimilation (Hyb-Var) is not yet supported for GCAFS.

For a list of descriptions for the jobs at this tier, see :doc:`job_descriptions`.
