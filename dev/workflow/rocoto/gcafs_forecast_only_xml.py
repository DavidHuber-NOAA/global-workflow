#!/usr/bin/env python3

from rocoto.rocoto_xml import RocotoXML
from applications.applications import AppConfig
from wxflow import to_timedelta, timedelta_to_HMS
from typing import Dict


class GCAFSForecastOnlyRocotoXML(RocotoXML):

    def __init__(self, app_config: AppConfig, rocoto_config: Dict) -> None:
        # Make sure we're using 'gcafs' as the run type
        # First ensure the keys exist before trying to access them
        if 'base' in app_config.configs:
            if app_config.configs['base']['RUN'] == 'gfs':
                app_config.configs['base']['RUN'] = 'gcafs'
            elif 'RUN' not in app_config.configs['base']:
                # If RUN is not defined, set it to 'gcafs'
                app_config.configs['base']['RUN'] = 'gcafs'
            else:
                app_config.configs['base']['RUN'] = 'gcafs'
        else:
            # If 'base' doesn't exist, initialize it with RUN set to 'gcafs'
            app_config.configs['base'] = {'RUN': 'gcafs'}

        super().__init__(app_config, rocoto_config)

    def get_cycledefs(self):
        sdate_gfs = self._base['SDATE_GFS']
        edate_gfs = self._base['EDATE']
        interval_gfs = self._base['interval_gfs']
        strings = []
        sdate_gfs_str = sdate_gfs.strftime("%Y%m%d%H%M")
        edate_gfs_str = edate_gfs.strftime("%Y%m%d%H%M")
        interval_gfs_str = timedelta_to_HMS(interval_gfs)
        # Change "gfs" to "gcafs" in cycle definitions
        strings.append(f'\t<cycledef group="gcafs">{sdate_gfs_str} {edate_gfs_str} {interval_gfs_str}</cycledef>')

        # Create cycle-specific cycledefs for GCAFS (00z, 06z, 12z, 18z)
        # This allows different forecast lengths for different cycles
        if interval_gfs <= to_timedelta('6H'):
            for cyc in ['00', '06', '12', '18']:
                # Find first occurrence of this cycle hour at or after sdate_gfs
                cyc_hour = int(cyc)
                sdate_cyc = sdate_gfs.replace(hour=cyc_hour)
                if sdate_cyc < sdate_gfs:
                    # Move to next day if we're past this hour
                    sdate_cyc = sdate_cyc + to_timedelta('24H')
                # Find last occurrence at or before edate_gfs
                edate_cyc = edate_gfs.replace(hour=cyc_hour)
                if edate_cyc > edate_gfs:
                    # Move back a day if we're past the end date
                    edate_cyc = edate_cyc - to_timedelta('24H')

                if sdate_cyc <= edate_cyc:
                    sdate_cyc_str = sdate_cyc.strftime("%Y%m%d%H%M")
                    edate_cyc_str = edate_cyc.strftime("%Y%m%d%H%M")
                    interval_cyc_str = timedelta_to_HMS(to_timedelta('24H'))
                    strings.append(
                        f'\t<cycledef group="gcafs_{cyc}">'
                        f'{sdate_cyc_str} {edate_cyc_str} {interval_cyc_str}'
                        f'</cycledef>'
                    )

        date2_gfs = sdate_gfs + interval_gfs
        if date2_gfs <= edate_gfs:
            date2_gfs_str = date2_gfs.strftime("%Y%m%d%H%M")
            # Change "gfs_seq" to "gcafs_seq" in cycle definitions
            strings.append(
                f'\t<cycledef group="gcafs_seq">'
                f'{date2_gfs_str} {edate_gfs_str} {interval_gfs_str}'
                f'</cycledef>'
            )

        if self._base['DO_METP']:
            if interval_gfs < to_timedelta('24H'):
                # Run verification at 18z, no matter what if there is more than one gfs per day
                sdate_metp = sdate_gfs.replace(hour=18)
                edate_metp = edate_gfs.replace(hour=18)
                interval_metp = to_timedelta('24H')
                sdate_metp_str = sdate_metp.strftime("%Y%m%d%H%M")
                edate_metp_str = edate_metp.strftime("%Y%m%d%H%M")
                interval_metp_str = timedelta_to_HMS(interval_metp)
            else:
                # Use same cycledef as gfs if there is no more than one per day
                sdate_metp_str = sdate_gfs_str
                edate_metp_str = edate_gfs_str
                interval_metp_str = interval_gfs_str

            strings.append(f'\t<cycledef group="metp">{sdate_metp_str} {edate_metp_str} {interval_metp_str}</cycledef>')

        strings.append('')
        strings.append('')

        return '\n'.join(strings)
