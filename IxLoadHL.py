'''
    IxLoad Library is High level support for Ixload automation.
'''
#version 1.0
from IxUtils import IxUtils as IxLoadUtils
import re
import time
IX_UTIL = IxLoadUtils()


def load_config(rt_handle, rxf_file_path, supported_file):
    '''
        load_config Call will load the saved cofiguration into Ixload.
        Args:
        Example:
        - load_config("C:/Users/Administrator/Documents/Ixia/IxLoad/Repository/waseem_testing.rxf")
        Return:
        - Success: {"status": 1}
        - Failure: {'status': 0, 'log': Exception("unable to load sample.rxf as file doesnt exist")}
    '''
    try:
        
        if ("\\" in rxf_file_path) :
            filename = rxf_file_path.split("\\")[-1]
            if supported_file:
                supported_file_name = supported_file.split("\\")[-1]
        else:
            filename = rxf_file_path.split("/")[-1]
            if supported_file:
                supported_file_name = supported_file.split("/")[-1]
        if ("\\" in rt_handle.file_path):
            uploadPath = rt_handle.file_path + '\\' + filename
            if supported_file:
                filePath = rt_handle.file_path + '\\' + supported_file_name
        else:
            uploadPath = rt_handle.file_path + '/' + filename
            if supported_file:
                filePath = rt_handle.file_path + '/' + supported_file_name
        IX_UTIL.uploadFile(rt_handle, rt_handle.session_url, rxf_file_path, uploadPath)
        if supported_file:
            IX_UTIL.uploadFile(rt_handle, rt_handle.session_url, supported_file, filePath)
        IX_UTIL.load_repository(rt_handle, rt_handle.session_url, uploadPath)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def start_test(rt_handle):
    '''
        start_test Call to start the configured test.
        Args:
        Example:
        - start_test()
        Return:
        - Success: {"status": 1, "state":running}
        - Failure: {'status': 0, 'log': Exception("No ports have been assigned to \
                                                   'Traffic2@Network2'. Please assign one \
                                                    or more ports and retry")
    '''
    # try:
    #     IX_UTIL.run_test(rt_handle, rt_handle.session_url)
    #     test_state = True
    #     while test_state:
    #         state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
    #         if state.lower() == "configuring":
    #             time.sleep(10)
    #         if state.lower() == "running":
    #             test_state = False
    #             return {"status": 1, "state": state}
    #         else:
    #             test_state = False
    #             return {"status": 0, "state": state}
    # except Exception as err:
    #     return {"status": 0, "log": err}
    try:
        IX_UTIL.run_test(rt_handle, rt_handle.session_url)
        state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        if state.lower() == "configuring":
            time.sleep(120)
            state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url) 
        if state.lower() == "running":
            return {"status": 1, "state": state}
        else:
            return {"status": 0, "state": state} 
    except Exception as err: 
        return {"status": 0, "log": err}

def stop_test(rt_handle):
    '''
        stop_test Call to stop the configured test.
        Args:
        Example:
        - stop_test()
        Return:
        - Success: {"status": 1, "state":unconfigured}
        - Failure: {'status': 0, 'log': Exception("No ports have been assigned to \
                                                'Traffic2@Network2'. Please assign one \
                                                    or more ports and retry")
    '''
    try:
        IX_UTIL.stop_traffic(rt_handle, rt_handle.session_url)
        state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        if state.lower() == "unconfigured":
            return {"status": 1}
        else:
            return {"status": 0, "state": state}
    except Exception as err:
        return {"status": 0, "log": err}

