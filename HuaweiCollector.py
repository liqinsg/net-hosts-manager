#!/usr/bin/python3

import logging
import re
from pprint import pprint
from datetime import datetime

from BaseCollector import BaseCollector
from HuaweiSSH import HuaweiSSH
from ReportCsv import ReporterCsv
from ReportExcel import ReportExcel
from CustomerHostnames import CustomerHostnames

__author__ = 'Ravil Shamatov, ravil.shamatov@huawei.com, rav.shamatov@gmail.com'
SCRIPT_DESCRIPTION = f"""This is Collector for Huawei network devices that collect needed information from list of hosts. 
Author: {__author__}. Version: 2020-04-01"""

REPORT_DEFAULT_NAME = 'report_' + datetime.today().strftime('%Y-%m-%d_%H-%M-%S')
HUAWEI_FUNCTIONS = {
    'common':   HuaweiSSH.request_common_info,
    'lldp':     HuaweiSSH.request_lldp_neighbor_list, 
    'stack':    HuaweiSSH.request_stack_brief_info,
    'esn_chassis':  HuaweiSSH.request_esn_chassis,
    'esn_full': HuaweiSSH.request_esn_full,
    'all_boards_list': HuaweiSSH.request_all_boards_list,
    'main_boards_list': HuaweiSSH.request_boards_list,
    'mac_summary': HuaweiSSH.request_mac_summary,
    'routes_summary': HuaweiSSH.request_all_vrf_routes_number,
    'access_users_mab':   HuaweiSSH.request_mab_users_number,
    'access_users_dot1x':   HuaweiSSH.request_dot1x_users_number,
    'vrf':  HuaweiSSH.request_all_vrf_list
    }

COLUMNS_HEADER = {
        'geo':      ('Location',    10, ""),
        'segment':  ('Segment',     8,  ""),
        'role':     ('Role',        8,  ""),
        'hostname': ('Hostname',    39, "Got using 'display cur | i sysname' command"),
        'mgmt_ip':  ('MGMT IP',     17, ""),
        'hardware': ('Hadware',     21, "Got using 'display version' command"),
        'software_version':     ('Software version',    21, ""),
        'patch_version':        ('Patch version',       20, ""),
        'uptime':               ('Last reboot date',    22, "Calculated using 'display version' command.\nFormat: YEAR-MONTH-DAY"),
        'esn_chassis':          ('ESN Chassis',         24, "ESN of chassis, got using 'display ESN' command"),
        'main_boards_list':     ('Boards',  22,	"Boards from 'display device' output excepting Power and Fan boards"),
        'stack_info': ('Stack',   17, ""),
        'in_used':  ('MAC Used', 10,    "In-used mac-address from 'display mac-address summary' command's output"),
        'capacity': ('MAC Capacity',    10, ""),
        'memory_usage': ('Memory Usage', 10, "Memory Usage in percentage"),
        'mab_users_number': ('MAB users', 10, 
            "Total number of MAB users, got using 'display access-user access-type mac-authen' command. For S switches only."),
        'dot1x_users_number': ('802.1x users', 10, 
            "Total number of 802.1x users, got using 'display access-user access-type dot1x' command. For S switches only."),
        'vrf': ('VRF', 15,	""),
        'total': ('Total Routes', 6, 
            "Column 'total routes' from 'display ip routing-table all-vpn-instance statistics' command's output"),
        'bgp':      ('BGP',     6,      ""),
        'ospf':     ('OSPF',    6,		""),
        'isis':     ('IS-IS',   6,		""),        
        'static':   ('Static',  6,		""),
        'direct':   ('Direct',  6,		""),
        'updated':  ('Updated', 24,		"Date when information about this device was collected last time.")}

CSV_MODE = 'w'

