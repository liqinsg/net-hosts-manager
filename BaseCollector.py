#!/usr/bin/python3

import concurrent
import logging
import os
import re
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from datetime import datetime
from getpass import getpass
from itertools import repeat
from sys import argv

from BaseSSH import BaseSSH
from HuaweiSSH import HuaweiSSH
from LoggingSettings import LoggingSettings

__author__ = 'Ravil Shamatov, ravil.shamatov@huawei.com, rav.shamatov@gmail.com'
SCRIPT_DESCRIPTION = f"""This is Collector that run list of commands on each remote machine from list of SSH hosts. 
Author: {__author__}. Version: 2020-04-01"""

DEVICES_LST_LINE_REGEX = r'(?P<hostname>\S+)\s*,\s*(?P<ipv4_address>\d+\.\d+\.\d+\.\d+).*'

HOSTS_FILENAME = 'devices.lst'
COMMANDS_FILENAME = 'commands.lst'
LOGFILE_EXTENSION = 'log'
LOGS_FOLDER = 'data'
MODULE_LOGGER_NAME = 'BaseCollector'
WRITE_OUTPUT_MODE = 'w'
THREADS_NUMBER = 20
LINE_DELIMETER = '='*80

COLLECTOR_LOG_FILENAME = 'collector.log'

DEFAULT_LOGGING_SETTINGS = {
    'parent_logger' : None,
    'propagate' : True,
    'debugging': True,
    'verbose': True,
    'mode': None,
    'logger_name': MODULE_LOGGER_NAME,
    'log_filename_extension' : LOGFILE_EXTENSION,
    'log_directory': LOGS_FOLDER,
    'log_write_mode': 'a'
}


