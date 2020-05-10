#!/usr/bin/python3

import ipaddress
import logging
from argparse import ArgumentParser
from datetime import datetime
from getpass import getpass
from os import system
from sys import platform
from time import sleep, strftime, time
import re

import paramiko
from LoggingSettings import LoggingSettings
from netmiko import ConnectHandler
from netmiko.ssh_exception import (NetMikoAuthenticationException,
                                   NetMikoTimeoutException)

SSH_LIB_PARAMIKO = 'paramiko'
SSH_LIB_NETMIKO = 'netmiko'
SSH_SENDING_COMMAND_TIMEOUT_SEC = 0.5

PARAMIKO_DEFAULT_BUFFER_LENGTH = 4000

MODULE_LOGGER_NAME = 'SshConnections'
LOGFILE_EXTENSION = 'log'
LOGS_FOLDER = 'LOGS'
LOG_DIRECTORY = 'data'
DEFAULT_LOGGING_SETTINGS = {
    'parent_logger': None,
    'propagate': True,
    'debugging': False,
    'verbose': False,
    'mode': None,
    'logger_name': MODULE_LOGGER_NAME,
    'log_filename_extension': LOGFILE_EXTENSION,
    'log_directory': LOGS_FOLDER
}


class BaseSSH(object):
    """Represents and manipulate single Network Host with remote SSH access."""

    _ip_address = ''           # Type: an IPv4Address (module ipaddress)
    _hostname = ''             # Type: string. Represents configured on this device hostname, not resolved via DNS
    __vendor = ''               # Type: string.
    __os_version = ''           # Type: string.
    _uptime = ''               # Type: string

    _ssh_lib_type = None          # Type: SSH_LIB_PARAMIKO or SSH_LIB_NETMIKO
    _logger = None

    def __init__(self, ipv4, hostname='', logger_settings={}):
        """
        Arguments:
            ipv4 {str} -- IPv4

        Keyword Arguments:
            hostname {str} -- hostname (default: {''})
            logger_settings {dict} --
                            {
                                'parent_logger' : None,     # parent logger if exists
                                'propagate': True,
                                'mode': None,               # 'collector' or None
                                'logger_name': '',
                                'log_file_level': logging.INFO,
                                'log_console_level': logging.WARNING,
                                'log_filename_extension' : 'log',
                                'log_directory': 'LOGS',
                                'log_write_mode': 'a'
                            }
        """
        # Setting default logging settings
        self.logger_settings = {**LoggingSettings.get_default_settings(), **logger_settings}
        try:
            self.ip_address = ipv4
            self.hostname = hostname
            # Configuring logging
            self.logger_settings['logger_name'] = str(self)
            self._logger = LoggingSettings.get_logger(**self.logger_settings)
            # Log about createing object
            self.log_event_debug(
                f"Object BaseSSH has been created for {str(self)} " + \
                f"with logger {self._logger}, level {self._logger.level}, handlers {self._logger.handlers}")
        except ipaddress.AddressValueError as e:
            self.hostname = ipv4
            if self.logger_settings['parent_logger']:
                self.logger_settings['parent_logger'].error(
                    f"BaseSSH {str(self)} - wrong IP address, exception '{e}'")
        except Exception as e:
            if self.logger_settings['parent_logger']: 
                self.logger_settings['parent_logger'].error(
                    f"Error during creating object BaseSSH for {str(self)}: '{e}'")
            else: 
                print(f"Error during creating object BaseSSH for {ipv4}: '{e}'")

    def __str__(self):
        return self.hostname or str(self.ip_address)

    @property
    def ip_address(self):
        return str(self._ip_address)
    
    @ip_address.setter
    def ip_address(self, ipv4):
        self._ip_address = ipaddress.IPv4Address(ipv4)

    def set_hostname(self, hostname_str):
        self._hostname = hostname_str if hostname_str else self._hostname

    @property
    def hostname(self):
        return self._hostname or None

    @hostname.setter
    def hostname(self, hostname):
        self._hostname = hostname

    @property
    def os_version(self):
        return self._os_version or None

    @os_version.setter
    def os_version(self, version):
        self._os_version = version

    @property
    def hardware(self):
        return self._hardware or None

    @hardware.setter
    def hardware(self, hardware):
        self._hardware = hardware

    @property
    def uptime(self):
        return self._uptime or None
    
    @uptime.setter
    def uptime(self, uptime_str):
        self._uptime = uptime_str

    @property
    def ssh_lib_type(self):
        return self._ssh_lib_type

    @ssh_lib_type.setter
    def ssh_lib_type(self, ssh_lib):
        self._ssh_lib_type = ssh_lib

    def connect_ssh(self, 
                    username, 
                    password,
                    port=22,
                    nmiko_device_type=None):
        """Create connection to SSH Host using Paramiko or Netmiko module

        Arguments:
            username {string} -- Username for connecting via SSH
            password {string} -- Password for connecting via SSH

        Keyword Arguments:
            port {int} -- TCP port for SSH connection (default: {22})
            nmiko_device_type {string} -- device_type for Netmiko module (default: {''})
        """
        if nmiko_device_type: 
            self.connect_ssh_nmiko(username, password, port, nmiko_device_type)
        else: 
            self.connect_ssh_pmiko(username, password, port)

    def connect_ssh_nmiko(self, username, password, port, device_type=''):
        """Inizialize SSH connection using Netmiko module

        Arguments:
            username {string} -- Username for connecting via SSH
            password {string} -- Password for connecting via SSH

        Keyword Arguments:
            port {int} -- target TCP port for SSH connection (default: {22})
            device_type {string} -- Netmiko module device_type according
                        to https://github.com/ktbyers/netmiko/tree/develop/docs/netmiko (default: {''})
        """
        device_params = {
            'device_type': device_type,
            'ip': str(self.ip_address),
            'username': username,
            'password': password}
        self._logger.debug(
            f'Trying to connect using Netmiko and device_type "{device_type}"')
        try:
            self.nmiko_ssh_session = ConnectHandler(**device_params)
            self.nmiko_ssh_session.enable()
            self._ssh_lib_type = SSH_LIB_NETMIKO
            self.log_connection_status_change('Connected', 'Netmiko')
        except ValueError as e:
            self._logger.warning(f"Host{str(self)}\t- wrong IP, exception '{e}'")
        except NetMikoAuthenticationException:
            self._logger.warning(f"Host {str(self)}\t- Authentication failed")
        except NetMikoTimeoutException:
            self._logger.warning(f"Host {str(self)}\t- Timeout of connection")
        except Exception as e:
            self._logger.info(
                f"Error during connecting to host {str(self)} via SSH using Netmiko -- {e}", exc_info=True)
            self._logger.error()

    def connect_ssh_pmiko(self, username, password, port):
        """Start an interactive shell session on the SSH server using Paramiko module.  A new `.Channel`
        is opened and connected to a pseudo-terminal using the requested
        terminal type and size.

        Arguments:
            username {string} -- Username to login via SSH
            password {password} -- Password to login via SSH

        Keyword Arguments:
            port {int} -- TCP port for SSH connection. (default: {22})

        Returns:
            [.Channel] -- SSH Channel connected to the remote shell
        """
        self.pmiko_ssh_session = paramiko.SSHClient()
        self.pmiko_ssh_session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.pmiko_ssh_session.connect(
                hostname=self.ip_address,
                username=username,
                password=password,
                port=port)
        except TimeoutError:
            self._logger.error(f'No access to host {str(self)} - Timeout connection', exc_info=True)
            return
        except paramiko.ssh_exception.AuthenticationException:
            # ! Change this handling exception
            self._logger.error(f'No access to host {str(self)} - Autentication failed', exc_info=True)
            return
        
        self._ssh_lib_type = SSH_LIB_PARAMIKO
        self.log_connection_status_change('Connected', 'Paramiko')
        
        try:
            self.ssh_channell = self.pmiko_ssh_session.invoke_shell()
            sleep(0.2)
            self.log_event_info(
                'Message after successfull logging:\n' + \
                str(self.ssh_channell.recv(2000).decode('utf-8').replace('\r\n', '\n')))
            self._adjust_pmiko_ssh_screen_lenght()
        except Exception:
            self._logger.critical(
                f'Exception while trying to connect to host {self.ip_address} via SSH using Paramiko', exc_info=True)

    def send_command(self, command, **kwargs):
        """Execute SSH command on host if SSH session is established, else skip.

        Arguments:
            command {string} -- Command that should be executed in terminal

        Keyword Arguments:
            timeout {float} -- timeout in seconds (default: {0.5})
            paramiko_length {int} -- [description] (default: {4000})
            netmiko_expect_string {regexp} -- [description] (default: {r''})
            netmiko_prompt {str} -- [description] (default: {''})

        Returns:
            {str} -- Output of executed command
        """
        # import ipdb; ipdb.set_trace()
        if self.ssh_lib_type == SSH_LIB_PARAMIKO:
            return self.send_command_pmiko(command, **kwargs)
        elif self.ssh_lib_type == SSH_LIB_NETMIKO:
            return self.send_command_nmiko(command, **kwargs)
        else:
            self._logger.error(
                f"Error during executing command '{command}' for host {str(self)}", exc_info=True)
            return ''

    def send_commands(self, commands):
        """Execute list of SSH commands one by one
        
        Arguments:
            commands {list of str} -- List of commands that will be executed
        
        Returns:
            [str] -- Output after executing all commands
        """        
        output = ''
        self._logger.debug('{self} - running commands {commands}')
        for command in commands: 
            output += self.send_command(command)
        return output

    def send_command_nmiko_with_prompt(self, command, expect_string, prompt):
        """Execute SSH command on host using prompt. For example, 
        >display elabel
        Are you sure [Y/N]y

        Arguments:
            command {str} -- Command that should be executed
            expect_string {raw str} -- Regular expression that is expected (for exapmle, r'[Y/N]')
            prompt {str} -- Prompt that should be entered (for example, 'y')

        Returns:
            [str] -- Output of executed command
        """
        self.log_event_debug(
            f"Command '{command}' will be executed on host {self.ip_address} using Netmiko with prompt: " + \
            f"expect string '{expect_string}', prompt '{prompt}'")
        output = self.nmiko_ssh_session.send_command_expect(command, expect_string)
        self.log_event_debug(f'Output before prompt:\n{output}')
        output += self.nmiko_ssh_session.send_command_expect(prompt, r'\>|\]')
        self.log_event_debug(f'Output after prompt:\n{output}')
        return output

    def send_command_nmiko(self, command, **kwargs):
        """Execute command using Netmiko module if SSH connections is estalished. Else skip.

        Arguments:
            command {string} -- Command that should be executed on SSH host

        Keyword Arguments:
            delay_factor {int} -- [description] (default: {0})
            expect_string {regexp} -- [description] (default: {r''})
            prompt {str} -- [description] (default: {''})

        Returns:
            [string] -- Result of executing command
        """
        #delay_factor=0, expect_string=r'', prompt=''
        try:
            if kwargs.get('expect_string', None) and kwargs.get('prompt', None):
                self._logger.info('send_command_nmiko_with_prompt')
                output = self.send_command_nmiko_with_prompt(
                    command,
                    kwargs['expect_string'], 
                    kwargs['prompt'])
            else:
                output = self.nmiko_ssh_session.send_command(command)
            self.log_command(command, output)
            return output
        except Exception:
            self._logger.error(
                f'Exception while trying to execute {command} for host {self.ip_address}', exc_info=True)
            return ''

    def send_command_pmiko(self, command, timeout=0.5, length=4000):
        """Execute command on SSH host if SSH session is estalished. Else skip.

        Arguments:
            command {string} -- Command that should be executed.

        Keyword Arguments:
            timeout {float} -- Timeout between executing command and getting output (default: {0.5})
            length {int} -- Length of buffer (default: {4000})

        Returns:
            [string] -- Output after executing command.
        """
        try:
            self.ssh_channell.send(' ' + command + '\n')
            sleep(timeout)
            output = self.ssh_channell.recv(length).decode('utf-8').replace('\r\n', '\n')
            self.log_command(command, output)
            return output
        except AttributeError:
            if not self._ssh_lib_type:
                self.log_event_error(
                    f'Exception while trying to execute {command} for host {self.ip_address}. ' + \
                    "Tried to run command, but SSH connection hadn't been established.")
            else:
                self.log_event_error(
                    f'Exception while trying to execute {command} for host {self.ip_address}')
            return ''
    
    def get_recv_pmiko(self, timeout=0, length=4000):
        """Get output from Paramiko SSH channel
        
        Keyword Arguments:
            timeout {int} -- Timeout before getting output (default: {0})
            length {int} -- Length of output in  (default: {4000})
        """        
        try:
            output = self.ssh_channell.recv(length).decode('utf-8').replace('\r\n', '\n')
            if output: 
                self.log_command(f"Paramiko terminal output at {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}", output)
            else: 
                self._logger.debug(f"No ouptut from Paramiko channel at {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}")
            return output
        except Exception:
            self._logger.error(f"Handled exception while trying to get_recv_pmiko for host {self}", exc_info=True)

    def _adjust_pmiko_ssh_screen_lenght(self):
        # ! Write later
        pass

    def _disconnect_ssh_nmiko(self):
        """Close SSH connection that was establihsed using module Netmiko
        """
        try:
            self.nmiko_ssh_session.disconnect()
            self.ssh_lib_type = None
            self.log_connection_status_change('Disconnected', 'Netmiko')
        except Exception:
            self._logger.warning(f'Tried to close Netmiko connection, but handled Exception', exc_info=True)

    def _disconnect_ssh_pmiko(self):
        """Close SSH connection that was establihsed using module Paramiko
        """
        try:
            self.ssh_connection.close()
            self.ssh_lib_type = None
            self.log_connection_status_change('Disconnected', 'Paramiko')
        except Exception:
            self._logger.warning(f'Tried to close Paramiko connection, but handled Exception', exc_info=True)

    def disconnect_ssh(self):
        """Close SSH connection that was establihsed
        """
        if self._ssh_lib_type == SSH_LIB_NETMIKO:
            self._disconnect_ssh_nmiko()
        elif self._ssh_lib_type == SSH_LIB_PARAMIKO:
            self._disconnect_ssh_pmiko()
        # ! self._logger.disabled = True

    @property
    def change_datetime(self):
        '''Datetime that represents time of last change or getting information'''
        return datetime.today().strftime('%Y-%m-%d (%a) %H:%M:%S')

    def log_event_debug(self, msg):
        self._logger.debug(msg)

    def log_event_info(self, msg):
        self._logger.info(msg)

    def log_event_warning(self, msg):
        self._logger.warning(msg)

    def log_event_error(self, msg, exception=''):
        self._logger.error(msg, exc_info=True)

    def log_event_critical(self, msg, exception=''):
        self._logger.critical(msg)

    def log_connection_status_change(self, change, connection_mode=''):
        """Log event about changing status of SSH conection

        Arguments:
            change {str} -- type of changes ('Connected' or 'Disconnected')
            connection_mode {str} -- name of used module (Paramiko, Netmiko, etc)
        """
        line = f"{change} {datetime.today().strftime('%Y-%m-%d')} " + \
            f"at {datetime.today().strftime('%H:%M:%S')}"
        if self.logger_settings['mode'] != 'collector':
            line += f" using {self.ssh_lib_type} module"
            self._logger.warning(line)
        else:
            self._logger.propagate = False
            self._logger.warning(line)
            self._logger.propagate = True

    def log_command(self, command, output):
        """Log Command and it's Output to log handlers.

        Arguments:
            command {str} -- Command that should be executed.
            output {str} -- Output of command.
        """        
        self._logger.propagate = False
        if self.logger_settings['parent_logger']:
            self.logger_settings['parent_logger'].info(f"Host {str(self)} - Executing command '{command}'")
        if self.logger_settings['mode'] == 'collector' or self.logger_settings['mode'] == 'watcher':
            self._logger.warning(self.logger_settings['command_line_delimeter'])
            self._logger.warning(
                self.logger_settings['command_line_intend']*' ' + command)
            self._logger.warning(self.logger_settings['command_line_delimeter'])
            self._logger.warning(output + '\n\n')
        else:
            self._logger.warning(f"Executing command '{command}' using module Netmiko")
        self._logger.propagate = True

    def log_command_timestamp(self, command, output):
        # ! TODO
        return

    @staticmethod
    def clear_screen():
        """Clear terminal screen. Limitation: for Linux or Windows only.
        """        
        if platform == "linux":
            system('clear')
        elif platform == 'win32':
            system('cls')
        else: 
            print(f"Can't clear screen for OS type '{platform}'")

    ''' For using as a script '''
    @staticmethod
    def run_periodically(mgmt_ip, device_type, command, logger_settings, interval_seconds, duration_seconds):
        """Execute Command every Interval time and log result to Log handlers.

        Arguments:
            mgmt_ip {str} -- IPv4 address of host
            device_type {str} -- Netmiko device type (for example, 'huawei')
            command {str} -- Command that should be executed.
            logger_settings {dict of str} -- Logging Settings # ! Add description
            interval_seconds {int} -- Interval in seconds between time of executing command.
            duration_seconds {int} -- How long output of command should be recorded.
        """        
        host = BaseSSH(mgmt_ip, logger_settings=logger_settings)
        print(f"""
        Watching on host {mgmt_ip} ({device_type}) output of command {command}.
        Interval {interval_seconds} seconcds, Duration {BaseSSH.get_time_string(duration_seconds)}.
        Logging to {host._logger.handlers}""")
        start_time = time()
        host.connect_ssh(
            username=input('Enter username: '), 
            password=getpass(), 
            port=22, 
            nmiko_device_type=device_type)
        while time() - start_time < duration_seconds:
            BaseSSH.clear_screen()
            print(
                strftime("%a, %d %b %Y %H:%M:%S"),
                f", Last time: {BaseSSH.get_time_string(duration_seconds - time() + start_time)}",
                f", Checking every {interval_seconds} seconds")
            host.send_command(command)
            sleep(interval_seconds)

    def check_logs_and_diagnose(self, commands_before, re_event, commands_after, repeat_counts=0):
        """Check terminal logs and if 're_event' appears - run diagnose commands. 
        Everything is logged.

        Arguments:
            commands_before {list of str} -- List of Commands that should be executed just after establishing SSH connection
            re_event {raw str} -- Regular expression for checking terminal logs
            commands_after {list of str} -- List of Commands that must be executed if 're_event' appears in logs

        Keyword Arguments:
            repeat_counts {int} -- [description] (default: {0})
        """        
        self.send_commands(commands_before)
        while True: 
            output = self.get_recv_pmiko(length=3000)
            match = re.search(re_event, output)
            if match:
                self._logger.info(f"Regex '{re_event}' found at output {output}")
                self.send_commands(commands_after)
                sleep(2)
                self.get_recv_pmiko(length=10000)
                return
            sleep(1)
            print('repeat')
        return

    @staticmethod
    def parse_args():
        """Represent script arguments

        Returns:
            [namespace] -- namespace of entered arguments
        """        
        parser = ArgumentParser(description="""
        That script execute terminal command on SSH remote machine.
        Usage example: run -t 'huawei' -c 'display version' -dm 1 '10.198.177.17'
        """)
        parser.add_argument('hostname', help='IP address of remote machine')
        parser.add_argument('-t', '--device_type', help='Netmiko device_type', required=False, default=None)
        parser.add_argument('-c', '--command', help='Command that should be executed periodically', required=True)
        parser.add_argument('-l', '--login_name', help='Specifies the user to log in as on the remote machine', required=False)
        parser.add_argument('-E', '--log_file', help='Log filename of collector', required=False)
        parser.add_argument('-s', '--seconds', help='Interval in seconds', required=False, default=5)
        parser.add_argument('-m', '--minutes', help='Interval in minutes', required=False, default=0)
        parser.add_argument('-H', '--hours', help='Interval in hours', required=False, default=0)
        parser.add_argument('-dh', '--duration_hours', help='Duration in hours', required=False, default=0)
        parser.add_argument('-dm', '--duration_minutes', help='Duration in minutes', required=False, default=0)
        parser.add_argument('-ds', '--duration_seconds', help='Duration in seconds', required=False, default=0)
        parser.add_argument('-cb', '--commands_before', help='Command that should be executed just after connecting', required=False)
        parser.add_argument('-re', '--regex', help='Regular Expression that is exprected in terminal messages', required=False, default=0)
        return parser.parse_args()

    @staticmethod
    def convert_to_seconds(hours, minutes, seconds):
        interval = hours * 3600 + minutes * 60 + seconds
        return int(interval)

    @staticmethod
    def get_time_string(seconds):
        hours = int(seconds // 3600 % 24)
        minutes = int(seconds // 60 % 60)
        seconds = int(seconds % 60)
        return f"{hours}:{minutes}:{seconds}"

    @staticmethod
    def main():
        args = BaseSSH.parse_args()
        default_log_settings = {
            'log_file_level': logging.INFO,
            'log_console_level': logging.INFO,
            'log_filename_extension': 'log',
            'log_write_mode': 'a',
            'mode': 'watcher',
            'command_line_delimeter': '='*80,
            'command_line_intend': 10
        }
        if args.regex:
            host = BaseSSH(args.hostname, logger_settings=default_log_settings)
            host.log_event_info('Checkging logs and running diagnose commands')
            #host.connect_ssh_pmiko('ravil', getpass(), port=22)
            host.connect_ssh_pmiko('ravil', 'zcv23ok;', port=22)
            host.check_logs_and_diagnose(
                commands_before = args.commands_before.split(';'),
                re_event = args.regex,
                commands_after = args.command.split(';')
            )
        else: 
            interval = BaseSSH.convert_to_seconds(
                int(args.hours), int(args.minutes), int(args.seconds))
            duration = BaseSSH.convert_to_seconds(
                int(args.duration_hours), int(args.duration_minutes), int(args.duration_seconds))
            BaseSSH.run_periodically(
                args.hostname,
                args.device_type,
                args.command,
                default_log_settings,
                interval,
                duration)

if __name__ == '__main__':
    BaseSSH.main()
