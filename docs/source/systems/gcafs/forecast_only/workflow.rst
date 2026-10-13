############################
GCAFS forecast-only workflow
############################

The GCAFS forecast-only workflow includes these main tasks:

#. **stage_ic** - Stage initial conditions
#. **prep_emissions** - Prepare emissions data files
#. **aerosol_init** - Initialize aerosol fields
#. **fcst** - Run the UFS model with aerosols/chemistry
#. **atmos_prod** - Post-process atmosphere/aerosol output
#. **atmos_ensstat** - Ensemble mean and spread (only when ensemble members are run)
#. **arch_vrfy** and **arch_tars** - Archive verification data and create tarballs

The workflow is managed by the rocoto workflow manager, with tasks defined in the
``dev/workflow/rocoto/gcafs_tasks.py`` file.

For a list of descriptions for the jobs at this tier, see :doc:`job_descriptions`.