class BaseCollector():
    """ Represents Collector for Huawei devices (collecting data about software, hardware, etc.)"""

    _logger = logging.getLogger('BaseCollector')
    _username = ''         # Username for SSH connections
    _password = ''         # Password for SSH connections
    #_collector_logger = None  # logging.Logger class  
    log_settings = {} # LoggingSettings.get_default_settings()
    host_log_settings = {} #LoggingSettings.get_default_settings()

    def __init__(self, **settings): 
        """Create BaseCollector object
        """
        self.apply_config_file(settings['config_file'])
        self.apply_argument_settings(settings)
        self._logger = LoggingSettings.get_logger(**self.log_settings)
        self.host_log_settings['parent_logger'] = self._logger

        #self.set_username_password(username)
        self.log_logging_configuration()
        if settings['login_name']:
            self.password = getpass()

        self.check_log_directory(self.log_settings['log_directory'])
        self.check_log_directory(self.host_log_settings['log_directory'])

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        if username:
            self._username = username
            self._logger.debug(f"Set username {self.username}.")
        else:
            self._logger.error(f"Tried to set empty username '{username}'.")

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        if password:
            self._password = password
            self._logger.debug(f"Set password.")
        else:
            self._logger.error(f"Tried to set empty username '{password}'")

    @property
    def default_device_type(self):
        return self._default_device_type

    @default_device_type.setter
    def default_device_type(self, device_type):
        if device_type:
            self._default_device_type = device_type
            self._logger.error(f"Set default Netmiko device type '{device_type}'")
        else: 
            self._logger.error(f"Tried to set empty device_type '{device_type}'")

    ''' Apllying settings '''
    def apply_argument_settings(self, settings):
        
        self.hosts_filename = settings['devices_file'] or self.hosts_filename
        self.commands_filename = settings['commands_file'] or self.commands_filename
        self.threads_number = settings['threads'] or self.threads_number
        self.username = settings['login_name'] or self.username
        self.default_device_type = settings['device_type']
        self.log_settings['logger_name'] = settings['log_file'] or self.log_settings['logger_name'] 
        self.log_settings['log_directory'] = settings['logs_directory'] or self.log_settings['log_directory'] 
        self.host_log_settings['log_directory'] = settings['logs_directory'] or self.host_log_settings['log_directory']
        self.set_logging_levels(settings['verbose'])

    def set_logging_levels(self, count):
        """ Set logging settings according key argument of script
        
        Arguments:
            count {int} -- verbose leve:
            # ! - V - Collector (console-WARNING, file-DEBUG), Hosts (console-WARNING, file-INFO)
            # ! - VV - Collector (console-INFO, file-DEBUG), Hosts (console-INFO, file-INFO)
            # ! - VVV - Collector (console-DEBUG, file-DEBUG), Hosts (console-DEBUG, file-INFO)
        """
        if count == 0:
            self.log_settings['log_console_level'] = logging.ERROR
            self.log_settings['log_file_level'] = logging.INFO
            self.host_log_settings['log_file_level'] = logging.WARNING
        if count == 1:
            self.log_settings['log_console_level'] = logging.WARNING
            self.log_settings['log_file_level'] = logging.INFO
            self.host_log_settings['log_file_level'] = logging.WARNING
        elif count == 2:
            self.log_settings['log_console_level'] = logging.INFO
            self.log_settings['log_file_level'] = logging.DEBUG
            self.host_log_settings['log_file_level'] = logging.INFO
        elif count == 3:
            self.log_settings['log_console_level'] = logging.DEBUG
            self.log_settings['log_file_level'] = logging.DEBUG
            self.host_log_settings['log_file_level'] = logging.DEBUG
           
    def log_logging_configuration(self):
        """Log about all configuration that applied for this Collector

        """        
        self._logger.debug(f'Applied logging settings {self.log_settings}')
        self._logger.error(
            f"\nCommon collector settings:\n" + \
            f"\tHosts_File_Name = '{self.hosts_filename}'\n" + \
            f"\tCommands_File_Name = '{self.commands_filename}'\n" + \
            f"\tThreads_Number = '{self.threads_number}'\n" + \
            f"\tUsername = '{self.username}'\n" + \
            f"\tNetmiko device type: '{self.default_device_type}'\n" + \
            f"\tWriting logs mode (script/host) = " + \
            f"{self.log_settings['log_write_mode']}/{self.host_log_settings['log_write_mode']}")
        #self._logger.debug(f"\tPassword: '{self._password}'")
        self._logger.info(f"\tLogging Handlers = '{self._logger.handlers}'")
        self._logger.error('')
        self._logger.debug(f'Applied hosts logging settings {self.host_log_settings}')
        self._logger.debug(f"Logging handlers: '{self._logger.handlers}'")

    def check_log_directory(self, path):
        """Check if Directory exists. If not - create directory.
        # ! Add supprint both Windows&Linux paths
        
        Arguments:
            path {string} -- path to directory
        """        
        if not os.path.isdir(path):
            os.mkdir(path)
            self._logger.debug(f"Created folder '{path}'")
        else:
            self._logger.debug(f"Directory '{path}' exists")

    def apply_config_file(self, config_filename):
        """Read, parse and apply configuration file
        
        Arguments:
            config_filename {str} -- path to file including filename
        """                
        config = ConfigParser()
        print(f"Reading configuration from file '{config_filename}'")
        try:
            config.read(config_filename)
            self.apply_config_file_logging(**config['Collector_Log_Settings'])
            self.apply_config_file_collector(**config['Collector_Settings'])
            self.apply_config_file_host(**config['Hosts_Log_Settings'])

            self.check_log_directory(self.log_settings['log_directory'])
            self.check_log_directory(self.host_log_settings['log_directory'])
        except Exception as e:
            print(e)

    def apply_config_file_collector(self, **settings):
        """Apply common collector settings
        """        
        self.hosts_filename = settings['hosts_file_name']
        self.hosts_file_regex = settings['hosts_file_regex']
        self.hosts_file_fomment_sign = settings['hosts_file_comment_sign']
        self.commands_filename = settings['commands_file_name']
        self.threads_number = int(settings['threads_number'])
        self.username = settings['username'] 
        self.password = str(settings['password'])

    def apply_config_file_logging(self, **settings):
        """Apply logging collector settings
        """        
        self.log_settings['logger_name'] = settings['log_file_name']
        self.log_settings['log_filename_extension'] = settings['log_file_extension']
        self.log_settings['log_directory'] = settings['log_directory']
        self.log_settings['propagate'] = settings['propagate']
        self.log_settings['log_write_mode'] = settings['log_write_mode']
        self.log_settings['log_file_level'] = BaseCollector.get_logging_level_from_cfg_string(
            settings['log_file_level'])
        self.log_settings['log_console_level'] = BaseCollector.get_logging_level_from_cfg_string(
            settings['log_console_level'])
        self.log_settings['mode'] = None
        
    def apply_config_file_host(self, **settings):
        """Apply logging settings for connections to remote machines
        """        
        self.host_log_settings['log_filename_extension'] = settings['log_file_extension']
        self.host_log_settings['log_directory'] = settings['log_directory']
        self.host_log_settings['log_write_mode'] = settings['log_write_mode']
        self.host_log_settings['mode'] = settings['log_format']
        self.host_log_settings['command_line_delimeter'] = settings['command_line_delimeter']
        self.host_log_settings['command_line_intend'] = int(settings['command_line_intend'])
        self.host_log_settings['log_file_level'] = BaseCollector.get_logging_level_from_cfg_string(
            settings['log_file_level'])

    @staticmethod
    def get_logging_level_from_cfg_string(word):
        levels = {
            'debug': logging.DEBUG,
            'info' : logging.INFO,
            'warning' : logging.WARNING,
            'error' : logging.ERROR,
            'critical': logging.CRITICAL}
        try:
            return levels[word]
        except KeyError:
            print(f"""Unknown logging level '{word}'. Possible levels: 
                'debug, 'info', 'warning', 'error', 'critical'""")

    ''' RUNNING COLLECTOR '''
    def run_for_device(self, host_info, commands):
        """For host {host_info} run every command from list {commands}
        
        Arguments:
            host_info {dict of string} -- information about host in format
                             {'hostname': 'SL1', 'mgmt_ip': '10.198.177.17'}
            commands {list of string} -- list of commands in format ['disp ver', 'disp clock']
        """        
        # If no one command - don't attempt to innizialize SSH session
        if not commands:
            return
        # Inizialize SSH session
        self._logger.debug(
            f"Trying to create host '{host_info}' and logging settings {self.host_log_settings}")
        ssh_host = BaseSSH(
            host_info['mgmt_ip'], 
            host_info['hostname'],
            self.host_log_settings)
        ssh_host.connect_ssh(self.username, self._password, nmiko_device_type=self.default_device_type)
        if ssh_host.ssh_lib_type:
            for cmd in commands:
                ssh_host.send_command(cmd)
            self._logger.warning(f"Host {str(ssh_host)}\t- Done")     
        # Close SSH session.
        ssh_host.disconnect_ssh()

    def run(self, function, hosts, args=None):
        """Run function for every host from hosts using arguments {args}
        
        Arguments:
            function {func} -- Function that should be run
            hosts {iter of dict} -- List of hosts
        
        Keyword Arguments:
            args {tuple} -- Arguments for running function (default: {None})
        """        
        with concurrent.futures.ThreadPoolExecutor(self.threads_number) as executor:
            for host in hosts:
                if args:
                    self._logger.debug(
                        f"Runing function {function} for host '{host}' and args '{args}'")
                    executor.submit(function, host, args)
                else: 
                    self._logger.debug(
                        f"Runing function {function} for host '{host}' and without args")
                    executor.submit(function, host)

    def run_for_files(self, hosts_filename='', commands_filename=''):
        """Run commands from file {commands_filename} for every host from file {hosts_filename}
        
        Keyword Arguments:
            hosts_filename {string} -- filename for devices (default: {HOSTS_FILENAME})
            commands_filename {[type]} -- filename for commands (default: {COMMANDS_FILENAME})
        """
        self.hosts_filename = hosts_filename or self.hosts_filename
        self.commands_filename = commands_filename or self.commands_filename

        commands = BaseCollector.get_commands_from_file(self.commands_filename)
        self._logger.info(
            f"Starting Collector for user {self.username} {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}, " + \
            f"devices file '{self.hosts_filename}', commands file '{self.commands_filename}', " + \
            f"threads number {self.threads_number}, device_type: '{self.default_device_type}'")
        self.run(
            self.run_for_device,
            BaseCollector.iter_hosts_from_file(
                self.hosts_filename, 
                self.hosts_file_regex,
                self.hosts_file_fomment_sign),
            commands
        )
        self._logger.info(
            f"Stopped Collector for user user {self.username} {datetime.today().strftime('%Y-%m-%d %H:%M:%S')} " + \
            f"devices file '{self.hosts_filename}', commands file '{self.commands_filename}'")

    def set_start_timer(self):
        self.start_time = datetime.now()

    def get_duration_seconds(self):
        return datetime.now() - self.start_time
    
    ''' Getting information from files '''
    @staticmethod
    def get_commands_from_file(filename):
        return [line.strip() for line in open(filename, 'r')]

    @staticmethod
    def get_host_from_line(line, regex, comment_sign):
        """Return information about device from line
        
        Arguments:
            line {string} -- line that should be checkced
        
        Returns:
            dict of string -- Information about device in format 
                    {'hostname': 'SL1', 'mgmt_ip': '10.198.177.17'}
        """        
        if line.startswith('#'):
            return
        match = re.search(regex, line)
        try:
            return {
                'hostname': match.group('hostname'),
                'mgmt_ip': match.group('ipv4_address')
                }
        except AttributeError:
            # print(f'Not found information about IPv4 in this line: {line.strip()}')
            return

    @staticmethod
    def get_hosts_from_file(filename, regex=DEVICES_LST_LINE_REGEX, comment_sign='#'):
        """Read every line of file and return list of devices
        
        Keyword Arguments:
            filename {string} -- filename that must be read (default: 'devices.lst')
        
        Returns:
            list of dict -- Devices in format: [{'hostname': 'SL1', 'mgmt_ip': '10.198.177.17'}]
        """        
        host_list = []
        with open(filename, 'r') as f:
            for line in f.readlines():
                host = BaseCollector.get_host_from_line(line, regex, comment_sign)
                if host: 
                    host_list.append(host)
        return host_list
    
    @staticmethod
    def iter_hosts_from_file(filename, regex=DEVICES_LST_LINE_REGEX, comment_sign='#'):
        """Iterate over every line and return information about host one by one
        
        Keyword Arguments:
            filename {string} -- filename that must be read (default: 'devices.lst')
        
        Yields:
            iter of dict -- Iterator over hosts, every host format:
                        {'hostname': 'SL1', 'mgmt_ip': '10.198.177.17'}
        """        
        with open(filename, 'r') as f:
            for line in f.readlines():
                host = BaseCollector.get_host_from_line(line, regex, comment_sign)
                if host:
                    yield host
                else: 
                    pass

    ''' Script arguments '''
    @staticmethod
    def parse_arguments():
        parser = ArgumentParser(description=SCRIPT_DESCRIPTION)
        parser.add_argument('-F','--config_file',help='Alternative per-user configuration file',required=False, default='collector_huawei.ini')
        parser.add_argument('-d','--devices_file',help='Filename of devices list',required=False)
        parser.add_argument('-c','--commands_file',help='Filename of commands list',required=False)
        parser.add_argument('-dt','--device_type',help='Netmiko device_type',required=False, default='huawei')
        parser.add_argument('-V','--verbose',action='count', default=0)
        parser.add_argument('-t','--threads',help='Number of threads',required=False,default=0)
        parser.add_argument('-l','--login_name',help='Specifies the user to log in as on the remote machine',required=False)
        parser.add_argument('-E','--log_file',help='Log filename of collector',required=False)
        parser.add_argument('-L','--logs_directory',help='Directory for logs',required=False)
        parser.add_argument('-a','--append_log_mode',action='store_true',help='Append to logs, not to rewrite',required=False)
        parser.add_argument('-w','--write_log_mode',action='store_true',help='Rewrite logs, not to append',required=False)
        parser.add_argument('-R','--report_filename',help='Report filename',required=False)
        return parser.parse_args()

    @staticmethod
    def get_script_arguments(args):
        settings = {}
        settings['config_file'] = args.config_file
        settings['devices_file'] = args.devices_file or None
        settings['commands_file'] = args.commands_file or None
        settings['device_type'] = args.device_type or None
        settings['verbose'] = args.verbose
        settings['threads'] = args.threads
        settings['login_name'] = args.login_name or None
        settings['log_file'] = args.log_file or None
        settings['logs_directory'] = args.logs_directory or None
        settings['report_filename'] = args.logs_directory or None
        if args.write_log_mode:
            settings['Log_Write_Mode'] = 'w'
        elif args.append_log_mode:
            settings['Log_Write_Mode'] = 'a'
        
        return settings

    @staticmethod
    def main():
        """Main function 
        """        
        # ! Finish all key arguments of script
        settings = BaseCollector.get_script_arguments(
            BaseCollector.parse_arguments())
        collector = BaseCollector(**settings)
        # Check how much time it took to execute this script
        collector.set_start_timer()
        collector.run_for_files()
        collector._logger.warning(f'\nIt took {collector.get_duration_seconds()} seconds')


if __name__ == '__main__':
    BaseCollector.main()
