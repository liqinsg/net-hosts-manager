#!/usr/bin/python3
# coding=utf8

import re
from datetime import datetime, timedelta

from BaseSSH import BaseSSH
from HuaweiCE import HuaweiCE
from HuaweiS import HuaweiS
from netmiko import ConnectHandler
from netmiko.ssh_exception import (NetMikoAuthenticationException,
                                   NetMikoTimeoutException)

# module_logger = logging.getLogger("HuaweiDevice")

NETMIKO_DEVICE_TYPE = 'huawei'

CMD_NON_SPLIT_SCREEN = 'screen-length 0 temporary'
EMPTY_STACK_INFO = {'status': 0,
        'Stack mode': '',
        'Stack topology type': '',
        'Stack system MAC': '',
        'Stack members number': 0}

HARDWARE_PLATFORMS = {
    'CE': r'CE', 
    'S': r'S\d+', 
    'USG': r'USG'}



DISPLAY_VERSION = 'display version'
DISPLAY_PATCH = 'display patch'
DISPLAY_SYSNAME = 'display current-configuration | include sysname'
DISPLAY_LLDP_NEIGHBOR = 'display lldp neighbor'
DISPLAY_STACK = 'display stack'
DISPLAY_CHASSIS_ESN = 'display esn'
#DISPLAY_DEVICE = 'display device'
DISPLAY_DEVICE = 'display device manufacture-info'
DISPLAY_MAC_SUMMARY = 'display mac-address summary'
DISPLAY_ROUTES_SUMMARY = 'display ip routing-table all-vpn-instance statistics'
REGEX_ROUTES_SUMMARY = {
    'total':    r'\nTotal\s+(?P<routes_number>\d+)',
    'direct':   r'\nDIRECT\s+(?P<routes_number>\d+)',
    'static':   r'\nSTATIC\s+(?P<routes_number>\d+)',
    'ospf':     r'\nOSPF\s+(?P<routes_number>\d+)',
    'isis':     r'\nIS.*?IS\s+(?P<routes_number>\d+)',
    'bgp':      r'\nBGP\s+(?P<routes_number>\d+)'}
DISPLAY_IP_VRF = 'display ip vpn-instance'

