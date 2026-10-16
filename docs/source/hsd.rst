.. _hsd_tiers:

######################################
Hierarchical System Design (HSD) Tiers
######################################

The global workflow supports several forecasting systems: GFS, GEFS, SFS and GCAFS. The
Hierarchical System Design (HSD) lets a subset of the repository be extracted for a given system
and capability level using `JOSH <https://josh-project.github.io/josh/>`_ (Just One Single History)
filters. The filter lists live in ``dev/hsd/``.

=====
Tiers
=====

.. list-table::
   :header-rows: 1
   :widths: 12 28 60

   * - Tier
     - Name
     - Contents
   * - 0
     - Full global workflow
     - Every forecasting system, every component, all documentation.
   * - 1
     - Individual forecasting system
     - Everything needed by one system (e.g., GCAFS), including data assimilation and
       production-only code. Other systems are removed.
   * - 1.5
     - System without production code
     - Tier 1 minus production-only code. Cycled experiments with data assimilation can still
       be run. Only defined for GFS and GCAFS.
   * - 2
     - System forecast-only
     - Tier 1.5 minus data assimilation. Forecasts are started from existing initial conditions.
       Defined for GFS, GEFS, SFS and GCAFS.

The tiers are strictly nested: each tier is a subset of the one above it.

==================================
Documentation layout and filtering
==================================

Documentation is organized so that a tier can be produced purely by deleting paths:

.. code-block:: text

   docs/source/
     user_guide/, contributor_guide/    Tier 0 material that applies to all systems
     tier0/                             Multi-system material (e.g., combined job table), removed at Tier 1+
     systems/<system>/index.rst         Tier 1 system overview
     systems/<system>/production/       Tier 1 only (production-only)
     systems/<system>/cycled/           Tier 1 and Tier 1.5 (data assimilation)
     systems/<system>/forecast_only/    Tier 1, 1.5 and 2

Every ``toctree`` that lists a variable set of pages uses a ``:glob:`` pattern so that removing a
directory does not break the build (Sphinx only warns that a glob matched nothing).

When adding documentation, place it in the lowest tier directory that needs it. Do not
reference a higher-tier page from a lower-tier page except through a glob toctree.
Each system's ``index.rst`` is a Tier 1 overview; it should stay brief and link to tier pages by glob.

The JOSH filters are described in ``dev/hsd/README.md``.

Adding a system
===============

Systems register themselves: the application, Rocoto XML, task and ecFlow factories in ``dev/workflow`` discover
modules by naming convention (``<system>*.py``), so a new system needs its own modules, a
``docs/source/systems/<system>/`` tree and a ``dev/hsd/<system>.tier*.list`` set, and no edits to shared Python code.
``dev/hsd/check_lists.py`` verifies that the lists are consistent with the repository.