def get_stats(rt_handle, stats_to_display, polling_interval, duration):
    '''
    get stats Call to poll the selected stats.
        Args:
            stats_to_display =   {
                        #format: { stats_source : [stat name list] }
                        "HTTPClient": ["Transaction Rates"],
                        "HTTPServer": ["TCP Failures"]
                    }
        - stats_to_display - stats to pull in the above format.
        Example:
            stats_to_display =   {
                        #format: { stats_source : [stat name list] }
                        "HTTPClient": ["Transaction Rates"],
                        "HTTPServer": ["TCP Failures"]
                    }
        - get_stats(stats_to_display)
        Return:
        -Success : {"status": 1, "stats": {HTTPClient": {"Transaction Rates":30},
                                           "HTTPServer": {"TCP Failures":0} }
        -Failure : {"status": 0, "log": "HTTPClient-Transaction Rates stats are not availble}
    '''
    try:
        state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        if state.lower() == 'running':
            stats = IX_UTIL.poll_stats(rt_handle, rt_handle.session_url, stats_to_display, polling_interval, duration)
        else:
            raise Exception("Cannot Get Stats when ActiveTest State - '%s'"%state)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1, "stats": stats}

def save_config(rt_handle, rxf_file_path, username, password, sftp_enable, server):
    '''
       save_config Call will save the cofiguration in a given path.
       Args:
        -rxf_file_path : path where configuration need to saved, configuration will be saved in .rxf.
       Example:
       - rxf_file_path = "C:/Program Files (x86)/Python36-32/http.rxf"
       -save_config(rxf_file_path)
       Return:
       -Success :
    '''
    try:
        if server:
            if "\\" in rxf_file_path:
                filename = rxf_file_path.split("\\")[-1]
                file_path = rxf_file_path.replace(filename, "")
            else:
                filename = rxf_file_path.split("/")[-1]
                file_path = rxf_file_path.replace(filename, "")
            if "\\" in rt_handle.file_path:
                remote_path = "%s\\%s" % (rt_handle.file_path, filename)
            else:
                remote_path = "%s/%s" % (rt_handle.file_path, filename)
        else:
            remote_path = rxf_file_path
        IX_UTIL.stop_traffic(rt_handle, rt_handle.session_url)
        IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        IX_UTIL.save_rxf(rt_handle, rt_handle.session_url, remote_path)
        if server:
            if sftp_enable:
                IX_UTIL.downloadResource(rt_handle=rt_handle, downloadFolder=file_path, localPath=remote_path, timeout=200)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}


def generate_report(rt_handle, file_path, file_name, username, password, sftp_enable, server):
    '''
       save_config Call will save the cofiguration in a given path.
       Args:
        -rxf_file_path : path where configuration need to saved, configuration will be saved in .rxf.
       Example:
       - rxf_file_path = "C:/Program Files (x86)/Python36-32/http.rxf"
       -save_config(rxf_file_path)
       Return:
       -Success :
    '''
    try:
        if server:
            # filename = rxf_file_path.split("/")[-1]
            ##path = 'C:\\ProgramData\\Ixia\\IxLoadGateway'
            if "\\" in rt_handle.file_path:
                remote_path = "%s\\%s" % (rt_handle.file_path, file_name)
            else:
                remote_path = "%s/%s" % (rt_handle.file_path, file_name)
        else:
            if "\\" in rt_handle.file_path:
                remote_path = file_path + "\\" + file_name
            else:
                remote_path = file_path + "/" + file_name
        IX_UTIL.report_config(rt_handle, rt_handle.session_url, remote_path)
        if server:
            IX_UTIL.downloadResource(rt_handle=rt_handle, downloadFolder=file_path, localPath=remote_path, timeout=200)     
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}


