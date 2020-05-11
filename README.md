# net-hosts-manager
Collecting information from network devices (routers, switches) using SSH.


**BaseSSH.py** - execute command on SSH remote machine in interval of X seconds during Y seconds.

Usage example: 

    # Run on host 192.168.0.1 command 'display version' each 5 seconds during 1 minute
    BaseSSH.py '192.168.0.1' -t 'huawei' -c 'display version' -s 5 -dm 1  

**BaseCollector.py** - execute list of the same commands on list of hosts

Usage example:

    # Run list of hosts from file 'devices.txt' 
