#!/usr/bin/env python3

from rocoto.rocoto_xml import RocotoXML
from applications.applications import AppConfig
from wxflow import to_timedelta, timedelta_to_HMS
from typing import Dict


class SFSRocotoXML(RocotoXML):

    def __init__(self, app_config: AppConfig, rocoto_config: Dict) -> None:
        super().__init__(app_config, rocoto_config)

    def get_cycledefs(self):
        sdate = self._base['SDATE_GFS']
        edate = self._base['EDATE']
        interval = self._base['interval_gfs']
        sdate_str = sdate.strftime("%Y%m%d%H%M")
        edate_str = edate.strftime("%Y%m%d%H%M")
        interval_str = timedelta_to_HMS(interval)
        strings = []
        strings.append(f'\t<cycledef group="sfs">{sdate_str} {edate_str} {interval_str}</cycledef>')

        # Create cycle-specific cycledefs for SFS (00z, 06z, 12z, 18z)
        # This allows different forecast lengths for different cycles
        if interval <= to_timedelta('6H'):
            for cyc in ['00', '06', '12', '18']:
                # Find first occurrence of this cycle hour at or after sdate
                cyc_hour = int(cyc)
                sdate_cyc = sdate.replace(hour=cyc_hour)
                if sdate_cyc < sdate:
                    # Move to next day if we're past this hour
                    sdate_cyc = sdate_cyc + to_timedelta('24H')
                # Find last occurrence at or before edate
                edate_cyc = edate.replace(hour=cyc_hour)
                if edate_cyc > edate:
                    # Move back a day if we're past the end date
                    edate_cyc = edate_cyc - to_timedelta('24H')

                if sdate_cyc <= edate_cyc:
                    sdate_cyc_str = sdate_cyc.strftime("%Y%m%d%H%M")
                    edate_cyc_str = edate_cyc.strftime("%Y%m%d%H%M")
                    interval_cyc_str = timedelta_to_HMS(to_timedelta('24H'))
                    strings.append(
                        f'\t<cycledef group="sfs_{cyc}">'
                        f'{sdate_cyc_str} {edate_cyc_str} {interval_cyc_str}'
                        f'</cycledef>'
                    )

        date2 = sdate + interval
        if date2 <= edate:
            date2_str = date2.strftime("%Y%m%d%H%M")
            strings.append(
                f'\t<cycledef group="sfs_seq">'
                f'{date2_str} {edate_str} {interval_str}'
                f'</cycledef>'
            )

        strings.append('')
        strings.append('')

        return '\n'.join(strings)
