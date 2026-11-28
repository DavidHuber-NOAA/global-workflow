#####################################
UFS-MPAS Atmosphere (Experimental)
#####################################

========
Overview
========

The GFS can optionally use the Model for Prediction Across Scales (MPAS) dynamical core, coupled
to the CCPP physics inside the UFS Weather Model ("UFS-MPAS"), in place of FV3. This capability is
experimental and currently limited to:

* GFS forecast-only experiments with ``--app ATM``
* Cold starts from MPAS ``init_atmosphere`` initial conditions (no warm starts, restarts, or IAU)
* The 120 km quasi-uniform global mesh (``x1.40962``) with the ``MPAS_GFSv17`` CCPP suite and TEMPO
  microphysics, following the UFS ``control_gfs_mpas`` regression test
* Native MPAS output only; UPP and all downstream products (tracker, GEMPAK, AWIPS, etc.) are
  disabled

========
Building
========

UFS-MPAS is built from a separate UFS Weather Model checkout (``sorc/ufs_mpas_model.fd``) and is not
part of ``build_all.sh all``:

.. code-block:: bash

   git submodule update --init --recursive sorc/ufs_mpas_model.fd
   cd sorc
   ./build_all.sh gfs gfs_mpas
   ./link_workflow.sh

This produces ``exec/ufs_model_gfs_mpas.x``. Note that the UFS regression tests only build UFS-MPAS
with GNU compilers; ``build_ufs.sh -i gnu`` may be required.

=====================
Setting Up a Forecast
=====================

.. code-block:: bash

   ./setup_expt.py gfs forecast-only --atm_model mpas --app ATM --pslot my_mpas_run \
                --idate 2023031012 --edate 2023031012 --resdetatmos 96 \
                --icsdir /path/to/ics --comroot /path/to/com --expdir /path/to/exp

``--resdetatmos`` is only used for downstream bookkeeping; the MPAS mesh is set by ``MPAS_MESH`` in
``config.base``. The initial condition must be staged in ``ICSDIR`` as
``gfs.YYYYMMDD/HH/model/atmos/input/mpas_init.nc``.

=========
Fix Files
=========

The following MPAS-specific fix files are expected under ``${FIXglobal}/mpas`` (see ``mpas_ver``
in ``versions/fix.ver``):

* ``x1.40962/x1.40962.graph.info.part.<N>``: mesh decomposition for ``N`` atmosphere tasks
* ``x1.40962/constituents.xml`` (or ``constituents.xml``): tracer definitions consistent with the ICs
* ``physics/LANDUSE.TBL`` and ``physics/GENPARM.TBL``: MPAS land-use and soil parameter tables
* ``physics/tempo/*``: TEMPO microphysics lookup tables
* ``physics/thompson/*``: Thompson microphysics tables (only for ``imp_physics=8``)
* ``stream_list/MPAS_GFSv17/stream_list.atmosphere.{output,restart,diag_phys}``: optional output
  field lists; if absent, all fields are written

The physics fix files already used by FV3 (ozone/water vapor photochemistry, solar constant, surface
emissivity, CO2, MERRA2 aerosol climatology, aerosol optics, ``ugwp_limb_tau.nc``, and
``ccn_activate.bin``) are reused from ``am``, ``aer``, ``lut``, and ``ugwd``.

======
Output
======

Native MPAS files are copied to ``COMOUT_ATMOS_HISTORY`` as
``gfs.tHHz.mpas_history.fFFF.nc`` and ``gfs.tHHz.mpas_diag_phys.fFFF.nc``.
