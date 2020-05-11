#!/usr/bin/python3


class HuaweiCE():

    @staticmethod
    def get_lldp_neighbor_list_regex(software_version=''):
        """Return regular expression for matching all LLDP neighbors in 'display lldp neighbor' output
        
        Arguments:
            software_version {string} -- Software version informatio in format
        
        Returns:
            [string] -- Regular expression for searching information
        """        
        """ 'display lldp neighbor' output example:
            100GE1/0/1 has 1 neighbor(s):

            Neighbor index                     :1
            Chassis type                       :MAC Address
            Chassis ID                         :7c1c-f152-5001
            Port ID subtype                    :Interface Name
            Port ID                            :100GE1/0/0
            Port description                   :-D- AC-R4-CE6860-01 [100GE1/0/1] ---
            System name                        :AG-R4-CE12804-01              
            System description                 :Huawei Versatile Routing Platform Software
            VRP (R) software, Version 8.180 (CE12800 V200R005C10SPC800)
            Copyright (C) 2012-2018 Huawei Technologies Co., Ltd.
            HUAWEI CE12804

            System capabilities supported      :bridge router
            System capabilities enabled        :bridge router
            Management address type            :IPv4
            Management address                 :10.198.177.7
            Expired time                       :98s

            Port VLAN ID(PVID)                 :0
            Port and Protocol VLAN ID(PPVID)   :unsupported         
            VLAN name of VLAN                  :--
            Protocol identity                  :--
            Auto-negotiation supported         :No
            Auto-negotiation enabled           :No
            OperMau                            :speed (100000) /duplex (Full)
            Link aggregation supported         :Yes
            Link aggregation enabled           :No
            Aggregation port ID                :0
            Maximum frame Size                 :9216
            Port Identity                      :--
            Discovered time                    :2020-03-18 15:27:28+03:00

            EEE support                        :No
            Transmit Tw                        :65535
            Receive Tw                         :65535
            Fallback Receive Tw                :0
            Echo Transmit Tw                   :0
            Echo Receive Tw                    :0

            Network Card ID                    :--
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
        return 'display device elabel', '', ''

    @staticmethod
    def get_regex_request_boards_list(flag_all_boards, version=''):
        '''
        CE12808's Device status:
        -------------------------------------------------------------------------------------------
        Slot  Card   Type                     Online   Power Register     Alarm     Primary        
        -------------------------------------------------------------------------------------------
        1     -      CE-L12CQ-FD              Present  On    Registered   Normal    NA             
        9     -      CE-MPUA                  Present  On    Registered   Normal    Master         
        10    -      CE-MPUA                  Present  On    Registered   Normal    Slave          
        11    -      CE-CMUA                  Present  On    Registered   Normal    Master         
        12    -      CE-CMUA                  Present  On    Registered   Normal    Slave          
        13    -      CE-SFU08F                Present  On    Registered   Normal    NA             
        14    -      CE-SFU08F                Present  On    Registered   Normal    NA             
        15    -      CE-SFU08F                Present  On    Registered   Normal    NA             
        16    -      CE-SFU08F                Present  On    Registered   Normal    NA             
        17    -      CE-SFU08F                Present  On    Registered   Normal    NA             
        PWR1  -      PHD-3000WA               Present  Off   Registered   Abnormal  NA             
        PWR2  -      PHD-3000WA               Present  Off   Registered   Abnormal  NA             
        PWR3  -      PHD-3000WA               Present  On    Registered   Normal    NA             
        PWR4  -      PHD-3000WA               Present  On    Registered   Normal    NA             
        FAN1  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN2  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN3  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN4  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN5  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN6  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN7  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN8  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN9  -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN10 -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN11 -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN12 -      FAN-12C                  Present  On    Registered   Normal    NA             
        FAN13 -      FAN-12C                  Present  On    Registered   Normal    NA             
        -------------------------------------------------------------------------------------------
        '''
        if flag_all_boards:
            return r'\s+(?P<index>\S*\d+)\s+' + \
                r'(?P<sub>\S+)\s+' + \
                r'(?P<type>\S+)\s+' + \
                r'(?P<online>\S+)\s+' + \
                r'(?P<power>\S+)\s+' + \
                r'(?P<register>\S+)\s+' + \
                r'(?P<status>\S+)\s+' + \
                r'(?P<role>\S+)'
        else: 
            return r'\s+(?P<index>\d+)\s+' + \
                r'(?P<sub>\S+)\s+' + \
                r'(?P<type>\S+)\s+' + \
                r'(?P<online>\S+)\s+' + \
                r'(?P<power>\S+)\s+' + \
                r'(?P<register>\S+)\s+' + \
                r'(?P<status>\S+)\s+' + \
                r'(?P<role>\S+)'

    @staticmethod
    def get_command_and_regex_boards_esn(flag_all_boards, hardware='', version=''):
        '''
        <HUAWEI> display device manufacture-info
        ----------------------------------------------------------------------------
        Slot       Card   Type               Serial-number            Manu-date
        ----------------------------------------------------------------------------
        1          --     CE5850-48T4S2Q-EI  210235527210D4000028     2013-04-24
                FAN2   FAN-40SA-B         210235542310CC000023     2013-01-27
                PWR2   PAC-150WA          21021309698ND1000010     2013-01-11
        ----------------------------------------------------------------------------
        '''
        if flag_all_boards:
            return 'display device manufacture-info', r'\n(?P<index>\d+)\s+(?P<card>\S+)\s+(?P<type>\S+)\s+(?P<sn>\S+)'
        else:
            return 'display device manufacture-info', r'\n(?P<index>\d+)\s+(?P<card>\S+)\s+(?P<type>\S+)\s+(?P<sn>\S+)'



    @staticmethod
    def get_regex_request_mac_summary(version=''):
        '''
        Summary information of slot 1:
        Capacity of this slot : 139264     
        -----------------------------------
        Static     :               0       
        Blackhole  :               0       
        Dyn-Local  :               1       
        Dyn-Remote :               0       
        Dyn-Trunk  :               0       
        OAM        :               0       
        Sticky     :               0       
        Security   :               0       
        Authen     :               0       
        Guest      :               0       
        Mux        :               0       
        Tunnel     :               0       
        Snooping   :               0       
        Evn        :               4       
        In-used    :               5       
        -----------------------------------
        '''
        return r'Capacity of this slot\s*:\s*(?P<capacity>\d+)(.*\n)*?' + \
            r'In-used\s*:\s*(?P<in_used>\d+)'

    @staticmethod
    def get_command_and_regex_memory(version=''):
        '''display memory 
        Memory utilization statistics at 2020-04-15 13:30:54 763 ms
        System Total Memory: 1976072 Kbytes    
        Total Memory Used: 1157068 Kbytes    
        Memory Using Percentage: 58%               
        State: Non-overload      
        Overload threshold:  95%, Overload clear threshold:  75%, Duration:    2s
        ----------------------------
        ServiceName   MemUsage(KB)   
        ----------------------------
        FEA                 198343
        CMF                 148358
        ....
        '''
        return 'display memory', r'\nMemory Using Percentage\s*:\s*(?P<usage_percent>\d+)%'