#! /usr/bin/env bash

#===============================================================================
#
#   FILE: forecast_mpas.sh
#
#   DESCRIPTION: Functions for the UFS-MPAS atmosphere (MPAS dynamical core with
#                CCPP physics inside the UFS Weather Model).  These replace the
#                FV3_* functions in forecast_fv3.sh when ATM_MODEL=mpas.
#
#                UFS-MPAS support is experimental and currently limited to
#                cold-started, atmosphere-only forecasts (no restarts, no IAU,
#                no inline post or write grid component).
#
#   Fix files (FIXmpas=${FIXglobal}/mpas):
#     ${FIXmpas}/${MPAS_MESH}/${MPAS_MESH}.graph.info.part.<ATMPETS>  mesh partition
#     ${FIXmpas}/${MPAS_MESH}/constituents.xml (or ${FIXmpas}/constituents.xml)
#     ${FIXmpas}/physics/LANDUSE.TBL, ${FIXmpas}/physics/GENPARM.TBL
#     ${FIXmpas}/physics/tempo/* (TEMPO microphysics lookup tables; imp_physics=88)
#     ${FIXmpas}/physics/thompson/* (Thompson microphysics tables; imp_physics=8)
#     ${FIXmpas}/stream_list/${CCPP_SUITE}/stream_list.atmosphere.* (optional)
#   Initial conditions (from MPAS init_atmosphere):
#     ${COMIN_ATMOS_INPUT}/mpas_init.nc
#
#===============================================================================

