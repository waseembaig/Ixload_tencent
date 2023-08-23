"""
IxLoad module providing abstraction of IxLoad Robot keywords.
"""
import os
import re
import sys
import time
import atexit
import telnetlib
import yaml
import json
import inspect
#import pexpect
import IxRestApi as IxRestUtils
from IxLoadHL import *


class IxLoad():
    """
    IxLoad emulation class
    """
    def __init__(self, system_data=None, chassis=None, appserver=None):
        """
        IxLoad abstraction layer for HLTAPI

        -- Workflow 1 --
        :param  system_data  *MANDATORY* Dictionary of IxLoad information
          Example:
          system_data =
            system:
              primary:
                appserver: wf-appserver2.englab.juniper.net
                controllers:
                  unknown:
                    domain: englab.juniper.net
                    hostname: wf-ixchassis2
                    mgt-intf-name: mgt0
                    mgt-ip: 10.9.1.107
                    osname: IxOS
                make: ixia
                model: xgs12
                name: wf-ixchassis2
                osname: IxOS

        -- Workflow 2 --
        :param  chassis  *MANDATORY* Name of chassis
        :param  appserver  *MANDATORY* Name of tcl server

        :return: ixload object
        """
        self.port_list = None
        self.handle_to_port_map = None
        self.port_to_handle_map = None
        atexit.register(self.cleanup)
        self.intf_to_port_map = None
        self.interfaces = None
        self.session = None
        self.session_url = None
        self.user_functions = dict()
        self.appserver = None
        # IxLoad API handle
        self.ixload = None

        #environment = yaml.load(open(os.path.join(os.path.dirname(credentials.__file__), "environment.yaml")))
        #self.lib_path = environment['ixia-lib-path']
        self.connection = None
    def load_config(self, rxf_file_path, supported_file=None):
        return(load_config(self, rxf_file_path, supported_file))
        
    def disconnect(self):
        return (disconnect(self))

    def add_chassis(self, chassis_list, portlist_per_community=None):
        return (add_chassis(self, chassis_list, portlist_per_community))
    
    def start_test(self):
        return (start_test(self))
    
    def release_config(self):
        return (release_config(self))

    def stop_test(self):
        return(stop_test(self))
    
    def set_config(self, force=0):
        return(set_config(self, force))
    
    def stats_config(self, polling_interval, file_path=None):
        return (stats_config(self, polling_interval, file_path))
    
    def get_port_no(self, **kwargs):
        return (get_port_no(self, kwargs))
        
    def poll_csv_stats(self, stats_to_display, file_name, file_path, username=None, password=None, server=0, parse=0):
        return (poll_csv_stats(self, stats_to_display, file_name, file_path, username, password, server, parse))

    def get_stats(self, stats_to_display, polling_interval=0, duration=0):
        return (get_stats(self, stats_to_display, polling_interval, duration))

    def save_config(self, rxf_file_path, username=None, password=None, sftp_enable=0, server=0):
        return (save_config(self, rxf_file_path, username, password, sftp_enable, server))
    
    def generate_report(self, file_path, file_name, username=None, password=None, sftp_enable=0, server=0):
        return (generate_report(self, file_path, file_name, username, password, sftp_enable, server))

    def get_test_status(self):
        return (get_test_status(self))

    def add_ports(self, portlist_per_community):
        return (add_ports(self, portlist_per_community))
    
    def reboot_port(self, port):
        return (reboot_port(self, port))

    def timeline_http_config(self, config_dict):
        return (timeline_http_config(self, config_dict))

    def timeline_ftp_config(self, config_dict):
        return (timeline_ftp_config(self, config_dict))

    def timeline_dns_config(self, config_dict):
        return (timeline_dns_config(self, config_dict))

    def emulation_http(self, kwargs):
        if "networkName" in kwargs.keys():
            network_name = kwargs['networkName']
            kwargs.pop('networkName')
            return (emulation_http(self, network_name, kwargs))
        else:
            raise Exception("Network name is mandatory argument")
    def emulation_dut(self, kwargs):
        return (emulation_dut(self, kwargs))
    
    def network_config(self, kwargs):
        return (network_config(self, kwargs))
    
    def get_config(self, network_name, args):
        return (get_config(self, network_name, args))

    def emulation_ftp(self, network_name, **kwargs):
        return (emulation_ftp(self, network_name, kwargs))

    def emulation_dns(self, network_name, **kwargs):
        return (emulation_dns(self, network_name, kwargs))

    def cleanup(self):
        """
        Destructor to disconnect from IxLoad server
        """
        try:
            if self.session:
                self.log("Deleting session")
                self.ixload.delete_session(self.session)
            if self.ixload:
                self.log("Disconnecting from IxLoad chassis")
                self.ixload.disconnect()
        except Exception:
            pass

    def _get_version(self):
        """
        Get Chassis OS Version of IxLoad TC
        :
        :return: ixia chassisversion
        """
        version = None
        try:
            pexp = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@%s' % self.chassis)
            pexp.expect('.+password:')
            time.sleep(2)
            out = pexp.after
            self.log(level="INFO", message="{}".format(out))
            if out:
                pexp.sendline('admin')
                pexp.expect('#')
                time.sleep(2)
                banner_out = pexp.before
                if re.search(r'enter chassis', banner_out.decode('utf-8'), re.I|re.M):
                    pexp.sendline('enter chassis')
                pexp.sendline('show ixos active-version')
                pexp.expect('#')
                time.sleep(2)
                version_out = pexp.before
                self.log(level="INFO", message="{}".format(version_out.decode('utf-8')))
                match = re.search(r'IxOS active version:.+IxOS.+(\d+\.\d+)\.\d+\.\d+|Active IxOS Version\s+.+:\s+(\d+\.\d+)\.\d+\.\d+',\
                                    version_out.decode('utf-8'), re.IGNORECASE)
                pexp.sendline('exit')
                if match is not None:
                    version = match.group(1) if match.group(1) is not None else match.group(2)
                    self.log(level="INFO", message="Ixos version: %s \n" % version)
                else:
                    raise TobyException("Could not get the ixia verion using ssh connection to box %s" % self.chassis, host_obj=self)
        except Exception:
            self.telnet_handle = telnetlib.Telnet(self.chassis)
            # self.telnet_handle.set_debuglevel(10)
            self.telnet_handle.read_until(b"Ixia>")
            time.sleep(self.wait)
            cmd = "package require IxTclHal;version cget -ixTclHALVersion\n"
            cmd = cmd.encode('ascii')
            self.telnet_handle.write(cmd)
            match_results = self.telnet_handle.expect([br"\d+\.\d+\.\d+\.\d+"])
            version = match_results[1].group(0).decode('ascii')
            self.telnet_handle.close()

        if not version:
            raise TobyException("Unable to detect Ixia chassis version. Is your Ixia chassis reachable?", host_obj=self)

        self.log(level='info', message='CHASSIS VERSION: ' + version)
        major_minor_version = re.search(r'^\d+\.\d+', version).group(0)

        if not major_minor_version:
            raise TobyException("Unable to derive major and minor version from " + version, host_obj=self)

        if float(major_minor_version) < 8.20:
            raise TobyException("Unsupported version " + major_minor_version + ". Minimum version supported: 8.20", host_obj=self)
        return version

    def _set_envs(self):
        """
        Set PYTHONPATH required for IxLoad
        """

        sys.path.append(self.lib_path)
        # sys.path.append(self.ixload_lib_path + '/RestScripts/Utils')
        self.log(level="info", message="ADDED_TO_PYTHONPATH= " + self.lib_path)
        # self.log(level="info", message="ADDED_TO_PYTHONPATH= " + self.ixload_lib_path + '/RestScripts/Utils')

    def add_interfaces(self, interfaces):
        """
        Get interfaces{} block from yaml to use fv- knobs therein
        """
        self.interfaces = interfaces

    def add_intf_to_port_map(self, intf_to_port_map):
        """
        Add attribute to ixload object which contains
        params intf to port mappings
        """
        self.intf_to_port_map = intf_to_port_map

    def invoke(self, command, **kwargs):
        """
        Pass-through for ixnetwork.py functions
        (ixnetwork.py? or something else?)
        """
        if re.match(r"^http_post", command):
            reply = self.connection.http_post(url=kwargs['url'], data=kwargs['data'])
            return reply
        elif re.match(r"^http_get", command):
            if 'option' in kwargs.keys():
                #import pdb;pdb.set_trace()
                reply = self.connection.http_get(url=kwargs['url'], option=kwargs['option'])
            elif "stream" in kwargs.keys():
                reply = self.connection.http_get(url=kwargs['url'], stream=kwargs['stream'])
            else:
                reply = self.connection.http_get(url=kwargs['url'])
            return reply
        elif re.match(r"^http_request", command):
            reply = self.connection.http_request(method=kwargs['method'], url=kwargs['url'])
            return reply
        elif re.match(r"^httpRequest2", command):
            reply = self.connection.httpRequest2(method=kwargs['method'], url=kwargs['url'], params=kwargs['params'], downloadStream=kwargs['downloadStream'], timeout=kwargs['timeout'])
            return reply
        elif re.match(r"^http_options", command):
            reply = self.connection.http_options(url=kwargs['url'])
            return reply
        elif re.match(r"^http_patch", command):
            reply = self.connection.http_patch(url=kwargs['url'], data=kwargs['data'])
            return reply
        elif re.match(r"^http_delete", command):
            reply = self.connection.http_delete(url=kwargs['url'], data=kwargs['data'])
            return reply
        if command in self.user_functions:
            self.log(level="info", message="Invoking Juniper IXIA Ixload function " + command + " with parameters " + str(kwargs))
            result = self.user_functions[command](self, **kwargs)
            self.log(level="info", message="Invocation of Juniper IXIA Ixload function " + command + " completed with result: " + str(result))
            return result
        if command == 'get_session':
            self.log(level="info", message="Returning IxLoad Session Handle")
            return self.session_url
        self.log(level="info", message="Invoking IxLoad method " + command + " with parameters " + str(kwargs))
        ixload_method = getattr(self.ixload, command)
        result = ixload_method(**kwargs)
        if type(result) is dict and 'status' in result:
            if not result['status']:
                raise TobyException("Invocation of IxLoad method " + command + " failed with result: " + str(result), host_obj=self)
        self.log(level="info", message="Invocation of IxLoad method " + command + " succeeded with result: " + str(result))
        return result

    # def connect(self, port_list, **kwargs):
        # """
        # Connect to IxLoad chassis
        # :return: ixload connection object
        # """
        # if not port_list:
            # raise TobyException("Missing port_list parameter", host_obj=self)

        # self.log(level="info", message="Connecting to Ixia IxLoad service on port 8443...")
        # bad_connect = self.create_session(gateway_server=self.appserver, gateway_port=8443, ixload_version=self.version)

        # # Use bad version to get back error containing proper version and then turn around
        # # and use proper version from error to try and create session again
        # version_appserver = None
        # if not bad_connect['status']:
            # version_appserver = re.search(r'Available\s+versions\s+.+(\d+\.\d+\.\d+\.\d+)', str(bad_connect['log']), re.I).group(1)
            # self.log(level='INFO', message="Available Version {}".format(version_appserver))
        # else:
            # raise TobyException("Unable to detect ixload version", host_obj=self)

        # if version_appserver is None:
            # raise TobyException("Could Not get the Version from Ixload Appserver")
        # major_minor_version = re.search(r'^\d+\.\d+', self.version).group(0)
        # if major_minor_version not in version_appserver:
            # raise TobyException("Version miss match with Chassis {} and Appserver {}".format(self.version, version_appserver))
        # # Trying for right connection
        # result = self.create_session(gateway_server=self.appserver, gateway_port=8443, ixload_version=version_appserver)
        # if not result['status']:
            # raise TobyException("Invocation of IxLoad connect() failed with result: " + str(result), host_obj=self)
        # else:
            # self.log(level="info", message="IxLoad Session Started")
            # return result['session']

    def connect(self, gateway_server, gateway_port, ixload_version):
        '''
            This method is used to create a new session. It will return the url of the newly created session
            Args:
            - ixload_version this is the actual IxLoad Version to start
        '''
        
        try:
            #http_redirect=True
            self.connection = IxRestUtils.get_connection(gateway_server, gateway_port, http_redirect=True)
            session_url = "sessions"
            data = {"ixLoadVersion": ixload_version}
            data = json.dumps(data)
            #import pdb;pdb.set_trace()
            reply = self.connection.http_post(url=session_url, data=data)
            if not reply.ok:
                raise Exception(reply)
            try:
                new_obj_path = reply.headers['location']
            except:
                raise Exception("Location header is not present. Please check if the action was created successfully.")
            session_id = new_obj_path.split('/')[-1]
            self.session_url = "%s/%s" % (session_url, session_id)
            start_session_url = "%s/operations/start" % (self.session_url)
            reply = self.connection.http_post(url=start_session_url, data={})
            if not reply.ok:
                raise Exception(reply.text)
            action_result_url = reply.headers.get('location')
            if action_result_url:
                action_result_url = self.strip_api_and_version_from_url(action_result_url)
                action_finished = False
                while not action_finished:
                    action_status_obj = self.connection.http_get(url=action_result_url)
                   
                    if action_status_obj.state == 'finished':
                        if action_status_obj.status == 'Successful':
                            action_finished = True
                            self.appserver = gateway_server
                        else:
                            error_msg = "Error while executing action '%s'." % start_session_url
                            if action_status_obj.status == 'Error':
                                error_msg += action_status_obj.error
                            #self.log(error_msg)
                            raise Exception(error_msg)
                    else:
                        time.sleep(0.1)
            resource_url = "%s/resources" % (self.connection.url)
            resource_obj = self.connection.http_get(url=resource_url)
            self.file_path = resource_obj.sharedLocation
        except Exception as err:
            return {"status": 0, "log": err}
        return {"status": 1, "session" : self.session_url}
        
    def strip_api_and_version_from_url(self, url):
        '''
        #remove the slash (if any) at the beginning of the url
        '''
        if url[0] == '/':
            url = url[1:]
        url_elements = url.split('/')
        if 'api' in url:
            #strip the api/v0 part of the url
            url_elements = url_elements[2:]
        return '/'.join(url_elements)

    def get_port_handle(self, intf):
        """
        Use IxLoad object information to get port handle keys
        """
        if intf in self.intf_to_port_map.keys():
            port = self.intf_to_port_map[intf]
            if port in self.port_to_handle_map.keys():
                return self.port_to_handle_map[port]
        else:
            raise TobyException("No such params interface " + intf, host_obj=self)

def invoke(device, function, **kwargs):
    """
    Pass-through function for IxLoad method of same name to call sth.py functions
    """
    return device.invoke(function, **kwargs)