class HuaweiSSH(BaseSSH):
    '''Represents and manipulate single Huawei Switch or Router with remote SSH access.'''

    _hardware = ''         # Type : string
    _patch_version = ''    # Type : string
    _lldp_neighbors = []   # Type : list of dictionaries
    _esn_chassis = []      # Type : list
    __esn_boards = []
    _stack = EMPTY_STACK_INFO
    __os_version = ''
    __ip_address = ''
    __device_type = ''    # ! Сделать отдельные классы для каждого вида устройств (AR, CE, S, NE)
    __boards_list = []

    ''' Connection '''
    def connect_ssh_nmiko(self, username, password, port=22, device_type=NETMIKO_DEVICE_TYPE):
        """ Establish SSH connection using Netmiko module

        Arguments:
            username {string} -- Username for SSH connection
            password {string} -- Password for SSH connection

        Keyword Arguments:
            port {int} -- Target host's TCP port for SSH connection (default: {22})
            device_type {str} -- device_type for Netmiko module (default: {'huawei'})
        """
        super().connect_ssh_nmiko(username, password, port, device_type)

    def adjust_ssh_screen_lenght(self):
        self.send_command(CMD_NON_SPLIT_SCREEN) 

    ''' Software version '''
    @staticmethod
    def is_os_version_valid(version):
        regex = r'V\d+R\d+'
        match = re.search(regex, version, flags=re.IGNORECASE)
        return True if match else False

    def _return_version(self, output_display_version):
        """ Look for version information in output of command 'display version'.

        Arguments:
            output_display_version {string} -- Output of commmand 'display version'

        Returns:
            [string] -- VRP Version information (Example: V200R005C10SPC800). 
                        If no information is found - return 'N\A'
        """
        """ Example 1 of "display version" output
                Huawei Versatile Routing Platform Software
                VRP (R) software, Version 8.180 (CE6860EI V200R005C10SPC800)
                Copyright (C) 2012-2018 Huawei Technologies Co., Ltd.
                HUAWEI CE6860-48S8CQ-EI uptime is 4 days, 8 hours, 22 minutes
                Patch Version: V200R005SPH008"""
        """ Example 2 of "display version" output
                Huawei Versatile Routing Platform Software
                VRP (R) software, Version 5.170 (S5720 V200R011C10SPC600)
                Copyright (C) 2000-2018 HUAWEI TECH Co., Ltd.
                HUAWEI S5720-52P-LI-AC Routing Switch uptime is 11 weeks, 5 days, 9 hours, 17 minutes"""
        regex = r'VRP.*software.*(?P<version>V\d+R\d+\S+)\)'
        match = re.search(regex, output_display_version, re.IGNORECASE)
        try:
            return str(match.group('version'))
        except AttributeError:
            self.log_event_error(
                f'Exception while trying to find Software Version for host {self.get_ip_address()} ' + \
                f'in this output:\n{output_display_version}')
            return 'N/A'

    def request_software_version(self):
        """Request Software version of device

        Returns:
            [string] -- VRP Version information in format 'V200R005C10SPC800'
        """
        self.log_info_requesting('Software_version', DISPLAY_VERSION)
        self.os_version = self._return_version(
            self.send_command(DISPLAY_VERSION))
        self.log_info_requested('Software_version', self.os_version, DISPLAY_VERSION)
        return self.os_version
    
    ''' Hardware '''
    @property
    def hardware_platform(self):
        """Return hardware platform type of device (CE/S/AR/NE/AC)

        Returns:
            [string] -- Hardware platform type (CE/S/AR/NE/AC)
        """
        hardware = self.hardware or self.request_hardware_info()
        for platform in HARDWARE_PLATFORMS.keys():
            if re.search(HARDWARE_PLATFORMS[platform], hardware):
                return platform

    def _return_hardware(self, output_display_version, full=False):
        """ Look for hardware information in output of command 'display version'

        Arguments:
            output_display_version {string} -- Output of commmand 'display version'

        Returns:
            [string] -- Hardware information (Example: CE6860-48S8CQ-EI, S5720-52P-LI-AC)
        """

        """ Example 1 of "display version" output
            Huawei Versatile Routing Platform Software
            VRP (R) software, Version 8.180 (CE6860EI V200R005C10SPC800)
            Copyright (C) 2012-2018 Huawei Technologies Co., Ltd.
            HUAWEI CE6860-48S8CQ-EI uptime is 4 days, 8 hours, 22 minutes
            Patch Version: V200R005SPH008"""
        """ Example 2 of "display version" output
            Huawei Versatile Routing Platform Software
            VRP (R) software, Version 5.170 (S5720 V200R011C10SPC600)
            Copyright (C) 2000-2018 HUAWEI TECH Co., Ltd.
            HUAWEI S5720-52P-LI-AC Routing Switch uptime is 11 weeks, 5 days, 9 hours, 17 minutes"""
        regexes = [
            r'Copyright .*\nHUAWEI (?P<hardware>\S+).* uptime',
            r'Copyright .*\n(?P<hardware>\S+).* uptime'
        ]
        for regex in regexes: 
            match = re.search(regex, output_display_version)
            try:
                hardware = match.group('hardware')
                self.log_match_found('hardware', hardware, regex, output_display_version)
                return hardware
            except AttributeError:
                pass
        self.log_match_error('hardware', regex, output_display_version)
        return 'N/A'

    def request_hardware_info(self):
        """Request hardware platform information of device

        Returns:
            [string] -- Hardware platform information in format ''CE6860-48S8CQ-EI' or 'S5720-28P-LI-AC'
        """        
        self.log_info_requesting('Hardware', DISPLAY_VERSION)
        self.hardware = self._return_hardware(
            self.send_command(DISPLAY_VERSION))
        self.log_info_requested('Hardware', self.os_version, DISPLAY_VERSION)
        return self.hardware    

    ''' Uptime '''
    @staticmethod
    def convert_uptime_to_since_date(uptime_period):
        """Convert uptime information in format '28 weeks, 1 day, 10 hours, 7 minutes' 
        to date from last reboot in format '2019-09-20, Fri, 16:28'
        
        Arguments:
            uptime_period {str} -- uptime information in format '28 weeks, 1 day, 10 hours, 7 minutes'
        
        Returns:
            [str] -- Date of last reboot in format '2019-09-20, Fri, 16:28'
        """        
        regex = r'(?P<number>\d+)\s+(?P<period_name>\w+)'
        matches = re.findall(regex, uptime_period)
        def days_multiply(word):
            words = {
                'weeks': 7,
                'week':7,
                'day':1,
                'days':1}
            return int(words.get(word, 0))
        def minutes_multiply(word):
            words = {
                'hour' : 60,
                'hours': 60,
                'munites': 1,
                'minutes':1}
            return int(words.get(word, 0))
        #now = datetime.date.today()
        days, minutes, x = 0, 0, []
        for match in matches: 
            days += int(match[0]) * days_multiply(match[1])
        for match in matches: 
            minutes += int(match[0]) * minutes_multiply(match[1])
        # If timedelta has been calculated successfully:
        if days or minutes: 
            date_shift = datetime.now() - timedelta(days=days,minutes=minutes)
            return date_shift.strftime("%Y-%m-%d (%a) %H:%M") # '2019-09-20, Fri, 16:28'
        else: # return just N/A
            return f"N/A for '{uptime_period}'"

    def _return_uptime(self, output_display_version):
        """ Look for uptime information in output of command 'display version'

        Arguments:
            output_display_version {string} -- Output of commmand 'display version'

        Returns:
            [string] -- Uptime information (Example: '11 weeks, 5 days, 9 hours, 17 minutes')
        """

        """ Example 2 of "display version" output
            Huawei Versatile Routing Platform Software
            VRP (R) software, Version 5.170 (S5720 V200R011C10SPC600)
            Copyright (C) 2000-2018 HUAWEI TECH Co., Ltd.
            HUAWEI S5720-52P-LI-AC Routing Switch uptime is 11 weeks, 5 days, 9 hours, 17 minutes"""

        regex = r'uptime is\s+(?P<uptime>.*)'
        match = re.search(regex, output_display_version)
        try:
            uptime = match.group('uptime')
            self.log_match_found('uptime', uptime, regex, output_display_version)
            return uptime
        except AttributeError:
            log_match_error('uptime', regex, output_display_version)
            return 'N/A'  

    def request_uptime_info(self):
        """Request uptime information of device

        Returns:
            [string] -- Uptime in format '10 weeks, 6 days, 9 hours, 17 minutes'
        """        
        self.log_info_requesting('Uptime', DISPLAY_VERSION)
        self.uptime = self._return_uptime(
            self.send_command(DISPLAY_VERSION))
        return self.uptime

    ''' Patch functions '''
    @property
    def patch_version(self):
        return self._patch_version or None

    @patch_version.setter
    def patch_version(self, patch_version):
        self._patch_version = patch_version
        
    def _is_no_patch_exists(self, output_display_patch):
        """Checks if patch exists.
        In some cases output of command "display patch" may looks like this:
            Info: No patch exists.
            The state of the patch state file is: Idle
            The current state is: Idle
        If so, then function returns True (means 'Yes, no patch exists')
        Else - returns False (means 'No, no confirmation that no patch exists was found')

        Arguments:
            output_display_patch {string} -- output of command 'display patch'

        Returns:
            [boolean] -- [description]
        """
        regex = r'No patch exists'
        match = re.search(regex,output_display_patch)
        if match is not None:
            return True
        else:
            return False

    def _return_patch(self, output_display_patch):
        """ Look for Patch information in output of command 'display patch'.

        Arguments:
            output_display_patch {[type]} -- [description]
                Format for CE:
                    Patch Package Name    :flash:/CE6860EI-V200R005SPH008.PAT
                    Patch Package Version :V200R005SPH008
                    Patch Package State   :Running
                    Patch Package Run Time:2020-03-03 12:38:44+03:00
                Format for S:
                    Patch Package Name   :flash:/s5720li-v200r011sph011.pat
                    Patch Package Version:V200R011SPH011
                    The state of the patch state file is: Running
                    The current state is: Running

        Returns:
            [string] -- patch version information in format 'V200R005SPH008' or 'V200R011SPH011'. 
                        If not installed - return 'No patch'
                        If not found info in 'display patch' output - return 'N/A'
        """
        regex = r'Patch Package Version\s*:\s*(?P<patch_version>\S+)'
        match = re.search(regex, output_display_patch)
        try:
            patch_version = str(match.group('patch_version'))
            self.log_match_found('Patch version', patch_version, regex, output_display_patch)
            return patch_version
        except AttributeError:
            if self._is_no_patch_exists(output_display_patch):
                return 'No patch'
        except Exception as e:
            self.log_match_error('Patch Version', regex, output_display_patch)
            return 'N/A'

    def request_patch_info(self):
        """Request information about current patch version using command 'display patch'.

        Returns:
            [string] -- patch version information in format 'V200R005SPH008' or 'V200R011SPH011'. 
                        If not installed - return 'No patch'
                        If not found info in 'display patch' output - return 'N/A'
        """
        self.log_info_requesting('Patch Version', DISPLAY_PATCH)
        self.patch_version = self._return_patch(
            self.send_command(DISPLAY_PATCH))
        self.log_info_requested('Patch Version', self.patch_version, DISPLAY_PATCH)
        return self.patch_version

    ''' Common Information Functions'''
    def _return_sysname(self, output_display_cur):
        """ Look for Sysname information in output of command 'display current-configuration | include sysname'.

        Arguments:
            output_display_cur {string} -- output of command 'display current-configuration | include sysname'

        Returns:
            [string] -- current hostname in format 'AC-R4-CE6860-01' or 'ToR-R3
        """
        regex = r'sysname (?P<sysname>\S+)'
        match = re.search(regex, output_display_cur)
        try:
            sysname = str(match.group('sysname'))
            self.log_match_found('Sysname', sysname, regex, output_display_cur)
            return sysname
        except AttributeError:
            self.log_match_error('Sysname', regex, output_display_cur)
            return 'N/A'

    def request_common_info(self, flag_uptime_since=True):
        """Request common information:
            hostname, hardware, software_version, patch_version, uptime.

        Returns:
            [dict of string] -- Dictionary with brief information about device in format: 
                {'software_version': 'V200R005C10SPC800', 
                'patch_version': 'V200R005SPH008', 
                'hardware': 'CE6860-48S8CQ-EI', 
                'uptime': '8 days, 8 hours, 29 minutes ', 
                'hostname': 'AC-R4-CE6860-01'}
        """
        self.log_info_requesting('Common information', 'display version')
        output = self.send_command(DISPLAY_VERSION)
        self.os_version = self._return_version(output)
        self.hardware = self._return_hardware(output)
        if flag_uptime_since:
            self.uptime = HuaweiSSH.convert_uptime_to_since_date(self._return_uptime(output))
        else: 
            self.uptime = self._return_uptime(output)
        self.log_info_requested('Software version', self.os_version, DISPLAY_VERSION)
        self.log_info_requested('Hardware', self.hardware, DISPLAY_VERSION)
        self.log_info_requested('Uptime', self.uptime, DISPLAY_VERSION)

        self.patch_version = self._return_patch(
            self.send_command(DISPLAY_PATCH))
        self.log_info_requested('Patch version', self.patch_version, DISPLAY_PATCH)

        self.hostname = self._return_sysname(
            self.send_command(DISPLAY_SYSNAME))
        self.log_info_requested('Sysname', self.hostname, DISPLAY_SYSNAME)

        return {'hostname': self.hostname,
                'software_version': self.os_version,
                'patch_version': self.patch_version,
                'hardware': self.hardware,
                'uptime': self.uptime}

    ''' LLDP '''
    @staticmethod
    def is_mgmt_interface(interface_name):
        """Check if Interface is Management interface or not.

        Arguments:
            interface_name {string} -- interface name in format '100GE1/0/2' or 'MEth0/0/0'

        Returns:
            [boolean] -- Return True if Interface is Management interface and False if not.
        """
        match = re.search(r'meth', interface_name, re.IGNORECASE)
        return True if match else False

    @staticmethod
    def is_neighbor_huawei(system_description):
        # ! TODO
        return

    def _return_lldp_neighbor_list(self, output_display_lldp_neighbor):
        """ Look for information about all LLDP neighbors in output of command 'display lldp neighbor'.

        Arguments:
            output_display_lldp_neighbor {string} -- output of command 'display lldp neighbor'

        Returns:
            [list of tuple] -- List of LLDP neighbors. tuple format: 
                (interface, interface_neighbors_number, neighbor_interface, neighbor_hostname, neighbor_description, neighbor_mgmt_address)
        """
        neighbors = []
        regex = r'(?P<interface>\S+) has (?P<interface_neighbors_number>\d+) neighbor.*\n\n' + \
            r'Neighbor index(.*\n)*?' + \
            r'Port ID\s+:\s*(?P<neighbor_interface>\S+)(.*\n)*?' + \
            r'System name\s+:\s*(?P<neighbor_hostname>\S+)(.*\n)*?' + \
            r'System description\s+:(?P<neighbor_description>\S+)(.*\n)*?' + \
            r'Management address.+:(?P<neighbor_mgmt_address>\d+\.\d+\.\d+\.\d+)'
        matches = re.finditer(regex, output_display_lldp_neighbor)
        try:
            for m in matches:
                '''
                neighbor = {'interface_neighbors_number' : m.group('interface_neighbors_number'),
                            'neighbor_interface' : m.group('neighbor_interface'),
                            'neighbor_hostname' : m.group('hostname'),
                            'neighbor_description' : m.group('neighbor_description'),
                            'neighbor_mgmt_address' : m.group('neighbor_mgmt_address')}
                '''
                ''' Check two conditions for LLDP neighbor:
                    1. Neighbor hostname isn't local device's hostname (Means this interface isn't 'service type tunnel')
                    2. Local interface isn't Management interface'''
                #print(m.groups())
                if m.group('neighbor_hostname') != self.hostname and \
                    not HuaweiSSH.is_mgmt_interface(m.group('interface')):
                    neighbors.append((
                            m.group('interface'),
                            m.group('interface_neighbors_number'),
                            m.group('neighbor_interface'),
                            m.group('neighbor_hostname'),
                            m.group('neighbor_description'),
                            m.group('neighbor_mgmt_address')))
            self._logger.debug(f'LLDP neighbors for {str(self)}, full list: {neighbors}')
            return neighbors
        except AttributeError:
            self.log_match_error('LLDP neighbors', regex, output_display_lldp_neighbor)
            return ['N/A']

    def request_lldp_neighbor_list(self):
        """Request information about LLDP neighbors using command 'display lldp neighbor'

        Returns:
            [list of dict] -- Information about lldp neighbors in format:
                                {'100GE1/0/1': {'neighbor_description': 'Huawei',
                                        'neighbor_hostname': 'AG-R4-CE12804-01',
                                        'neighbor_interface': '100GE1/0/0',
                                        'neighbor_mgmt_address': '10.198.177.7',
                                        'interface_neighbors_number': '1'},
                                '100GE1/0/2': {'neighbor_description': 'Huawei',
                                        'neighbor_hostname': 'AG-R5-CE12804-02',
                                        'neighbor_interface': '100GE1/0/0',
                                        'neighbor_mgmt_address': '10.198.177.8',
                                        'interface_neighbors_number': '1'},
        """
        self.log_info_requesting('LLDP neighbors', DISPLAY_LLDP_NEIGHBOR)
        output = self.send_command(DISPLAY_LLDP_NEIGHBOR)
        neighbors = self._return_lldp_neighbor_list(output)
        self.log_info_requested('LLDP neighbors', neighbors, DISPLAY_LLDP_NEIGHBOR)

    ''' Stack '''
    @property
    def stack_info(self, stack_info):
        self._stack_info = stack_info

    @stack_info.setter
    def stack_info(self, stack_info):
        """
        Arguments:
            stack_info {dict of string} -- dict of string inf format
                                {'Stack members number': 1,
                                'Stack mode': 'Service-port',
                                'Stack system MAC': '2416-6d8e-c2a6',
                                'Stack topology type': 'Link',
                                'status': 1}
        """        
        self._stack['status'] = stack_info['status']
        self._stack['Stack mode'] = stack_info['Stack mode'] 
        self._stack['Stack topology type'] = stack_info['Stack topology type']
        self._stack['Stack system MAC'] = stack_info['Stack system MAC']
        self._stack['Stack members number'] = stack_info['Stack members number']

    def _return_stack_member_number(self, output_display_stack):
        """Count number of Stack members in output of command 'display stack'

        Arguments:
            output_display_stack {[type]} -- [description]
                Example:
                Slot of the active management port: --
                Slot      Role        MAC Address      Priority   Device Type
                -------------------------------------------------------------
                0         Master      e0cc-7a41-2160   200        S5720-56C-PWR-EI-AC1
                1         Slave       e0cc-7a41-23c0   100        S5720-56C-PWR-EI-AC1

        Returns:
            [int] -- number of stack members
        """
        regex = r'(?P<index>\d+)\s+(?P<role>\S+)\s+(?P<mac>\S+-\S+-\S+)\s+(?P<priority>\d+)\s+(?P<device_type>\S+)'
        match = re.findall(regex, output_display_stack)
        members_number =  len(match)
        self.log_match_found('Stack members number', members_number, regex, output_display_stack)
        return members_number

    def _return_stack_info(self, output_display_stack, one_key_only, more_than_two_member_only):
        """ Look for information about stack using Regular Expression in output of 'display stack' command

        Arguments:
            output_display_stack {string} -- output of command 'display stack'

            <HUAWEI> display stack
            Stack mode: Service-port                                                      
            Stack topology type: Link                                                       
            Stack system MAC: 0000-1382-4569                                                
            MAC switch delay time: 10 min                                                    
            Stack reserved VLAN: 4093                                                       
            Slot of the active management port: 0
            Slot    Role        MAC address       Priority   Device type
            -------------------------------------------------------------
                0   Master      0018-82b1-6eb4   200          S5720-28P-LI-AC
                1   Standby     0018-82b1-6eba   150          S5720-28P-LI-AC

        Returns:
            [dict of string] -- Brief information about stack in format: 
                {'Stack members number': 1,
                'Stack mode': 'Service-port',
                'Stack system MAC': '2416-6d8e-c2a6',
                'Stack topology type': 'Link',
                'status': 1}
        """        
        result = {}
        regex = r'Stack mode\s*:\s*(?P<mode>\S+)(.*\n)*?' + \
            r'Stack topology type\s*:\s*(?P<type>\S+)(.*\n)*?' + \
            r'Stack system MAC\s*:\s*(?P<MAC>\S+-\S+-\S+)(.*\n)*?'
        self.log_event_debug(f'Checking if {str(self)} is stack:')
        match = re.search(regex, output_display_stack)
        result['Stack members number'] = self._return_stack_member_number(output_display_stack)
        if more_than_two_member_only and result['Stack members number'] > 1:
            try:
                result['Stack mode'] = match.group('mode')
                result['Stack topology type'] = match.group('type')
                result['Stack system MAC'] = match.group('MAC')
                result['status'] = 1
                if one_key_only:
                    result = {
                        'stack_info': f"topo: {result.get('Stack topology type', 'no')}, members: {result['Stack members number']}"}
                self.log_match_found('Stack information', result, regex, output_display_stack)
            except AttributeError:
                if one_key_only:
                    result = {'stack_info': f"members: {result['Stack members number']}"}
                if self.hardware_platform == 'CE': 
                    pass
                else:
                    self.log_match_error('Stack information', regex, output_display_stack)
        elif one_key_only:
            result = {
                'stack_info': ""}

        return result

    def request_stack_brief_info(self, one_key_only=False, more_than_two_member_only=True):
        """Request stack information using command 'display stack'

        Return:
            [dict of string]  - information about current stack status in format:
        """                
        self.log_info_requesting('Stack information', DISPLAY_STACK)
        output = self.send_command(DISPLAY_STACK)
        stack_info = self._return_stack_info(output, one_key_only, more_than_two_member_only)           
        self.log_info_requested('Stack information', stack_info, DISPLAY_STACK)
        return stack_info
 
    ''' ESN '''
    def _return_chassiss_esn(self, output_display_esn):
        """ Look for information about ESN of chassis using Regex in output of 'display esn' command

        Arguments:
            output_display_esn {string} -- output of command 'display esn'

        Returns:
            [list of dict] -- list of ESN information in format:
                [{'index': '0', 'esn': '21980107682SJC600039'}]
        """        
        regex = r'(?P<index>\S+)\s*:\s*(?P<esn>\S+)'
        matches = re.finditer(regex, output_display_esn)
        esn_list = []
        try:
            for match in matches:
                esn_list.append(match.group('esn'))
            self.log_match_found('ESN Chassis', esn_list, regex, output_display_esn)
            return esn_list
        except Exception:
            self.log_match_error('ESN Chassis', regex, output_display_esn)
            return []

    def get_chassis_esn_command(self):
        return DISPLAY_CHASSIS_ESN

    def request_esn_chassis(self):
        """Request information about ESN of chassis using command 'display esn'

        Returns:
            [list of string] -- list of ESN information in format ['21980107682SJC600039']
        """
        command = self.get_chassis_esn_command()
        self.log_info_requesting('ESN Chassis', command)
        output = self.send_command(command)
        esn_chassis = self._return_chassiss_esn(output)
        self.log_info_requested('ESN Chassis', esn_chassis, command)
        return esn_chassis

    def _return_esn_full(self, output_display_elabel):
        """Look for information about ESN of all boards in output of 'display elabel' command

        Arguments:
            output_display_elabel {string} -- Output of Platform's command for requesting elabel 

        Returns:
            [list of dir] -- List of boards in format: 
                            [{'bar_code': '21980107682SJC600039',
                                'board_type': 'S5720-28P-LI-AC',
                                'description': 'S5720-28P-LI-AC(24 Ethernet 10/100/1000 ports,4 Gig SFP,AC '
                                'power support,overseas)',
                                'item': '98010768',
                                'manufactured': '2018-12-19'}]
        """        
        regex = r'\[Board Properties\]\n' + \
                r'BoardType=(?P<board_type>.*)\n' + \
                r'BarCode=(?P<bar_code>\S+)\n' + \
                r'Item=(?P<item>.*)\n' + \
                r'Description=(?P<description>.*)\n' + \
                r'Manufactured=(?P<manufactured>.*)'
        matches = re.finditer(regex, output_display_elabel)
        esn_list = []
        try:
            for match in matches:
                if match.group('board_type') and match.group('bar_code'):
                    esn_list.append({
                        'board_type'    : match.group('board_type'),
                        'bar_code'      : match.group('bar_code'),
                        'item'          : match.group('item'),
                        'description'   : match.group('description'),
                        'manufactured'  : match.group('manufactured')})
            self.log_match_found('ESN full', esn_list, regex, output_display_elabel)
            return esn_list
        except AttributeError:
            self.log_match_error('ESN full', regex, output)
            return []

    def get_command_display_esn_full(self):
        """ Get command for requesting information about full ESN information according to the platform type.
        For example, for S switches after executing command 'displaye elabel' prompt is needed.

        Returns:
            [str] -- command ('display elabel')
            [dict] -- dictionary in format {
                        expect_string: '[Y/N]', 
                        prompt: 'Y'}
        """        
        kwargs = {}
        platform = self.hardware_platform
        if platform == 'CE':
            command, kwargs['expect_string'], kwargs['prompt'] = HuaweiCE.get_request_esn_full_command()
        elif platform == 'S':
            command, kwargs['expect_string'], kwargs['prompt'] = HuaweiS.get_request_esn_full_command()
        else:
            command, kwargs['expect_string'], kwargs['prompt'] = HuaweiCE.get_request_esn_full_command()
        self._logger.debug(
            f"For requesting full ESN information: platform is {platform}, " + \
            f"command - '{command}', expect_string = '{kwargs['expect_string']}', prompt = '{kwargs['prompt']}'")
        return command, kwargs

    def request_esn_full(self):
        """Request ESN of all boards and SFP modules using command 'display elabel'

        Return:
            [list of dict] -- List of dictionaries containing information about ESN, for example:
                                [{'bar_code': '21980107682SJC600039',
                                'board_type': 'S5720-28P-LI-AC',
                                'description': 'S5720-28P-LI-AC(24 Ethernet 10/100/1000 ports,4 Gig SFP,AC '
                                'power support,overseas)',
                                'item': '98010768',
                                'manufactured': '2018-12-19'}]
        """
        command, command_kwargs = self.get_command_display_esn_full()
        self.log_info_requesting('ESN full', command + ' & ' + str(command_kwargs))
        output = self.send_command(command, **command_kwargs)
        esn_boards = self._return_esn_full(output)
        self.log_info_requested('ESN full', esn_boards, command + ' & ' + str(command_kwargs))
        return esn_boards

    ''' HARDWARE - boards'''
    def get_regex_request_boards_list(self, flag_all_boards):
        """ Return regular expression for searching information about all boards
            according to the hardware plaform type

        Returns:
            [string] -- Regular expression
        """
        platform = self.hardware_platform
        if platform == 'CE':
            regex = HuaweiCE.get_regex_request_boards_list(flag_all_boards)
        elif platform == 'S':
            regex = HuaweiS.get_regex_request_boards_list(flag_all_boards)
        else:
            regex = None
            #self._logger.error(f"Can't determine regex for Boards List host {str(self)}, platform {platform}")

        self._logger.debug(
            f"Determined regex '{regex}' for platform '{platform}, all_boards={flag_all_boards}")
        return regex

    def _return_boards_list(self, regex, output_display_device):
        """Look for information about boards type using regex in output of 'display device' command

        Arguments:
            output_display_device {string} -- Output of command for requesting information about boards

        Returns:
            [list of dict] -- List of boards in format [{'index': '1', 'type': 'CE-L12CQ-FD'}] 

        """        
        boards = []
        matches = re.finditer(regex, output_display_device)
        try:
            for match in matches:
                board = {
                    'index' : match.group('index'),
                    'type' : match.group('type')}
                    #'sn':   match.group('sn')}
                boards.append(board)
            self.log_match_found('Boards List', boards, regex, output_display_device)
            return boards
        except Exception:
            self.log_match_error('Boards List', regex, output_display_device)
            return boards

    @staticmethod
    def get_main_boards_only(boards_list):
        """ Return list of MPU/SFU/LPU boards only from list of all boards

        Arguments:
            boards_list {list of str} -- List of all boards including Power and Fan modules

        Returns:
            [list] -- list of main boards only
        """        
        boards = []
        for board in boards_list:
            try:
                int(board['index'])
                boards.append(board)
            except ValueError:
                pass
        return boards

    def request_all_boards_list(self, printable=False):
        # ! TODO
        boards = self.get_command_and_regex_boards_esn(flag_all_boards=True)
        if printable:
            return [str(board['index']) + ' - ' + str(board['type']) for board in boards]
        else:
            return boards

    def request_boards_list(self, printable=False, flag_all_boards=False):
        """Request list of all boards using command 'display device'

        Keyword Arguments:
            # ! TODO: change this behaviour of returning different variable type
            printable {bool}  -- if True - return list of string in format ['1 - LPUTYPE1', '2 - LPUTYPE2']
            flag_all_boards {bool} -- If True - return FAN and PWR boards too. (default: {False})

        Returns:
            [list of dict] -- List of boards in format {'index': '1', 'type': 'CE-L12CQ-FD'}
        """
        regex = self.get_regex_request_boards_list(flag_all_boards)
        self.log_info_requesting(f'Boards list (all_boards={flag_all_boards})', DISPLAY_DEVICE)
        output = self.send_command(DISPLAY_DEVICE)
        boards_list = self._return_boards_list(regex, output)
        self.log_info_requested(f'Boards list (all_boards={flag_all_boards})', boards_list, DISPLAY_DEVICE)
        if len(boards_list) < 2:
            return []
        if printable:
            return [str(board['index']) + ' - ' + board['type'] for board in boards_list]
        else:
            return boards_list

    ''' MAC Summary '''
    def get_regex_request_mac_summary(self):
        """Return regular expression for searching information about current mac summary

        Returns:
            [string] -- Regular expression
        """        
        platform = self.hardware_platform
        if platform == 'CE':
            regex_boards = HuaweiCE.get_regex_request_mac_summary()
        elif platform == 'S':
            regex_boards = HuaweiS.get_regex_request_mac_summary()
        else:
            regex_boards = ''
            self._logger.error(f"Can't determine regex for requesting MAC Summary host {str(self)}, platform {platform}")
        return regex_boards

    def _return_mac_summary(self, output_display_mac_sumamry):
        """ Look for information about current MAC addresses summary using regex 
            in output of 'display mac-address summary' command

        Arguments:
            output_display_mac_sumamry {string} -- Output of command 'display mac-address summary'

        Returns:
            [dict] -- Information about MAC usage summary in format {'capacity': 32000, 'in_used': '435'}
        """        
        regex = self.get_regex_request_mac_summary()
        match = re.search(regex, output_display_mac_sumamry)
        try:
            result = {
                'capacity': match.group('capacity'),
                'in_used': match.group('in_used')}
            self.log_match_found('MAC Summary', result, regex, output_display_mac_sumamry)
            return result
        except AttributeError:
            self.log_match_error('MAC Summary', regex, output_display_mac_sumamry)
            return {}
        except IndexError:
            self.log_match_error('MAC Summary', regex, output_display_mac_sumamry)
            return {}
        except Exception:
            self.log_match_error('MAC Summary', regex, output_display_mac_sumamry)
            return {}

    def request_mac_summary(self):
        """ Request information about MAC summary using command 'display mac-address summary'

        Returns:
            [dict] -- Information about MAC usage summary in format {'capacity': 32000, 'in_used': '435'}
        """        
        self.log_info_requesting('MAC Summary', DISPLAY_MAC_SUMMARY)
        mac_summary = self._return_mac_summary(
            self.send_command(DISPLAY_MAC_SUMMARY))
        self.log_info_requested('MAC Summary', mac_summary, DISPLAY_MAC_SUMMARY)
        return mac_summary

    ''' Access-users summary '''
    def get_command_and_regex_dot1x_users(self):
        """ Return command and regular expression for searching information about dot1x users
            according to the hardware plaform type

        Returns:
            [str] -- command
            [str] -- regular expression
        """        
        if self.hardware_platform == 'S':
            command, regex = HuaweiS.get_command_and_regex_dot1x_users()
            self._logger.debug(
                f"Determined for requesting Dot1x users: command '{command}', " + \
                f"regex '{regex}' for hardware {self.hardware}") 
            return command, regex
        else:
            self._logger.info(f"Can't request 802.1x users info for non-S series switches")
            return None, None

    def get_command_and_regex_mac_users(self):
        """ Return command and regular expression for searching information about MAB users
            according to the hardware plaform type

        Returns:
            [str] -- command
            [str] -- regular expression
        """    
        if self.hardware_platform == 'S':
            command, regex = HuaweiS.get_command_and_regex_mac_users()
            self._logger.debug(
                f"Determined for requesting MAB users: command '{command}', " + \
                f"regex '{regex}' for hardware {self.hardware}") 
            return command, regex
        else: 
            self._logger.info(f"Can't request MAC users info for non-S series switches")
            return None, None
            
    def _return_mab_users_number(self, regex, output_display_access_user):
        """ Look for information about MAB clients using regex in output

        Arguments:
            regex {str} -- Regular Expression
            output_display_access_user {str} -- output of command 'display access-user ...'

        Returns:
            [int] -- Number of MAB clients
        """        
        match = re.search(regex, output_display_access_user)
        try:
            users_number = int(match.group('total'))
            self.log_match_found('MAB users', users_number, regex, output_display_access_user)
            return users_number
        except AttributeError:
            if 'No online user' in output_display_access_user:
                return 'No one'
            else:
                self.log_match_error('MAB users', regex, output_display_access_user)
                return "N/A"

    def request_mab_users_number(self):
        """ Request information about clients authenticated using MAC address

        Returns:
            [int] -- Number of MAB clients
        """        
        command, regex = self.get_command_and_regex_mac_users()
        self.log_info_requesting('MAB users', command)
        if not command or not regex:
            return ''
        output = self.send_command(command)
        users_number = self._return_mab_users_number(regex, output)
        self.log_info_requested('MAB users', users_number, command)
        return users_number

    def _return_dot1x_users_number(self, regex, output_display_access_user):
        """ Look for information about 802.1x clients using regex in output

        Arguments:
            regex {str} -- Regular Expression
            output_display_access_user {str} -- output of command 'display access-user ...'

        Returns:
            [int] -- Number of 802.1x clients
        """ 
        match = re.search(regex, output_display_access_user)
        try:
            users_number = int(match.group('total'))
            self.log_match_found('Dot1x users', users_number, regex, output_display_access_user)
            return users_number
        except AttributeError:
            if 'No online user' in output_display_access_user:
                return 'No one'
            else:
                self.log_match_error('Dot1x users', regex, output_display_access_user)
                return "N/A"

    def request_dot1x_users_number(self):
        """ Request information about clients authenticated using 802.1x

        Returns:
            [int] -- Number of 802.1x clients
        """      
        command, regex = self.get_command_and_regex_dot1x_users()
        self.log_info_requesting('Dot1x users', command)
        if not command or not regex: 
            return ''
        output = self.send_command(command)
        users_number = self._return_dot1x_users_number(regex, output)
        self.log_info_requested('Dot1x users', users_number, command)
        return users_number

    def request_access_users_number(self):
        """ Request information about clients authenticated using 802.1x or MAB

        Returns:
            [dict of str] -- information about number of clients in format:
                            {
                                'dot1x_users_number':   300,
                                'mab_users_number': 200
                            }
        """        
        return {
            'dot1x_users_number': self.request_dot1x_users_number(),
            'mab_users_number': self.request_mab_users_number()
        }

    ''' Routes '''
    def _return_regex_search_result(self, text, regex, group_name):
        """ Search any information using Regular Expression 'regex' in any output 'text'.

        Arguments:
            text {str} -- any output in which searching will be done
            regex {str} -- regular expression for matching
            group_name {str} -- group name (regex should contain groups)

        Returns:
            [str] -- result of found information
        """        
        match = re.search(regex, text)
        try:
            result = match.group(group_name)
            self.log_match_found(group_name, result, regex, text)
            return result
        except AttributeError:
            self.log_match_found(group_name, '0', regex, text)
            return 0
        except Exception:
            self.log_match_error(group_name, regex, text)

    def request_all_vrf_routes_number(self):
        """Request information about total number of routes using command 
            'display ip routing-table all-vpn-instance statistics'
        
        Returns:
            [dict] -- information about number of routes for different routing protocols
        """
        self.log_info_requesting('all-vpn-instances routes number', DISPLAY_ROUTES_SUMMARY)        
        output = self.send_command(DISPLAY_ROUTES_SUMMARY)
        total_routes = {}
        for key in REGEX_ROUTES_SUMMARY:
            total_routes[key] = self._return_regex_search_result(
                output,
                REGEX_ROUTES_SUMMARY[key],
                'routes_number')
        self.log_info_requested('all-vpn-instances routes number', total_routes, DISPLAY_ROUTES_SUMMARY)
        # (Total, Direct, Static, OSPF, IS-IS, BGP)
        return total_routes
    
    ''' VRF '''
    def _return_total_number_vrf(self, output_display_ip_vpn_instances):
        """ Look for information about Total number of VPN-instances using Regula expressions
            in output of 'display ip vpn-instance' commmand

        Arguments:
            output_display_ip_vpn_instances {str} -- output of 'display ip vpn-instance' commmand

        Returns:
            [int] -- total number of VPN-istances
        """        
        regex = 'Total VPN-Instances configured\s+:\s*(?P<number>\d+)'
        match = re.search(regex, output_display_ip_vpn_instances)

        try:
            result = int(match.group('number'))
            self.log_match_found('Total VPN-Instances', result, regex, output_display_ip_vpn_instances)
            return result
        except AttributeError:
            if not output_display_ip_vpn_instances:
                return 0
            else:
                self.log_match_error('Total VPN-Instances', regex, output_display_ip_vpn_instances)
                return 'N\A'

    def request_all_vrf_list(self):
        """ Request information about all VPN-instances using command 'display ip vpn-instance'

        Returns:
            [list of str] -- names of VPN-instances
        """        
        self.log_info_requesting('all VRF list', DISPLAY_IP_VRF)
        output = self.send_command(DISPLAY_IP_VRF)
        regex = r'\n\s*(?P<vrf_name>\S+)\s+.*?\s+IPv'
        vrf_list = []

        matches = re.finditer(regex, output)
        for m in matches:
            vrf_list.append(
                m.group('vrf_name'))
        result_text = f'VRF: {str(self._return_total_number_vrf(output))}: ' + ', '.join(vrf_list)
        self.log_info_requested('all VRF list', result_text, DISPLAY_IP_VRF)
        return result_text

    ''' Memory '''
    def get_command_and_regex_memory(self):
        """ Return command and regular expression for requesting information about memory usage
            according to the hardware platform type (CE/S/AR/NE)

        Returns:
            [str] -- command
            [str] -- regular expression
        """        
        platform = self.hardware_platform
        if platform == 'CE':
            command, regex = HuaweiCE.get_command_and_regex_memory()
        elif platform == 'S':
            command, regex = HuaweiS.get_command_and_regex_memory()
        else:
            command, regex = None, None
            self._logger.error(f"Can't determine regex for requesting MAC Summary host {str(self)}, platform {platform}")
        return command, regex

    def __return_memory_usage_percentage(self, regex, output_display_memory):
        """ Look for information about memory usage using regex in output of 
            'display memory' command

        Arguments:
            regex {str} -- regular expression
            output_display_memory {str} -- output of 'display memory' command

        Returns:
            [int] -- percent of memory usage
        """        
        match = re.search(regex, output_display_memory)
        try:
            memory_usage = int(match.group('usage_percent'))
            self.log_match_found('Memory usage', memory_usage, regex, output_display_memory)
            return memory_usage
        except AttributeError:
                self.log_match_error('Memory usage', regex, output_display_memory)
                return "N/A"

    def request_memory_usage_percentage(self):
        """Request information about memory usage using 'display memory'

        Returns:
            [int] -- memory usage percentage
        """        
        command, regex = self.get_command_and_regex_memory()
        if not command or not regex: 
            self.log_not_requsting('Memory usage', self.hardware_platform)
            return ''
        self.log_info_requesting('Memory usage', command)
        output = self.send_command(command)

        memory_usage = self.__return_memory_usage_percentage(regex, output)
        
        self.log_info_requested('Memory usage', memory_usage, command)
        return memory_usage

    ''' CPU '''
    # ! TODO

    ''' Loopbacks '''
    def request_loobacks(self):
        # ! TODO
        return

    ''' Logging '''
    def log_match_found(self, attribute_name, attribute, regex, output):
        self._logger.debug(f"Got {attribute_name} '{str(attribute)}' using regex '{regex}'' from output \n{output}")

    def log_match_error(self, attribute_name, regex, output):
        self._logger.error(f"Can't get {attribute_name} using regex '{regex}'' from output \n{output}", exc_info=True)

    def log_not_requsting(self, attribute_name, platform):
        self._logger.debug(f"{self} - Not requestings {attribute_name} for host {str(self)}, platform '{platform}'")

    def log_info_requesting(self, attribute_name, command=''):
        self._logger.debug(f"{self} - Requesting {attribute_name} for host {str(self)} using command '{command}'")

    def log_info_requested(self, attribute_name, attribute, command=''):
        self._logger.info(f"{self} - Requested {attribute_name} = '{attribute}' using command '{command}'")