# Disable variable not used warnings
# shellcheck disable=SC2034
MPAS_predet() {
    echo "SUB ${FUNCNAME[0]}: Defining variables for UFS-MPAS"

    if [[ ! -d "${COMOUT_ATMOS_HISTORY}" ]]; then mkdir -p "${COMOUT_ATMOS_HISTORY}"; fi

    FIXmpas=${FIXmpas:-"${FIXglobal}/mpas"}
    MPAS_MESH=${MPAS_MESH:-"x1.40962"}

    # Physics/namelist settings
    blocksize=${blocksize:-32}
    dycore_only=${dycore_only:-".false."}
    FHZERO=${FHZERO:-6}
    FHCYC=0 # Surface cycling is not available with MPAS
    IAER=${IAER:-1011}
    cdmbgwd=${cdmbgwd:-"0.14,1.8,1.0,1.0"}
    mpas_phys_diag=${mpas_phys_diag:-".true."}
    mpas_pio_num_iotasks=${mpas_pio_num_iotasks:-${ATMPETS}}
    mpas_graph_prefix="graph.info.part."
    mpas_ic_filename="mpas_init.nc"
    mpas_oro_filename="none" # Orographic GWD statistics are read from the initial conditions

    # Output and restart frequency (output_fh "<freq> -1" writes every <freq> hours)
    MPAS_OUTPUT_FH="${FHOUT} -1"
    MPAS_RESTART_FH="${FHMAX}"

    # Fix files shared with FV3 (same CCPP physics)
    cpreq "${FIXugwd}/ugwp_limb_tau.nc" "${DATA}/ugwp_limb_tau.nc"

    local O3FORC H2OFORC
    if [[ "${new_o3forc:-YES}" == "YES" ]]; then
        O3FORC="ozprdlos_2015_new_sbuvO3_tclm15_nuchem.f77"
    else
        O3FORC="global_o3prdlos.f77"
    fi
    H2OFORC=${H2OFORC:-"global_h2o_pltc.f77"}
    cpreq "${FIXglobal}/am/${O3FORC}" "${DATA}/global_o3prdlos.f77"
    cpreq "${FIXglobal}/am/${H2OFORC}" "${DATA}/global_h2oprdlos.f77"

    cpreq "${FIXglobal}/am/global_solarconstant_noaa_an.txt" "${DATA}/solarconstant_noaa_an.txt"
    cpreq "${FIXglobal}/am/global_sfc_emissivity_idx.txt" "${DATA}/sfc_emissivity_idx.txt"
    cpreq "${FIXglobal}/am/global_co2historicaldata_glob.txt" "${DATA}/co2historicaldata_glob.txt"
    cpreq "${FIXglobal}/am/co2monthlycyc.txt" "${DATA}/co2monthlycyc.txt"
    local file
    for file in "${FIXglobal}/am/fix_co2_proj/global_co2historicaldata"*; do
        cpreq "${file}" "${DATA}/$(basename "${file//global_/}")"
    done

    # MERRA2 aerosol climatology and optics
    if ((IAER == 1011)); then
        local month mm
        for ((month = 1; month <= 12; month++)); do
            mm=$(printf %02d "${month}")
            cpreq "${FIXglobal}/aer/merra2.aerclim.2014-2023.m${mm}.nc" "${DATA}/aeroclim.m${mm}.nc"
        done
    fi
    cpreq "${FIXglobal}/lut/optics_BC.v1_3.dat" "${DATA}/optics_BC.dat"
    cpreq "${FIXglobal}/lut/optics_OC.v1_3.dat" "${DATA}/optics_OC.dat"
    cpreq "${FIXglobal}/lut/optics_DU.v15_3.dat" "${DATA}/optics_DU.dat"
    cpreq "${FIXglobal}/lut/optics_SS.v3_3.dat" "${DATA}/optics_SS.dat"
    cpreq "${FIXglobal}/lut/optics_SU.v1_3.dat" "${DATA}/optics_SU.dat"

    # NoahMP table
    cpreq "${PARMglobal}/ufs/noahmptable.tbl" "${DATA}/noahmptable.tbl"

    # MPAS-specific land-use and soil parameter tables
    cpreq "${FIXmpas}/physics/LANDUSE.TBL" "${DATA}/LANDUSE.TBL"
    cpreq "${FIXmpas}/physics/GENPARM.TBL" "${DATA}/GENPARM.TBL"

    # Microphysics lookup tables
    case "${imp_physics}" in
        88) # TEMPO
            cpreq "${FIXglobal}/am/ccn_activate.bin" "${DATA}/ccn_activate.bin"
            for file in "${FIXmpas}/physics/tempo/"*; do
                cpreq "${file}" "${DATA}/"
            done
            ;;
        8) # Thompson
            cpreq "${FIXglobal}/am/CCN_ACTIVATE.BIN" "${DATA}/CCN_ACTIVATE.BIN"
            cpreq "${FIXglobal}/am/freezeH2O.dat" "${DATA}/freezeH2O.dat"
            cpreq "${FIXglobal}/am/qr_acr_qgV2.dat" "${DATA}/qr_acr_qgV2.dat"
            cpreq "${FIXglobal}/am/qr_acr_qsV2.dat" "${DATA}/qr_acr_qsV2.dat"
            for file in "${FIXmpas}/physics/thompson/"*; do
                cpreq "${file}" "${DATA}/"
            done
            ;;
        *)
            err_exit "Unsupported microphysics option imp_physics=${imp_physics} for UFS-MPAS"
            ;;
    esac
}

MPAS_det() {
    echo "SUB ${FUNCNAME[0]}: Determining run type for UFS-MPAS"

    # UFS-MPAS currently only supports cold starts from MPAS init_atmosphere output
    warm_start=".false."
    RERUN="NO"
    DOIAU="NO"
    fhrot=0

    if [[ ! -f "${COMIN_ATMOS_INPUT}/${mpas_ic_filename}" ]]; then
        err_exit "UFS-MPAS initial condition file '${COMIN_ATMOS_INPUT}/${mpas_ic_filename}' does not exist!"
    fi
    echo "Cold start from '${COMIN_ATMOS_INPUT}/${mpas_ic_filename}'"
}