def poll_csv_stats(rt_handle, stats_dict, file_name, file_path, username, password, server=0, parse=0):
    '''
       save_config Call will save the cofiguration in a given path.
       Args:
        -rxf_file_path : path where configuration need to saved, configuration will be saved in .rxf.
       Example:
       - rxf_file_path = "C:/Program Files (x86)/Python36-32/http.rxf"
       -save_config(rxf_file_path)
       Return:
       -Success :
    '''
    try:
        stat_value = []
        stats_return = {}
        test_is_running = True
        for role in stats_dict.keys():
            stat_role = role
            for statname in stats_dict[role]:
                stat_value.append(statname)
        for key in stat_value:
            stats_return[key] = []
        if server:
            # filename = rxf_file_path.split("/")[-1]
            #path = 'C:\\inetpub\\ftproot'
            ##path = 'C:\\ProgramData\\Ixia\\IxLoadGateway'
            #path = 'C:\\Users\\Anush\\Documents\\Ixia\\IxLoad\\9.10.115.162'
            if "\\" in rt_handle.file_path:
                remote_path = "%s\\%s.csv" % (rt_handle.file_path, stat_role)
            else:
                remote_path = "%s/%s.csv" % (rt_handle.file_path, stat_role)
        #path = re.match(r'(.*)\/.*[a-z|A-Z|0-9]+\.csv$', file_name)
        #path = path.group(1)
        #local_path = "%s/%s.csv" % (path, stat_role)
        local_path = file_path
        while test_is_running:
            state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
            if state.lower() == "unconfigured":
                if server:
                    test_is_running = False
                    IX_UTIL.downloadResource(rt_handle=rt_handle, downloadFolder=local_path, localPath=remote_path, timeout=200)
                    #IX_UTIL.sftp_save_config(rt_handle.appserver, username, password, remote_path, local_path)
                    #IX_UTIL.ftp_save_config(rt_handle.appserver, username, password, remote_path)
                else:
                    test_is_running = False
        local_path = "%s\\%s.csv" % (file_path, stat_role)
        file_name = "%s\\%s.csv" % (file_path, file_name)
        stats = IX_UTIL.csv_stats(rt_handle, stats_return, local_path, file_name, parse = parse)
        
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1, "stats": stats}

def disconnect(rt_handle):
    '''
    Donnect Call to disconnect to the IxLoadLoad API server.
    Example:
    -disconnect()
    Return:
    -Success: {'status': 1}
    -Failure: {'status': 0, 'log': Exception(Failed to close to the session "sessions/2")}
    '''
    try:
        IX_UTIL.delete_session(rt_handle, rt_handle.session_url)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def get_test_status(rt_handle):
    '''
        get_test_status will return the current test status.
    '''
    try:
        state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        return {"status": 1, "state": state}
    except Exception as err:
        return {"status": 0, "log": err}

def add_chassis(rt_handle, chassis_list, portlist_per_community=None):
    '''
        add_chassis Call to connect to the chassis.
        Args:
        - chassis_list - List of Chassis that are needed for the test.
        - portlist_per_community - List of Ports per Community that are needed for the test.
        Example:
        - add_chassis([10.221.113.254,10.221.113.251])
          kportlist_per_community =    {
                                    "Traffic1@Network1" : [(1,5,1)]
                                }
            #"Traffic2@Network2" : [(1,5,2)]
        - add_chassis([10.221.113.254,10.221.113.251], kportlist_per_community)

        Return:
        - Success: {'status': 1}
        - Failure: {'status': 0, 'log': Exception("Error while executing action \
                                                   'sessions/2/ixload/chassisChain/chassis_list'.Error \
                                                    Port Assignment	Error adding chassis 10.221.113.251: Invalid \
                                                     chassis name or IP provided. Please check if sspt-ixia is \
                                                    correct.",)}
    '''
    try:
        portlist_per_community = {} if portlist_per_community is None else portlist_per_community
        IX_UTIL.clear_chassis_list(rt_handle, rt_handle.session_url)
        if not isinstance(chassis_list, list):
            chassis_list = [chassis_list]
        IX_UTIL.add_chassis_list(rt_handle, rt_handle.session_url, chassis_list)
        if len(portlist_per_community) > 0:
            #rt_handle.log(level="INFO", message="Assigning the ports: %s \n" % portlist_per_community)
            IX_UTIL.assign_ports(rt_handle, rt_handle.session_url, portlist_per_community)
            return {"status": 1}
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def stats_config(rt_handle, interval, file_path): 
    '''
    '''
    try:
        IX_UTIL.polling_interval_test(rt_handle, rt_handle.session_url, interval, rt_handle.file_path)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def get_port_no(rt_handle, kwargs): 
    '''
    '''
    try:
        ip = IX_UTIL.get_port_details(rt_handle, rt_handle.session_url, kwargs)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1, "ip": ip }

