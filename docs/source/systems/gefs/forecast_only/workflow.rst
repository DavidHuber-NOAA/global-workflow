###########################
GEFS forecast-only workflow
###########################


GEFS consists of a control forecast based on the GFS analysis and a number of ensemble members based on members of the GFS EnKF ensemble. Jobs are substantial similar to a GFS forecast-only run, with additional jobs to calculate ensemble forecast mean and spread. Due to the vast amount of data produces by the ensemble, there is also an optional additional job to reduce the number of variables for archival purposes.

The workflow is managed by the rocoto workflow manager, with tasks defined in the
``dev/workflow/rocoto/gefs_tasks.py`` file.


For a list of descriptions for all jobs, see :doc:`job_descriptions`.