MPAS_postdet() {
    echo "SUB ${FUNCNAME[0]}: Staging input data for UFS-MPAS"

    # Initial conditions
    cpreq "${COMIN_ATMOS_INPUT}/${mpas_ic_filename}" "${DATA}/${mpas_ic_filename}"

    # Mesh decomposition for the number of atmosphere tasks
    local graph_file="${FIXmpas}/${MPAS_MESH}/${MPAS_MESH}.graph.info.part.${ATMPETS}"
    if [[ ${ATMPETS} -gt 1 ]]; then
        if [[ ! -f "${graph_file}" ]]; then
            err_exit "MPAS graph partition file '${graph_file}' for ${ATMPETS} tasks does not exist!"
        fi
        cpreq "${graph_file}" "${DATA}/${mpas_graph_prefix}${ATMPETS}"
    fi

    # Tracer (constituent) definitions; must be consistent with the initial conditions
    if [[ -f "${FIXmpas}/${MPAS_MESH}/constituents.xml" ]]; then
        cpreq "${FIXmpas}/${MPAS_MESH}/constituents.xml" "${DATA}/constituents.xml"
    else
        cpreq "${FIXmpas}/constituents.xml" "${DATA}/constituents.xml"
    fi

    # Optional output stream lists; if absent, all fields are written
    local stream stream_dir="${FIXmpas}/stream_list/${CCPP_SUITE}"
    for stream in history restart diag; do
        local stream_file="stream_list.atmosphere.${stream}"
        if [[ "${stream}" == "history" ]]; then stream_file="stream_list.atmosphere.output"; fi
        if [[ "${stream}" == "diag" ]]; then stream_file="stream_list.atmosphere.diag_phys"; fi
        if [[ -f "${stream_dir}/${stream_file}" ]]; then
            cpreq "${stream_dir}/${stream_file}" "${DATA}/${stream_file}"
            declare -g "mpas_stream_list_${stream}=${stream_file}"
        else
            declare -g "mpas_stream_list_${stream}=none"
        fi
    done
}

MPAS_nml() {
    echo "SUB ${FUNCNAME[0]}: Creating input.nml and model_configure for UFS-MPAS"

    local start_year=${current_cycle:0:4}
    local start_month=${current_cycle:4:2}
    local start_day=${current_cycle:6:2}
    local start_hour=${current_cycle:8:2}

    atparse < "${PARMglobal}/ufs/mpas/input_gfs.nml.IN" > "${DATA}/input.nml"
    atparse < "${PARMglobal}/ufs/mpas/model_configure.IN" > "${DATA}/model_configure"

    echo "Rendered input.nml:"
    cat "${DATA}/input.nml"
    echo "Rendered model_configure:"
    cat "${DATA}/model_configure"
}

MPAS_out() {
    echo "SUB ${FUNCNAME[0]}: Copying output data for UFS-MPAS"

    # Configuration files
    cpfs "${DATA}/input.nml" "${COMOUT_CONF}/ufs.input.nml"
    cpfs "${DATA}/model_configure" "${COMOUT_CONF}/ufs.model_configure"
    cpfs "${DATA}/ufs.configure" "${COMOUT_CONF}/ufs.ufs.configure"

    # Native MPAS history/diagnostic files are named <stream>.YYYY-MM-DD_HH.MM.SS.nc
    local stream file valid fhr
    for stream in history diag_phys; do
        for file in "${DATA}/${stream}."*.nc; do
            if [[ ! -f "${file}" ]]; then continue; fi
            valid=$(basename "${file}" .nc)
            valid=${valid#"${stream}".}
            valid="${valid:0:4}${valid:5:2}${valid:8:2}${valid:11:2}"
            fhr=$(printf %03d "$(nhour "${valid}" "${current_cycle}")")
            cpfs "${file}" "${COMOUT_ATMOS_HISTORY}/${RUN}.t${cyc}z.mpas_${stream}.f${fhr}.nc"
        done
    done

    # Final restart (written for completeness; UFS-MPAS cannot restart from it yet)
    if [[ "${COPY_FINAL_RESTARTS:-NO}" == "YES" ]]; then
        if [[ ! -d "${COMOUT_ATMOS_RESTART}" ]]; then mkdir -p "${COMOUT_ATMOS_RESTART}"; fi
        for file in "${DATA}/restart."*.nc; do
            if [[ -f "${file}" ]]; then
                cpfs "${file}" "${COMOUT_ATMOS_RESTART}/$(basename "${file}")"
            fi
        done
    fi

    # MPAS log files
    for file in mpas_out.log mpas_err.log; do
        if [[ -f "${DATA}/${file}" ]]; then
            cpfs "${DATA}/${file}" "${COMOUT_ATMOS_HISTORY}/${RUN}.t${cyc}z.${file}"
        fi
    done

    echo "SUB ${FUNCNAME[0]}: Output data for UFS-MPAS copied"
}