def add_ports(rt_handle, portlist_per_community):
    '''
    add_ports Call to assign the ports to networks.
        Args:
        portlist_per_community =    {
                                    "Traffic1@Network1" : [(1,5,1)],
                                    "Traffic2@Network2" : [(1,5,2)]
                               }
        - portlist_per_community - ports per network in the above format.
        Example:
        portlist_per_community =    {
                                    "Traffic1@Network1" : [(1,5,1)],
                                    "Traffic2@Network2" : [(1,5,2)]
                               }
        - add_ports(portlist_per_community)
    '''
    try:
        IX_UTIL.assign_ports(rt_handle, rt_handle.session_url, portlist_per_community)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def reboot_port(rt_handle, port):
    '''
        Reboot ports
    '''
    try:
        IX_UTIL.reboot_ports(rt_handle, rt_handle.session_url, port)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def release_config(rt_handle):
    '''
        Reboot ports
    '''
    try:
        IX_UTIL.release_configs(rt_handle, rt_handle.session_url)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def timeline_http_config(rt_handle, config_dict):
    '''
    Configure the timeline of HTTP based on objective type.
    '''
    try:
        IX_UTIL.configure_time_line(rt_handle, rt_handle.session_url, config_dict)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def timeline_ftp_config(rt_handle, config_dict):
    '''
     Configure the timeline of FTP based on objective type.
    '''
    try:
        IX_UTIL.configure_time_line(rt_handle, rt_handle.session_url, config_dict)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def timeline_dns_config(rt_handle, config_dict):
    '''
     Configure the timeline of FTP based on objective type.
    '''
    try:
        IX_UTIL.configure_time_line(rt_handle, rt_handle.session_url, config_dict)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def emulation_dut(rt_handle, kwargs):
    '''
        Create or modify the Http Protocol Emulation.
    '''
    try:
        IX_UTIL.configure_dut(rt_handle, rt_handle.session_url, kwargs)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def emulation_http(rt_handle, network_name, kwargs):
    '''
        Create or modify the Http Protocol Emulation.
    '''
    try:
        if "mode" not in kwargs.keys():
            raise Exception('Argument mode not found, mode is a mandatory argument')
        IX_UTIL.emulation_protocol(rt_handle, rt_handle.session_url, network_name, "HTTP", "type1", kwargs)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def get_config(rt_handle, network_name, args):
    '''
        Create or modify the Http Protocol Emulation.
    '''
    try:
        if len(args) == 0:
            raise Exception('Please provide argument to get the details')
        args_list = args.copy()
        ethernet_args, args = IX_UTIL.get_list_args("eth_", args)
        ip_args, args = IX_UTIL.get_list_args("ip_", args)
        port_args, args = IX_UTIL.get_list_args("port_", args)
        # if len(ethernet_args) > 0:
            # ret_dict = IX_UTIL.get_ethernet(rt_handle, rt_handle.session_url, network_name, ethernet_args)
        if len(ip_args) > 0:
            ip = IX_UTIL.get_ip(rt_handle, rt_handle.session_url, network_name, ip_args)
            return (IX_UTIL.remove_items(ip, "ip", args_list))
        if len(port_args) > 0:
            port = IX_UTIL.get_port(rt_handle, rt_handle.session_url, network_name, port_args)
            return (IX_UTIL.remove_items(port, "port", args_list))
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}
 
