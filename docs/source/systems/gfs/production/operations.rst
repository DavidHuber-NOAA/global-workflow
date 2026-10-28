####################################
GFS experimental vs operational runs
####################################

Experimental run is different from operational runs in the following ways:

* **Workflow manager**:

  - Operations use `ecFlow <https://www.ecmwf.int/en/learning/training/introduction-ecmwf-job-scheduler-ecflow>`__, whereas development use `rocoto <https://github.com/christopherwharrop/rocoto/wiki/documentation>`__.

.. note::

   Experiments can also be run with ecFlow if the platform has an ecFlow server.

* **Dump step**:

  - Not run in experiments but in real-time production. Dump data already exists in GDA on supported platforms.

* **Additional steps** in experimental mode:

  - **arch_vrfy**
  - **arch_tars**
  - **cleanup**

^^^^^^^^^^^^^^^^^^^
For New Users
^^^^^^^^^^^^^^^^^^^
.. note::

  - Operational systems include many additional downstream jobs that are not run in development mode.
  - The workflow manager (rocoto or ecFlow) determines job dependencies and ensures each job runs only when its prerequisites are complete.
  - The exact job list for your experiment is defined in the workflow XML (rocoto) or suite definition (ecFlow)
