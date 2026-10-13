##########################
GFS forecast-only workflow
##########################

A forecast-only GFS run starts from existing initial conditions and runs the ``fetch`` (optional),
``stage_ic``, ``fcst`` and post-processing jobs, with optional wave, ocean and ice products, followed
by the experiment-mode ``arch_vrfy``, ``arch_tars`` and ``cleanup`` jobs.

In development, the workflow is managed by the rocoto workflow manager, with tasks defined in the
``dev/workflow/rocoto/gfs_tasks.py`` file.

For a list of descriptions for the jobs at this tier, see :doc:`job_descriptions`.
