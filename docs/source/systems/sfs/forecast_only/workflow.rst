##########################
SFS forecast-only workflow
##########################


The SFS is planned to have its own data assimilation system that mirrors that of GFS. The resulting workflow will be a mixture of that of GFS, with a DA portion, and GEFS, with a full-length ensemble forecast. For now, only a forecast-only version is available.

The workflow is managed by the rocoto workflow manager, with tasks defined in the
``dev/workflow/rocoto/sfs_tasks.py`` file.


For a list of descriptions for all jobs, see :doc:`job_descriptions`.
