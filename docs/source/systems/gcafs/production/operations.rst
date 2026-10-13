########################
GCAFS production support
########################

Production-only components of GCAFS are:

* The ecFlow suite definition and job scripts in ``dev/ecf/gcafs``
* NCO packaging and EE2 link tools: ``dev/ush/setup_gcafs_for_nco.py``,
  ``dev/ush/make_ee2_links.sh`` and ``dev/ush/global_net_converter.py``
* The GDAS fetch helper ``dev/ush/fetch_gdas_for_gcafs.sh``

These are removed from the Tier 1.5 and Tier 2 views of the repository.