class HuaweiCollector(BaseCollector):

    _default_device_type = 'huawei'
    _report_filename = REPORT_DEFAULT_NAME
    _check_list = {
        'common':   True,
        'lldp':     False,
        'stack':    True,
        'esn_chassis':  False,
        'esn_full':     False,
        'all_boards_list':  False,
        'main_boards_list': False,
        'mac_summary':  False,
        'routes_summary':   False,
        'access_users_mab': False,
        'access_users_dot1x': False,
        'vrf':      False,
        'resources':    False
    }
    
    def __init__(self, **settings):
        self.report_filename = settings['report_filename']

        super().__init__(**settings)

    @property
    def report_filename(self):
        return self._report_filename

    @report_filename.setter
    def report_filename(self, filename):
        self._logger.debug(f"Trying to set new report filename '{filename}'")
        self._report_filename = filename or self._report_filename
        self._logger.info(f"Set new report filename '{filename}'")

    @property
    def check_list(self):
        return self._check_list

    @check_list.setter
    def check_list(self, check_list):
        for key in self.check_list:
            self._check_list[key] = check_list[key]
        self._logger.debug(f"After applying check list {check_list}, new check_list: {self.check_list}")

    @staticmethod
    def convert_result_to_list(value):
        #print(value)
        try:
            if type(value) == list:
                return value
            elif type(value) == dict:
                return [str(value) for value in list(value.values())]
            elif type(value) == int or type(value) == str:
                return [value]
            else:
                print(f"Can't get result in list. Uknown data type {type(value)} '{value}'")
        except Exception:
            print(f"Exception while trying to convert value '{value}' to list")

    def request_common_info(self, host_huawei):
        properties = {}
        if self._check_list.get('common', None):
            properties = host_huawei.request_common_info()
            try: 
                properties['geo'] = CustomerHostnames.get_geolocation_from_sysname(properties['hostname'])
                self._logger.debug(
                    f"{host_huawei} - got geo information '{properties['geo']}'")
                properties['segment'] = CustomerHostnames.get_segment_from_sysname(properties['hostname'])
                self._logger.debug(
                    f"{host_huawei} - got segment information '{properties['segment']}'")
                properties['role'] = CustomerHostnames.get_role_from_sysname(properties['hostname'])
                self._logger.debug(
                    f"{host_huawei} - got role information '{properties['role']}'")
                properties['mgmt_ip'] = host_huawei.ip_address
            except Exception:
                self._logger.error(f"{host_huawei} exception for common_error", exc_info=True)
            #print(properties)
        return properties

    def request_all_for_device(self, host_huawei):
        properties = {
            **self.request_common_info(host_huawei), 
            **host_huawei.request_stack_brief_info(one_key_only=True),
            **host_huawei.request_mac_summary(),
            **host_huawei.request_all_vrf_routes_number(),
            **host_huawei.request_access_users_number()
        }
        #pprint(host_huawei.request_mac_summary())
        #ppritn
        properties['esn_chassis'] = ', '.join(host_huawei.request_esn_chassis())
        properties['main_boards_list'] =  ', '.join(host_huawei.request_boards_list(printable=True))
        properties['vrf'] = host_huawei.request_all_vrf_list()
        properties['memory_usage'] = f"{host_huawei.request_memory_usage()}%" 
        properties['updated'] = host_huawei.change_datetime
        return properties

    def get_report_header(self):
        header_values = [value[0] for value in COLUMNS_HEADER.values()]
        self._logger.info(f"Report header values: {header_values}")
        return header_values

    def get_table_devices_column_width(self):
        return tuple([column[1] for column in COLUMNS_HEADER.values()])
    
    def get_table_devices_column_comments(self):
        return tuple([column[2] for column in COLUMNS_HEADER.values()])

    def get_report_row(self, host_info):
        row = []
        for key in COLUMNS_HEADER.keys():
            row.append(host_info.get(key, 'Error'))
        return row

    def run_for_device(self, host_info, commands=''):
        self._logger.debug(
            f"Creating HuaweiSSH '{host_info}' and logging settings {self.host_log_settings}")
        host = HuaweiSSH(
            host_info['mgmt_ip'], 
            host_info['hostname'],
            self.host_log_settings)
        host.connect_ssh(self.username, self.password, nmiko_device_type=self.default_device_type)
        #self._logger.debug(f"{host} - ssh_lib_type {host.ssh_lib_type}")
        if host.ssh_lib_type:
            try:
                results = self.request_all_for_device(host)
            except Exception:
                self._logger.error(f'Exception for host {str}', exc_info=True)
        host.disconnect_ssh()
        try:   
            self.csv.write_row(
                self.get_report_row(results))
            self._logger.debug(f"Wrote to csv information about {host}")
        except UnboundLocalError: # There was exception in function request_all_for_device and data wasn't colllected
            pass
        except Exception:
            self._logger.error(f"Handled exception while writing to csv {host} results", exc_info=True)
        self._logger.info(f"{host} - collected result is {results}")
        self._logger.warning(f"Host {str(host)}\t- Done")

    def run_for_files(self, hosts_filename='', commands_filename=''):
        self._logger.error(f"Creating report file '{self.report_filename}'")
        self.csv = ReporterCsv(self.report_filename, mode=CSV_MODE)
        self.csv.write_header(
            self.get_report_header())
        self._logger.debug(f"Created report file '{self.report_filename}'")
        super().run_for_files(hosts_filename='', commands_filename='')
        del self.csv

    @staticmethod
    def convert_numbers_to_int(row):
        for i, value in enumerate(row): 
            try: 
                row[i] = int(value)
            except Exception:
                pass
        return row

    def convert_report_csv_to_xlsx(self):
        self.csv = ReporterCsv(self.report_filename, mode='r')
        self.xlsx = ReportExcel(self.report_filename + '.xlsx')
        self.xlsx.add_sheet_header(
            self.csv.read_row(),
            self.get_table_devices_column_width(),
            self.get_table_devices_column_comments()
        )
        for row in self.csv.reader:
            self._logger.debug(f"Adding row to xlsx report {row}")
            self.xlsx.write_row(
                HuaweiCollector.convert_numbers_to_int(row))
        self.xlsx.save()
        self._logger.warning(f"Excel report {self.report_filename + '.xlsx'} has been generated.")

    @staticmethod
    def main():
        """Main function 
        """        
        # ! Finish all key arguments of script
        settings = HuaweiCollector.get_script_arguments(
            HuaweiCollector.parse_arguments())
        collector = HuaweiCollector(**settings)
        # Check how much time it took to execute this script
        collector.set_start_timer()
        collector.run_for_files()
        collector.convert_report_csv_to_xlsx()
        collector._logger.warning(f'\nIt took {collector.get_duration_seconds()} seconds')

if __name__ == '__main__':
    HuaweiCollector.main()
