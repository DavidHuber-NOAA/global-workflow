########################################
Running a GCAFS forecast-only experiment
########################################

GCAFS can be run using the global-workflow framework. To set up a free-forecast GCAFS experiment:

.. code-block:: bash

   ./setup_expt.py gcafs forecast-only --pslot my_gcafs_run --app ATMA \
                --idate 2023010100 --edate 2023010100 \
                --resdetatmos 384 --comroot /path/to/com --expdir /path/to/exp

Configuration is managed through the standard global-workflow configuration files. GCAFS-specific
settings are documented in :doc:`configuration`.

After setting up the experiment, build the workflow XML and launch it:

.. code-block:: bash

   ./setup_workflow.py /path/to/exp/my_gcafs_run
   cd /path/to/exp/my_gcafs_run
   rocotorun -w gcafs.xml -d gcafs.db