def network_config(rt_handle, **kwargs):
    '''
    network config will allow users to configure Netwrok configuration on IxLoad
    configuration on ethernet, mac, vlan, IP, Emulated roauter etc.
    '''
    try:
        if "network_name" not in kwargs.keys():
            raise Exception('mode is Argum.ent network_name not found, a mandatory argument')
        network_name = kwargs['network_name']
        kwargs.pop('network_name')
        network_name = IX_UTIL.get_community_name(rt_handle, network_name)
        if len(kwargs) > 0:
            ethernet_args, kwargs = IX_UTIL.get_args("eth_", kwargs)
            ip_args, kwargs = IX_UTIL.get_args("ip_", kwargs)
            mac_args, kwargs = IX_UTIL.get_args("mac_", kwargs)
            vlan_args, kwargs = IX_UTIL.get_args("vlan_", kwargs)
            comp_lst = ['disable_min_max_buffer_size', 'adjust_tcp_buffers' ,'udp_port_randomization','inter_packet_delay',
                        'bestPerfSettings','delayed_acks_segments','accept_ra_all','accept_ra_default','llm_hdr_gap',
                        'name','inter_packet_granular_delay','llm_hdr_gap_ns','delayed_acks_timeout','delayed_acks','rps_needed','ip_no_pmtu_disc']
            tcp_args, kwargs = IX_UTIL.get_args("tcp_", kwargs, comp_lst)
            emulated_router_args, kwargs = IX_UTIL.get_args("er_", kwargs)
            if len(ethernet_args) > 0:
                IX_UTIL.configure_ethernet(rt_handle, rt_handle.session_url, network_name, ethernet_args)
            if len(ip_args) > 0:
                IX_UTIL.configure_ip(rt_handle, rt_handle.session_url, network_name, ip_args)
                #import pdb;pdb.set_trace()
            if len(mac_args) > 0:
                IX_UTIL.configure_mac(rt_handle, rt_handle.session_url, network_name, mac_args)
            if len(vlan_args) > 0:
                IX_UTIL.configure_vlan(rt_handle, rt_handle.session_url, network_name, vlan_args)
            if len(emulated_router_args) > 0:
                if "mode" not in emulated_router_args.keys():
                    raise Exception('Argument er_mode not found, er_mode is a mandatory argument for Emulated Router config')
                IX_UTIL.configure_emulated_router(rt_handle, rt_handle.session_url, network_name, emulated_router_args)
            if len(tcp_args) > 0:
                IX_UTIL.configure_tcp(rt_handle, rt_handle.session_url, network_name, tcp_args)
        #IX_UTIL.apply_config(rt_handle, rt_handle.session_url)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def set_config(rt_handle, force=0):
    try:
        #import pdb;pdb.set_trace()
        res = IX_UTIL.apply_config(rt_handle, rt_handle.session_url, force)
        time.sleep(30)
        state = IX_UTIL.get_test_current_state(rt_handle, rt_handle.session_url)
        if state.lower() == "configured" or "configuring":
            return {"status": 1, "state": state}
        else:
            return {"status": 0, "state": state}
    except Exception as err:
        return {"status": 0, "log": err}

def delete_chassis(rt_handle, chassis_list):
    '''
    This method will delete chassis from configured test.
    '''
    try:
        IX_UTIL.remove_chassis_list(rt_handle, rt_handle.session_url, chassis_list)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def delete_port(rt_handle, port_list_per_community):
    '''
    This method will delete ports from configured test.
    '''
    try:
        IX_UTIL.remove_port(rt_handle, rt_handle.session_url, port_list_per_community)
    except Exception as err:
        return {"status": 0, "log": err}
    return {"status": 1}

def emulation_ftp(rt_handle, network_name, kwargs):
    '''
        Create or modify the Ftp Protocol Emulation.
    '''
    try:
        if "mode" not in kwargs.keys():
            raise Exception('Argument mode not found, mode is a mandatory argument')
        IX_UTIL.emulation_protocol(rt_handle, rt_handle.session_url, network_name, "FTP", "type1", kwargs)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def emulation_dns(rt_handle, network_name, **kwargs):
    '''
        Create or modify the DNS Protocol Emulation.
    '''
    try:
        if "mode" not in kwargs.keys():
            raise Exception('Argument mode not found, mode is a mandatory argument')
        IX_UTIL.emulation_protocol(rt_handle, rt_handle.session_url, network_name, "DNS", "type2", kwargs)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1}

def get_session(rt_handle):
    '''
        get_session will return the session id
    '''
    try:
        session_id = IX_UTIL.get_session_status(rt_handle, rt_handle.session_url)
    except Exception as err:
        return {"status":0, "log": err}
    return {"status": 1, "session":session_id}
