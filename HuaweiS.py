#!/usr/bin/python3


class HuaweiS():

    @staticmethod
    def get_lldp_neighbor_list_regex(software_version=''):
        """Return regular expression for matching all LLDP neighbors in 'display lldp neighbor' output
        
        Arguments:
            software_version {string} -- Software version informatio in format
        
        Returns:
            [string] -- Regular expression for searching information
        """        
        """ 'display lldp neighbor' output example:
            GigabitEthernet0/0/1 has 1 neighbor(s):

            Neighbor index :1
            Chassis type   :MAC address 
            Chassis ID     :dc99-14dc-de3c 
            Port ID type   :Interface name 
            Port ID        :GigabitEthernet0/0/4
            Port description    :--- To ToR-R1.3 [G0/0/1] ---
            System name         :ToR-R1
            System description  :S5720-52P-LI-AC
            Huawei Versatile Routing Platform Software
            VRP (R) software, Version 5.170 (S5720 V200R011C10SPC600)
            Copyright (C) 2000-2018 HUAWEI TECH Co., Ltd.
            System capabilities supported   :bridge router 
            System capabilities enabled     :bridge router 
            Management address type  :ipv4
            Management address value :10.198.177.101
            OID  :0.6.15.43.6.1.4.1.2011.5.25.41.1.2.1.1.1.  
            Expired time   :105s

            Port VLAN ID(PVID)  :1
            VLAN name of VLAN  1:VLAN 0001

            Auto-negotiation supported    :Yes 
            Auto-negotiation enabled      :Yes        
            OperMau   :speed(1000)/duplex(Full)

            Power port class            :PD 
            PSE power supported         :No 
            PSE power enabled           :No 
            PSE pairs control ability   :No 
            Power pairs                 :Unknown 
            Port power classification   :Unknown

            Link aggregation supported:Yes 
            Link aggregation enabled :No 
            Aggregation port ID      :0

            Maximum frame Size       :9216
        """
        return r'(?P<interface>\S+) has (?P<number_of_neighbors>\d+) neighbor.*\n\n' + \
            r'Neighbor index(.*\n)*?' + \
            r'Port ID\s+:\s*(?P<neighbor_interface>\S+)(.*\n)*?' + \
            r'System name\s+:\s*(?P<hostname>\S+)(.*\n)*?' + \
            r'System description\s+:(?P<neighbor_description>\S+)(.*\n)*?' + \
            r'Management address\s+:(?P<neighbor_mgmt_address>\S+)'

    @staticmethod
    def get_request_esn_full_command(version=''):
        """[summary]
        
        Returns:
            [string, boolean] -- [Command to request information about ESN, if promt [Y/N] is needed]
        """        
        return 'display elabel', '[Y/N]', 'y'

    @staticmethod
    def get_regex_request_boards_list(flag_all_boards, version=''):
        '''
            S5720-56C-PWR-EI-AC1's Device status:
            Slot Sub  Type                   Online    Power    Register     Status   Role
            -------------------------------------------------------------------------------
            0    -    S5720-56C-PWR-EI       Present   PowerOn  Registered   Normal   Master
                1    ES5D21VST000           Present   PowerOn  Registered   Normal   NA
                PWR1 POWER                  Present   PowerOn  Registered   Normal   NA
                PWR2 POWER                  Present   PowerOn  Registered   Normal   NA
                FAN1 FAN                    Present   PowerOn  Registered   Normal   NA
            1    -    S5720-56C-PWR-EI       Present   PowerOn  Registered   Normal   Slave
                1    ES5D21VST000           Present   PowerOn  Registered   Normal   NA
                PWR1 POWER                  Present   PowerOn  Registered   Normal   NA
                PWR2 POWER                  Present   PowerOn  Registered   Normal   NA
                FAN1 FAN                    Present   PowerOn  Registered   Normal   NA
        '''
        if flag_all_boards: 
            # ! Regexes are the same (yet)
            return r'\n(?P<index>\S*\d+)\s+' + \
                r'(?P<sub>\S+)\s+' + \
                r'(?P<type>\S+)\s+' + \
                r'(?P<online>\S+)\s+' + \
                r'(?P<power>\S+)\s+' + \
                r'(?P<register>\S+)\s+' + \
                r'(?P<status>\S+)\s+' + \
                r'(?P<role>\S+)'
        else: 
            return r'\n(?P<index>\S*\d+)\s+' + \
                r'(?P<sub>\S+)\s+' + \
                r'(?P<type>\S+)\s+' + \
                r'(?P<online>\S+)\s+' + \
                r'(?P<power>\S+)\s+' + \
                r'(?P<register>\S+)\s+' + \
                r'(?P<status>\S+)\s+' + \
                r'(?P<role>\S+)'

    @staticmethod
    def get_command_and_regex_boards_esn(flag_all_boards, hardware='', version=''):
        ''' STACK S57
            <HUAWEI> display device manufacture-info
            Slot  Sub  Serial-number          Manu-date                                     
            - - - - - - - - - - - - - - - - - - - - - -                                     
            0     -    2102353169107C800132   2011-08-24                                    
                1    021ESN1234567890       2000-01-01                                    
            3     -    2102353170107C800132   2011-08-23                                    
            4     -    2102353170107C800132   2011-08-23                                    
                1    020WYG1234567892       2010-12-02                                    
            8     -    2102353170107C800235   2000-01-01
        '''
        ''' S27/57/67
            <HUAWEI> display device manufacture-info
            Slot  Sub  Serial-number          Manu-date                                     
            - - - - - - - - - - - - - - - - - - - - - -                                     
            0     -    2102353169107C800132   2011-08-24                                    
                1    021ESN1234567890       2000-01-01
        '''
        ''' S127
            <HUAWEI> display device manufacture-info
            Slot       Sub   Serial-number            Manu-date                             
            - - - - - - - - - - - - - - - - - - - - - - - - - - -                           
            backplane  -     2102113306P0AC000005     2010-12-03                            
            2          -     030LKV10AB000005         2010-11-29                            
            5          -     020RRN10BA000206         2011-10-28                            
            8          -     020TNF10B7000040         2011-07-20                            
            9          -     020MMN10BA000052         2011-10-11                            
            11         -     030MQN10AB000028         2010-11-27                            
            12         -     020MUR6TBA600089         2011-10-16                            
            14         -     030MQR10AB000006         2010-11-29
        '''
        if flag_all_boards:
            return 'display device manufacture-info', r'\n(?P<index>\d+)\s+(?P<card>\S+)\s+(?P<type>\S+)\s+(?P<sn>\S+)'
        else:
            return 'display device manufacture-info', r'\n(?P<index>\d+)\s+(?P<card>\S+)\s+(?P<type>\S+)\s+(?P<sn>\S+)'

    @staticmethod
    def get_regex_request_mac_summary(version=''):
        '''
        Summary information of slot 0:
        -----------------------------------
        Static     :               0
        Blackhole  :               0
        Dyn-Local  :               45
        Dyn-Remote :               0
        Dyn-Trunk  :               0
        Sticky     :               0
        Security   :               0
        Sec-config :               0
        Authen     :               0
        Guest      :               0
        Mux        :               0
        Snooping   :               0
        Pre-Mac    :               0
        In-used    :               45
        Capacity   :               16384
        -----------------------------------
        '''
        return r'In-used\s+:\s+(?P<in_used>\d+)\n' + \
            r'Capacity\s+:\s+(?P<capacity>\d+)'

    @staticmethod
    def get_command_and_regex_dot1x_users(version=''):
        '''
        ------------------------------------------------------------------------------------------------------
        UserID  Username               IP address                               MAC            Status 
        ------------------------------------------------------------------------------------------------------
                                                                                                    
        ------------------------------------------------------------------------------------------------------
        Total: 53, printed: 48   
        '''
        return 'display access-user access-type dot1x', r'\n\s*Total\s*:\s*(?P<total>\d+)'

    @staticmethod
    def get_command_and_regex_mac_users(version=''):
        '''
        display access-user access-type mac-authen                    
        ------------------------------------------------------------------------------------------------------
        UserID  Username               IP address                               MAC            Status 
        ------------------------------------------------------------------------------------------------------
        ....

        ------------------------------------------------------------------------------------------------------ 
        Total: 125, printed: 125                      
        '''
        return 'display access-user access-type mac-authen', r'\n\s*Total\s*:\s*(?P<total>\d+)'

    @staticmethod
    def get_command_and_regex_memory(version=''):
        '''display memory-usage 
        Memory utilization statistics at 2019-09-20 03:25:49+00:00
        System Total Memory Is: 354418688 bytes
        Total Memory Used Is: 95378484 bytes
        Memory Using Percentage Is: 26%
        '''
        return 'display memory-usage', r'\n\s*Memory Using Percentage Is\s*:\s*(?P<usage_percent>\d+)%'