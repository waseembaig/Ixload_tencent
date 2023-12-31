'''
IxUtils is a suppoting module of Ixload HL Library.
'''
import json
from sre_constants import SUCCESS
import time
#import pysftp
import ftplib
import requests
import yaml
import os
import re
import copy
import csv
ACTION_STATE_FINISHED = 'finished'
ACTION_STATUS_SUCCESSFUL = 'Successful'
ACTION_STATUS_ERROR = 'Error'
ACTION_STATUS_UNCONFIGURED = 'Unconfigured'
#version 1.0
class IxUtils(object):
    '''
        IxUtils consist of supporting module for IXload HL library.
    '''
    def __init__(self):
        self.connection = ""
        self.session_url = ""
        self.current_time = time.strftime("%H%M%S")

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

    def wait_for_action_to_finish(self, reply_obj, action_url, rt_handle):
        '''
            This method waits for an action to finish executing. after a POST request is sent in order to start an action,
            The HTTP reply will contain, in the header, a 'location' field, that contains an URL.
            The action URL contains the status of the action. we perform a GET on that URL every 0.5 seconds until the action finishes with a success.
            If the action fails, we will throw an error and print the action's error message.
            Args:
            - reply_obj the reply object holding the location
            - rt_handle - the url pointing to the operation
        '''
        action_result_url = reply_obj.headers.get('location')
        if action_result_url:
            action_result_url = self.strip_api_and_version_from_url(action_result_url)
            action_finished = False
            while not action_finished:
                action_status_obj = rt_handle.invoke('http_get', url=action_result_url)
                if action_status_obj.state == ACTION_STATE_FINISHED:
                    if action_status_obj.status == ACTION_STATUS_SUCCESSFUL:
                        action_finished = True
                    else:
                        error_msg = "Error while executing action '%s'." % action_url
                        if action_status_obj.status == ACTION_STATUS_ERROR:
                            error_msg += action_status_obj.error
                        raise Exception(error_msg)
                else:
                    time.sleep(0.1)

    def perform_generic_operation(self, rt_handle, url, payload_dict):
        '''
            This will perform a generic operation on the given url, it will wait for it to finish.
            Args:
            - url is the address of where the operation will be performed
            - payload_dict is the python dict with the parameters for the operation
        '''
        data = json.dumps(payload_dict)
        reply = rt_handle.invoke('http_post', url=url, data=data)
        if not reply.ok:
            raise Exception(reply.text)
        self.wait_for_action_to_finish(reply, url, rt_handle)
        return reply

    def perform_generic_patch_operation(self, rt_handle, url, payload_dict):
        '''
            This will perform a generic operation on the given url, it will wait for it to finish.
            Args:
            - url is the address of where the operation will be performed
            - payload_dict is the python dict with the parameters for the operation
        '''
        data = json.dumps(payload_dict)
        reply = rt_handle.invoke('http_patch', url=url, data=data)
        if not reply.ok:
            raise Exception(reply.text)
        responce = rt_handle.invoke('http_get', url=url, data=data)
        key = list(payload_dict.keys())[0]
        iteration = 1
        while(iteration <= 3):
            if str(responce[0][key]).lower() == str(payload_dict[key]).lower():
                return reply
            else:
                time.sleep(5)
                iteration = iteration + 1
        raise Exception("Update on the url %s is failed" %url)

    def perform_generic_patch(self, rt_handle, url, payload_dict):
        '''
            This will perform a generic PATCH method on a given url
            Args:
            - url is the address of where the operation will be performed
            - payload_dict is the python dict with the parameters for the operation
        '''
        data = json.dumps(payload_dict)
        reply = rt_handle.invoke('http_patch', url=url, data=data)
        if not reply.ok:
            raise Exception(reply.text)
        return reply

    def perform_generic_post(self, rt_handle, list_url, payload_dict):
        '''
            This will perform a generic POST method on a given url
            Args:
            - url is the address of where the operation will be performed
            - payload_dict is the python dict with the parameters for the operation
        '''
        data = json.dumps(payload_dict)
        reply = rt_handle.invoke('http_post', url=list_url, data=data)
        if not reply.ok:
            raise Exception(reply.text)
        try:
            new_obj_path = reply.headers['location']
        except:
            raise Exception("Location header is not present. Please check if the action was created successfully.")
        new_obj_id = new_obj_path.split('/')[-1]
        return new_obj_id

    def perform_generic_delete(self, rt_handle, list_url, payload_dict):
        '''
            This will perform a generic DELETE method on a given url
            Args:
            - url is the address of where the operation will be performed
            - payload_dict is the python dict with the parameters for the operation
        '''
        data = json.dumps(payload_dict)
        reply = rt_handle.invoke('http_delete', url=list_url, data=data)
        if not reply.ok:
            raise Exception(reply.text)
        return reply
    
    def downloadResource(self, rt_handle, downloadFolder, localPath, zipName=None, timeout=80):
        '''
            This method is used to download an entire folder as an archive or any type of file without changing it's format.

            Args:
            - connection is the connection object that manages the HTTP data transfers between the client and the REST API
            - downloadFolder is the folder were the archive/file will be saved
            - localPath is the local path on the machine that holds the IxLoad instance
            - zipName is the name that archive will take, this parameter is mandatory only for folders, if you want to download a file this parameter is not used.
        '''
        downloadResourceUrl = rt_handle.connection.url + "/downloadResource"
        downloadFolder = downloadFolder.replace("\\\\", "\\")
        localPath = localPath.replace("\\", "/")
        parameters = { "localPath": localPath, "zipName": zipName }
        
        downloadResourceReply = rt_handle.invoke('httpRequest2', method="GET", url=downloadResourceUrl, params= parameters, downloadStream=True, timeout =timeout)
        if not downloadResourceReply.ok:
            raise Exception("Error on executing GET request on url %s: %s" % (downloadResourceUrl, downloadResourceReply.text))

        if not zipName:
            zipName = localPath.split("/")[-1]
        elif zipName.split(".")[-1] != "zip":
            zipName  = zipName + ".zip"
        downloadFile = '/'.join([downloadFolder, zipName])
        #rt_handle.log("Downloading resource to %s..." % (downloadFile))
        try:
            with open(downloadFile, 'wb') as fileHandle:
                for chunk in downloadResourceReply.iter_content(chunk_size=1024):
                    fileHandle.write(chunk)
        except IOError as e:
            raise Exception("Download resource failed. Could not open or create file, please check path and/or permissions. Received IO error: %s" % str(e))
        except Exception as e:
            raise Exception('Download resource failed. Received the following error:\n %s' % str(e))
        else:
            return ("Download resource finished.")

    def release_configs(self, rt_handle, session_url):
        start_run_url = "%s/ixload/test/operations/abortAndReleaseConfigWaitFinish" % (session_url)
        data = {}
        self.perform_generic_operation(rt_handle, start_run_url, data)
        
    def uploadFile(self, rt_handle, session_url, fileName, uploadPath, overwrite=True):
        headers = {'Content-Type': 'multipart/form-data'}
        params = {"overwrite": overwrite, "uploadPath": uploadPath}
        url = "%s/resources" % (rt_handle.connection.url)
        result = {}
        try:
            start_run_url = "%s/ixload/test/operations/abortAndReleaseConfigWaitFinish" % (session_url)
            data = {}
            self.perform_generic_operation(rt_handle, start_run_url, data)
            with open(fileName, 'rb') as f:
                response = requests.post(url, data=f, params=params, headers=headers, verify=False)
                result["status"] = int(response.ok)
                if response.ok is not True:
                    result["error"] = response.text
                    raise Exception('POST operation failed with %s' % response.text)
        except requests.exceptions.ConnectionError as e:
            result["error"] = str(e)
            raise Exception(
                'Upload file failed. Received connection error. One common cause for this error is the size of the file to be uploaded.'
                ' The web server sets a limit of 1GB for the uploaded file size. Received the following error: %s' % str(e)
            )
        except IOError as e:
            result["error"] = str(e)
            raise Exception('Upload file failed. Received IO error: %s' % str(e))
        except Exception as e:
            result["error"] = str(e)
            raise Exception('Upload file failed. Received the following error:\n   %s' % str(e))
        else:
            result["error"] = ""
        return result
    
    def load_repository(self, rt_handle, session_url, rxf_file_path):
        '''
            This method will perform a POST request to load a repository.
            Args.
            - rt_handle is the address of the session to load the rxf for
            - rxf_file_path is the local rxf path on the machine that holds the IxLoad instance
        '''
        load_test_url = "%s/ixload/test/operations/loadTest" % (session_url)
        data = {"fullPath": rxf_file_path}
        self.perform_generic_operation(rt_handle, load_test_url, data)

    def sftp_load_config(self, server, username, password, localpath, remote_path):
        '''
            sftp_load_config will save the config from one machine to another using sftp protocol.
        '''
        try:
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            with pysftp.Connection(host=server, username=username, password=password, cnopts=cnopts) as sftp:
                sftp.put(localpath, remote_path)
            return 1
        except Exception as err:
            raise Exception('FTP transfer failed \n {}'.format(err))

    def apply_config(self, rt_handle, session_url, force=0):
        '''
            This method is used to start the currently loaded test. After starting the 'Start Test' action, wait for the action to complete.
            Args:
            - session_url is the address of the session that should run the test.
        '''
        if force:
            apply_config_url = "%s/ixload/test/operations/applyConfiguration" % (session_url)
            data = {}
            #self.perform_generic_post(rt_handle, apply_config_url, data)
            self.perform_generic_operation(rt_handle, apply_config_url, data)
        apply_config_url = "%s/ixload/test/operations/applyConfiguration" % (session_url)
        data = {}
        self.perform_generic_post(rt_handle, apply_config_url, data)
        #self.perform_generic_operation(rt_handle, apply_config_url, data)

    def run_test(self, rt_handle, session_url):
        '''
            This method is used to start the currently loaded test. After starting the 'Start Test' action, wait for the action to complete.
            Args:
            - session_url is the address of the session that should run the test.
        '''
        apply_config_url = "%s/ixload/test/operations/applyConfiguration" % (session_url)
        data = {}
        self.perform_generic_operation(rt_handle, apply_config_url, data)
        start_run_url = "%s/ixload/test/operations/runTest" % (session_url)
        data = {}
        run_stats = self.perform_generic_operation(rt_handle, start_run_url, data)
        return run_stats

    def stop_traffic(self, rt_handle, session_url):
        '''
            This method is used to start the currently loaded test. After starting the 'Start Test' action, wait for the action to complete.
            Args:
            - session_url is the address of the session that should run the test.
        '''
        apply_config_url = "%s/ixload/test/operations/gracefulStopRun" % (session_url)
        data = {}
        self.perform_generic_operation(rt_handle, apply_config_url, data)
        start_run_url = "%s/ixload/test/operations/abortAndReleaseConfigWaitFinish" % (session_url)
        data = {}
        run_stats = self.perform_generic_operation(rt_handle, start_run_url, data)
        return run_stats

    def delete_session(self, rt_handle, session_url):
        '''
            This method is used to delete an existing session.
            Args:
            - session_url is the address of the seession to delete
        '''
        delete_params = {}
        self.perform_generic_delete(rt_handle, session_url, delete_params)

    def get_test_current_state(self, rt_handle, session_url):
        '''
        This method gets the test current state. (for example - running, unconfigured, ..)
        Args:
            - session_url is the address of the session that should run the test.
        '''
        active_test_url = "%s/ixload/test/activeTest" % (session_url)
        test_obj = rt_handle.invoke('http_get', url=active_test_url)
        return test_obj.currentState

    def poll_stats(self, rt_handle, session_url, watched_stats_dict, polling_interval, duration):
        '''
            This method is used to poll the stats. Polling stats is per request but this method does a continuous poll.
            Args:
            - session_url is the address of the session that should run the test
            - watched_stats_dict these are the stats that are being monitored
            - polling_interval the polling interval is 4 by default but can be overridden.
        '''
        stats_source_list = list(watched_stats_dict.keys())
        stats_dict = {}
        collected_timestamps = {}  # format { stats_source : [2000, 4000, ...] }
        test_is_running = True
        for stats_source in stats_source_list[:]:
            stats_source_url = "%s/ixload/stats/%s/values" % (session_url, stats_source)
            stats_source_reply = rt_handle.invoke('http_request', method="GET", url=stats_source_url)
            if stats_source_reply.status_code != 200:
                stats_source_list.remove(stats_source)
        stats_value = []
        stats_dict = {}
        if polling_interval == 0 and duration == 0:
            for stats_source in stats_source_list:
                values_url = "%s/ixload/stats/%s/values" % (session_url, stats_source)
                values_obj = rt_handle.invoke('http_get', url=values_url)
                values_dict = values_obj.get_options()
                new_time_stamps = [int(timestamp) for timestamp in values_dict.keys() if timestamp not in collected_timestamps.get(stats_source, [])]
                new_time_stamps.sort(reverse=True)
                for timestamp in new_time_stamps:
                    time_stamp_str = str(timestamp)
                    collected_timestamps.setdefault(stats_source, []).append(time_stamp_str)
                    time_stamp_dict = stats_dict.setdefault(stats_source, {}).setdefault(timestamp, {})
                    for caption, value in values_dict[time_stamp_str].get_options().items():
                        if caption in watched_stats_dict[stats_source]:
                            stats_value.append(value)
                            time_stamp_dict[caption] = value
                            test_is_running = False
                            return time_stamp_dict
        elif polling_interval != 0 and duration == 0:
            
            retrieving_stats = watched_stats_dict[stats_source]
            time_stamp_dict = {}
            for stats in retrieving_stats:
                time_stamp_dict[stats] = []
            while test_is_running:
                #self.set_polling_interval(rt_handle, session_url, polling_interval)
                for stats_source in stats_source_list:
                    values_url = "%s/ixload/stats/%s/values" % (session_url, stats_source)
                    values_obj = rt_handle.invoke('http_get', url=values_url)
                    
                    values_dict = values_obj.get_options()
                    new_time_stamps = [int(timestamp) for timestamp in values_dict.keys() if timestamp not in collected_timestamps.get(stats_source, [])]
                    new_time_stamps.sort()
                    
                    # return new_time_stamps
                    stats_dict1 = watched_stats_dict[stats_source]
                    for stats in stats_dict1:
                        for timestamp in new_time_stamps:
                            time_stamp_str = str(timestamp)
                            collected_timestamps.setdefault(stats_source, []).append(time_stamp_str)
                            for caption, value in values_dict[time_stamp_str].get_options().items():
                                if caption == stats:
                                    time_stamp_dict[stats].append(value)
                test_is_running = self.get_test_current_state(rt_handle, session_url) == "Running"
            return time_stamp_dict
        elif duration != 0:
            retrieving_stats = watched_stats_dict[stats_source]
            time_stamp_dict = {}
            for stats in retrieving_stats:
                time_stamp_dict[stats] = []
            dur = duration/60
            t_end = time.time() + 60 * dur
            while time.time() < t_end:
                
                for stats_source in stats_source_list:
                    values_url = "%s/ixload/stats/%s/values" % (session_url, stats_source)
                    values_obj = rt_handle.invoke('http_get', url=values_url)
                    values_dict = values_obj.get_options()
                    new_time_stamps = [int(timestamp) for timestamp in values_dict.keys() if timestamp not in collected_timestamps.get(stats_source, [])]
                    new_time_stamps.sort(reverse=True)
                    time_stamp_str = str(new_time_stamps[0])
                    stats_dict1 = watched_stats_dict[stats_source]
                    for stats in stats_dict1:
                        for timestamp in new_time_stamps:
                            time_stamp_str = str(timestamp)
                            collected_timestamps.setdefault(stats_source, []).append(time_stamp_str)
                            for caption, value in values_dict[time_stamp_str].get_options().items():
                                if caption == stats:
                                    time_stamp_dict[stats].append(value)
                
                return time_stamp_dict

    def get_port_details(self, rt_handle, session_url, kwargs):
        '''
        '''
        chassis_id, card_id, port_id = kwargs['port'].split("/")
        card_id = str(chassis_id)+"."+str(card_id)
        card_url = "%s/ixload/chassisChain/chassisList/%s/cardList" % (session_url, chassis_id)
        card_list = rt_handle.invoke('http_get', url=card_url)
        for card in card_list:
            if card_id in card['name']:
                card_id = card['objectID']
                port_list_url = "%s/ixload/chassisChain/chassisList/%s/cardList/%s/portList" % (session_url, chassis_id, card_id)
                port_list = rt_handle.invoke('http_get', url=port_list_url)
                for port_l in port_list:
                    if port_l['portId'] == int(port_id):
                        object_id = port_l['objectID']
                        port_url = "%s/%s/" % (port_list_url, object_id)
                        port_details = rt_handle.invoke('http_get', url=port_url, option=1)
                        return port_details['managementIp']

    
    def polling_interval_test(self, rt_handle, session_url, interval, file_name, aggregation_type=None):  # added argument for aggregation type
        '''
        '''
        poll_url = "%s/ixload/preferences" % (session_url)
        data = {"enableRestStatViewsCsvLogging": "True", "enableL23RestStatViews":"True", "saveDataModelSnapshot":"True"}
        self.perform_generic_patch(rt_handle, poll_url, data)
        if interval:
            poll_url = "%s/ixload/test/activeTest" % (session_url)
            data = {"csvInterval":interval}
            self.perform_generic_patch(rt_handle, poll_url, data)
        poll_ur = "%s/ixload/test" % (session_url)
        if file_name == None:
            file_name = 'C:\\ProgramData\\Ixia\\IxLoadGateway'
        data1 = {"outputDir": "true", "runResultDirFull": file_name}
        self.perform_generic_patch(rt_handle, poll_ur, data1)
        if aggregation_type:
            name = self.get_role_name(rt_handle, session_url)
            config_url = "%s/ixload/stats/%s/configuredStats" % (session_url, name)
            data = {"aggregationType": aggregation_type}   
            self.perform_generic_patch(rt_handle, config_url, data)
            
    def get_role_name(self, rt_handle, session_url):
        '''
        This method is used to get the commandList url for a provided agent name.
        Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['role'] == "Client":
                    role = activity['protocol']+activity['role']
                    return role

    def report_config(self, rt_handle, session_url, file_name):
        '''
        '''
        pre_url = "%s/ixload/preferences" % (session_url)
        data = {"enableL23RestStatViews": "True", "enableRestStatViewsCsvLogging": "True"}
        self.perform_generic_patch(rt_handle, pre_url, data)
        report_url = "%s/ixload/test/operations/generateRestReport" % (session_url)
        data = {"reportFile": file_name}
        run_stats = self.perform_generic_operation(rt_handle, report_url, data)
        return run_stats
       # self.perform_generic_post(rt_handle, report_url, data)


       
    def csv_stats (self, rt_handle, stats_return, read_file, write_file, parse = None):
        '''
        '''
        a = []
        with open(read_file, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            
            for lines in csv_reader:
                a.append(lines)
            #del a[0:10]
            #del a[1:3]
            #return (read_file, write_file)
            with open(write_file, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                for i in range(len(a)):
                    writer.writerow(a[i])
            if parse:
                with open(write_file, 'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(a[0])
                    del a[0]
                    for i in range(len(a)):
                        if "SU" in a[i]:
                            writer.writerow(a[i])
            for key in stats_return.keys():
                with open(write_file, 'r') as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for lines in csv_reader:
                        stats_return[key].append(lines[key])
        return stats_return
    
    def get_dut_mandatory_args(self, kwargs):
        '''
            get_mandatory_args will the return mandatory arguemnts.
        '''
        arg_dict = {}
        if "mode" in kwargs.keys():
            arg_dict['mode'] = kwargs['mode']

            if kwargs["mode"] == "create":
                if "no_of_dut" in kwargs.keys():
                    arg_dict['no_of_dut'] = kwargs['no_of_dut']
                    kwargs.pop('no_of_dut')
                else:
                    raise Exception('no_of_dut not found, no_of_dut is mandatory argument')
                if "type" not in kwargs.keys():
                    raise Exception('type not found, type is mandatory argument')
                
            if kwargs["mode"] == "modify":
                if "type" not in kwargs.keys():
                    raise Exception('type not found, type is mandatory argument')
                if "dut_name" not in kwargs.keys():
                    raise Exception('dut_name not found, dut_name is mandatory argument')
                
            if kwargs["mode"] == "delete" :
                if "dut_name" not in kwargs.keys():
                    raise Exception('dut_name not found, dut_name is mandatory argument')
            kwargs.pop('mode')
        else:
            raise Exception('mode not found, mode is mandatory argument')
        return (arg_dict, kwargs)

    def get_dut_range_args(self, dut_args, kwargs):
        '''
        get the dut config arguments
        '''
        args_list = [{"ServerLoadBalancer":['enable', 'tos', 'vip']},
                     {"PacketSwitch": ['vlanUniqueCount', 'firstIp', 'vlanEnable', 'vlanId', 'innerVlanEnable',
                                      'ipIncrStep', 'ipType', 'vlanIncrStep', 'vlanCount', 'ipCount', 'protocol', 'portRanges']},
                     {"VirtualDut": ['vlanUniqueCount', 'firstIp', 'vlanEnable', 'vlanId', 'innerVlanEnable',
                                    'ipIncrStep', 'ipType', 'vlanIncrStep', 'vlanCount', 'ipCount', 'protocol', 'portRanges']}] 
        ret_dict = {}
        for list in args_list:
            for key,value in list.items():
                if key == dut_args['type']:
                    for item in value:
                        if item in kwargs.keys():
                            ret_dict[item] = kwargs[item]
                            kwargs.pop(item)
        return (ret_dict)

    def get_dut_config_args(self, dut_args, kwargs):
        '''
        get the dut config arguments
        '''
        args_list = [{"ServerLoadBalancer":['enableDirectServerReturn', 'serverNetwork']},
                     {"Firewall": ['ipAddress']}, {"ExternalServer": ['ipAddress']}]
        ret_dict = {}
        for arg_list in args_list:
            for key,value in arg_list.items():
                if key == dut_args['type']:
                    for item in value:
                        if item in kwargs.keys():
                            ret_dict[item] = kwargs[item]
                            kwargs.pop(item)
        return (ret_dict, kwargs)
    
    def get_dut_args(self, kwargs):
        '''
        get the dut config arguments
        '''
        args_list = ['type', 'comment']
        ret_dict = {}
        if "type" in kwargs.keys():
            ret_dict['type'] = kwargs['type']
        if "comment" in kwargs.keys():
            ret_dict['comment'] = kwargs['comment']
        return (ret_dict, kwargs)
    
    def add_dut(self, rt_handle, session_url, dut_args, kwargs):
        '''
        add dut dict to dutList config
        '''
        dut_list_url = "%s/ixload/test/activeTest/dutList" % session_url
        self.perform_generic_post(rt_handle, dut_list_url, dut_args)
        dut_list = rt_handle.invoke('http_get', url=dut_list_url)
        return dut_list[-1]

    def edit_dut(self, rt_handle, session_url, kwargs):
        flag = False
        dut_list_url = "%s/ixload/test/activeTest/dutList" % session_url
        dut_list = rt_handle.invoke('http_get', url=dut_list_url)
        for dut in dut_list:
            if dut['name'] == kwargs['dut_name']:
                flag = True
                dut_url = "%s/%s/" % (dut_list_url, dut['objectID'])
                dut_args, kwargs = self.get_dut_args(kwargs)
                if dut_args:
                    self.perform_generic_patch(rt_handle, dut_url, dut_args)
                config_args, kwargs = self.get_dut_config_args(dut_args, kwargs)
                dut_config_url = "%s/%s/dutConfig" % (dut_list_url, dut['objectID'])
                if config_args:
                    self.perform_generic_patch(rt_handle, dut_config_url, config_args)
                if dut_args['type'] == "ServerLoadBalancer":
                    range_args = self.get_dut_range_args(dut_args, kwargs)
                    if range_args:
                        dut_range_url = "%s/slbRangeList" % (dut_config_url)
                        self.perform_generic_patch(rt_handle, dut_range_url, range_args)    
                if dut_args['type'] == "VirtualDut":
                    network_args, kwargs = self.get_args("nr_", kwargs)
                    range_args  = self.get_dut_range_args(dut_args, network_args)
                    if range_args:
                        dut_range_url = "%s/networkRangeList" % (dut_config_url)
                        self.perform_generic_patch(rt_handle, dut_range_url, range_args)
                    protocol_args, kwargs = self.get_args("ppr_", kwargs)
                    range_args = self.get_dut_range_args(dut_args, protocol_args)
                    if range_args:
                        dut_range_url = "%s/protocolPortRangeList" % (dut_config_url)
                        dut_protocol_list = rt_handle.invoke('http_get', url=dut_range_url)
                        if len(dut_protocol_list) == 0:
                            self.perform_generic_post(rt_handle, dut_range_url, range_args)
                        else:
                            for protocol_range in dut_protocol_list:
                                protocol_url = "%s/%s" % (dut_range_url, protocol_range['objectID'])
                                dut_protocol=self.perform_generic_patch(rt_handle, protocol_url, range_args)
                if dut_args['type'] == "PacketSwitch":
                    onr_network_args, kwargs = self.get_args("onr_", kwargs)
                    range_args = self.get_dut_range_args(dut_args, onr_network_args)
                    if range_args:
                        dut_range_url = "%s/originateNetworkRangeList" % (dut_config_url)
                        self.perform_generic_patch(rt_handle, dut_range_url, range_args)
                    tnr_network_args, kwargs = self.get_args("tnr_", kwargs)
                    range_args=self.get_dut_range_args(dut_args, tnr_network_args)
                    if range_args:
                        dut_range_url = "%s/terminateNetworkRangeList" % (dut_config_url)
                        self.perform_generic_patch(rt_handle, dut_range_url, range_args)
                    opr_protocol_args, kwargs = self.get_args("opr_", kwargs)
                    range_args = self.get_dut_range_args(dut_args, opr_protocol_args)
                    if range_args:
                        dut_range_url = "%s/originateProtocolPortRangeList" % (dut_config_url)
                        dut_protocol_list = rt_handle.invoke('http_get', url=dut_range_url)
                        if len(dut_protocol_list)==0:
                            self.perform_generic_post(rt_handle, dut_range_url, range_args)
                        else:
                            for protocol_range in dut_protocol_list:
                                protocol_url = "%s/%s" %(dut_range_url, protocol_range['objectID'])
                                dut_protocol=self.perform_generic_patch(rt_handle, protocol_url, range_args)
                    tpr_protocol_args, kwargs = self.get_args("tpr_", kwargs)
                    range_args= self.get_dut_range_args(dut_args, tpr_protocol_args)
                    if range_args:
                        dut_range_url = "%s/terminateProtocolPortRangeList" % (dut_config_url)
                        dut_protocol_list = rt_handle.invoke('http_get', url=dut_range_url)
                        if len(dut_protocol_list)==0:
                            self.perform_generic_post(rt_handle, dut_range_url, range_args)
                        else:
                            for protocol_range in dut_protocol_list:
                                protocol_url = "%s/%s" %(dut_range_url, protocol_range['objectID'])
                                dut_protocol=self.perform_generic_patch(rt_handle, protocol_url, range_args)
        if not flag:
            raise Exception("Dut name- %s not found, cannot be modified"%(kwargs['dut_name']))

    def delete_dut(self, rt_handle, session_url, dut_name):
        '''
        delete the given dut from the dutList config 
        '''
        flag = False
        dut_list_url = "%s/ixload/test/activeTest/dutList" % session_url
        dut_list = rt_handle.invoke('http_get', url=dut_list_url)
        for dut in dut_list:
            if dut_name == dut['name']:
                flag = True
                payload = {}
                dut_url = "%s/%s/" % (dut_list_url, dut['objectID'])
                self.perform_generic_delete(rt_handle, dut_url, payload)
        if not flag:
            raise Exception( "Dut name- %s not found, cannot be deleted"%(dut_name))
           
    def add_dut_config(self, rt_handle, session_url, dut, kwargs):
        dut_url = "%s/ixload/test/activeTest/dutList" % session_url
        config_args, kwargs = self.get_dut_config_args(dut, kwargs)
        dut_config_url = "%s/%s/dutConfig" % (dut_url, dut['objectID'])
        self.perform_generic_patch(rt_handle, dut_config_url, config_args)
        if dut['type'] == "ServerLoadBalancer":
            range_args = self.get_dut_range_args(dut, kwargs)
            if range_args:
                dut_range_url = "%s/slbRangeList" % (dut_config_url)
                self.perform_generic_patch(rt_handle, dut_range_url, range_args)   
        if dut['type'] == "VirtualDut":
            network_args, kwargs = self.get_args("nr_", kwargs)
            range_args = self.get_dut_range_args(dut, network_args)
            if range_args:
                dut_range_url = "%s/networkRangeList" % (dut_config_url)
                self.perform_generic_patch(rt_handle, dut_range_url, range_args)
            protocol_args, kwargs = self.get_args("ppr_", kwargs)
            range_args = self.get_dut_range_args(dut, protocol_args)
            if range_args:
                dut_range_url = "%s/protocolPortRangeList" % (dut_config_url)
                self.perform_generic_post(rt_handle, dut_range_url, range_args)
        if dut['type'] == "PacketSwitch":
            origin_network_args, kwargs = self.get_args("onr_", kwargs)
            range_args = self.get_dut_range_args(dut, origin_network_args)
            if range_args:
                dut_range_url = "%s/originateNetworkRangeList" % (dut_config_url)
                self.perform_generic_patch(rt_handle, dut_range_url, range_args)
            terminate_network_args, kwargs = self.get_args("tnr_", kwargs)
            range_args = self.get_dut_range_args(dut, terminate_network_args)
            if range_args:
                dut_range_url = "%s/terminateNetworkRangeList" % (dut_config_url)
                self.perform_generic_patch(rt_handle, dut_range_url, range_args)
            origin_protocol_args, kwargs = self.get_args("opr_", kwargs)
            range_args = self.get_dut_range_args(dut, origin_protocol_args)
            if range_args:
                dut_range_url = "%s/originateProtocolPortRangeList" % (dut_config_url)
                self.perform_generic_post(rt_handle, dut_range_url, range_args)
            terminate_protocol_args, kwargs = self.get_args("tpr_", kwargs)
            range_args = self.get_dut_range_args(dut, terminate_protocol_args)
            if range_args:
                dut_range_url = "%s/terminateProtocolPortRangeList" % (dut_config_url)
                self.perform_generic_post(rt_handle, dut_range_url, range_args)

    def configure_dut(self, rt_handle, session_url, kwargs):
        '''
            Create or modify or delete the DUT config
        '''
        mand_args, kwargs = self.get_dut_mandatory_args(kwargs)
        if mand_args['mode'] == "create":
            for dut in range(mand_args['no_of_dut']):
                dut_args, kwargs = self.get_dut_args(kwargs)
                dut= self.add_dut(rt_handle, session_url, dut_args, kwargs)                        
                self.add_dut_config(rt_handle, session_url, dut, kwargs)
        if mand_args['mode'] == "modify":
            self.edit_dut(rt_handle, session_url, kwargs)
        if mand_args['mode'] == "delete":
            self.delete_dut(rt_handle, session_url, kwargs['dut_name'])

    def save_rxf(self, rt_handle, session_url, rxf_file_path):
        '''
            This method saves the current rxf to the disk of the machine on which the IxLoad instance is running.
            Args:
            - session_url is the address of the session to save the rxf for
            - rxf_file_path is the location where to save the rxf on the machine that holds the IxLoad instance
        '''
        save_rxf_url = "%s/ixload/test/operations/saveAs" % (session_url)
        data = {"fullPath":rxf_file_path, "overWrite": 1}
        self.perform_generic_operation(rt_handle, save_rxf_url, data)

    def ftp_load_config(self, server, username, password, filepath):
        '''
            This method performs ftp from script server tp APP server
        '''
        try:
            session = ftplib.FTP(server, username, password)
        except Exception as err:
            raise Exception('Could establish FTP session\n {}'.format(err))
        try:
            filename = filepath.split("/")[-1]
            file_to_open = open(filepath, 'rb')
            session.storbinary('STOR {}'.format(filename), file_to_open)
            file_to_open .close()
            session.quit()
            return 1
        except Exception as err:
            raise Exception('FTP transfer failed \n {}'.format(err))

    def ftp_save_config(self, server, username, password, filename):
        '''
            This method performs ftp from APP server to script server
        '''
        try:
            session = ftplib.FTP(server, username, password)
        except Exception as err:
            raise Exception('Could establish FTP session\n {}'.format(err))
        try:
            session.retrbinary("RETR " + filename, open(filename, 'wb').write)
            session.quit()
            return 1
        except Exception as err:
            raise Exception('FTP transfer failed \n {}'.format(err))

    def sftp_save_config(self, server, username, password, localpath, remote_path):
        '''
            sftp_save_config will save the config from one machine to another using sftp protocol.
        '''
        try:
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            with pysftp.Connection(host=server, username=username, password=password, cnopts=cnopts) as sftp:
                sftp.get(localpath, remote_path)
            return 1
        except Exception as err:
            raise Exception('SFTP transfer failed \n {}'.format(err))

    def clear_chassis_list(self, rt_handle, session_url):
        '''
            This method is used to clear the chassis list. After execution no chassis should be available in the chassis_listl.
            Args:

            - session_url is the address of the session that should run the test
        '''
        chassis_list_url = "%s/ixload/chassischain/chassisList" % session_url
        delete_params = {}
        self.perform_generic_delete(rt_handle, chassis_list_url, delete_params)

    def add_chassis_list(self, rt_handle, session_url, chassis_listl):
        '''
            This method is used to add one or more chassis to the chassis list.
            Args:
            - session_url is the address of the session that should run the test
            - chassis_listl is the list of chassis that will be added to the chassis chain.
        '''
        chassis_list_url = "%s/ixload/chassisChain/chassisList" % (session_url)
        for chassis_name in chassis_listl:
            data = {"name": chassis_name}
            chassis_id = self.perform_generic_post(rt_handle, chassis_list_url, data)
            refresh_connection_url = "%s/%s/operations/refreshConnection" % (chassis_list_url, chassis_id)
            self.perform_generic_operation(rt_handle, refresh_connection_url, {})
        return refresh_connection_url
    
    def reboot_ports(self, rt_handle, session_url, port):
        chassis_id, card_id, port_id = port[0].split("/")
        card_id = str(chassis_id)+"."+str(card_id)
        card_url = "%s/ixload/chassisChain/chassisList/%s/cardList" % (session_url, chassis_id)
        card_list = rt_handle.invoke('http_get', url=card_url)
        for card in card_list:
            if card_id in card['name']:
                card_id = card['objectID']
                port_list_url = "%s/ixload/chassisChain/chassisList/%s/cardList/%s/portList" % (session_url, chassis_id, card_id)
                port_list = rt_handle.invoke('http_get', url=port_list_url)
                for port_l in port_list:
                    if port_l['portId'] == int(port_id):
                        object_id = port_l['objectID']
                        port_url = "%s/%s/operations/reboot/" % (port_list_url, object_id)
                        self.perform_generic_operation(rt_handle, port_url, {})
                        return 


    def assign_ports(self, rt_handle, session_url, port_list_per_community):
        '''
            This method is used to assign ports from a connected chassis to the required NetTraffics.
            Args:
            - session_url is the address of the session that should run the test
            - port_list_per_community is the dictionary mapping NetTraffics to ports (format -> { community name : [ port list ] })
        '''
        active_test_url = "%s/ixload/test/activeTest" % session_url
        data = {"enableForceOwnership": "true"}
        self.perform_generic_patch(rt_handle, active_test_url, data)
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        value = []
        port_list_for_community1 = copy.deepcopy(port_list_per_community)
        for key in port_list_for_community1.keys():
            name = self.get_community_name(rt_handle, key)
            port_list_per_community[name] = port_list_for_community1[key]

        for community in community_list:
            port_list_for_community = port_list_per_community.get(community["name"])
            port_list_url = "%s/%s/network/portList" % (community_list_url, community["objectID"])
            value.append(community)
            if port_list_for_community is not None:
                for port in port_list_for_community:
                    chassis_id, card_id, port_id = [int(num) for num in port.split("/")]
                    param_dict = {"chassisId": chassis_id, "cardId": card_id, "portId": port_id}
                    self.perform_generic_post(rt_handle, port_list_url, param_dict)
        # apply_config_url = "%s/ixload/test/operations/applyConfiguration" % (session_url)
        # data = {}
        # self.perform_generic_operation(rt_handle, apply_config_url, data)
        return value

    def get_objective_type(self, rt_handle, session_url):
        '''
        This method gets the test configured user objective type(simluted user, connectionpersecond.
        Args:
            - session_url is the address of the session that should run the test.
        '''
        active_test_url = "%s/ixload/test/activeTest/communityList" % (session_url)
        test_obj = rt_handle.invoke('http_get', url=active_test_url)
        for obj in test_obj:
            if obj['activeRole'] == "Client":
                return obj['userObjectiveType']

    def configure_time_line(self, rt_handle, session_url, time_line_dict):
        '''
            configure_time_line will configure the test timeline objectives.
        '''
        for item in time_line_dict.keys():
            time_line_list_url = "%s/ixload/test/activeTest/timelineList" % session_url
            test_obj = rt_handle.invoke('http_get', url=time_line_list_url)
            time_line_list_url = "%s/%s" % (time_line_list_url, test_obj[0]['objectID'])
            data = {item:time_line_dict[item]}
            self.perform_generic_patch(rt_handle, time_line_list_url, data)
    
    def get_timeline_args(self, value_dict):
        '''
            get_timeline_args will return timeline argument.
        '''
        ret_dict = {}
        activity_list = ["rampUpType", "rampUpValue", "offlineTime", "rampDownTime", "standbyTime", "rampDownValue", "rampUpInterval", "iterations",
                         "rampUpTime", "sustainTime", "timelineType", "name"]
        for key in value_dict:
            if activity_list.count(key):
                ret_dict[key] = value_dict[key]
        for key in activity_list:
            if key in value_dict.keys():
                value_dict.pop(key)
        return (ret_dict, value_dict)

    def get_mandatory_args(self, kwargs):
        '''
            get_mandatory_args will the return mandatory arguemnts.
        '''
        arg_dict = {}
        if "mode" in kwargs.keys():
            arg_dict['mode'] = kwargs['mode']
            kwargs.pop('mode')
        else:
            raise Exception('mode not found, mode is mandatory argument')
        if "role" in kwargs.keys():
            arg_dict['role'] = kwargs['role']
            kwargs.pop('role')
        else:
            raise Exception('role not found, role is mandatory argument')
        # if "network_name" in kwargs.keys():
            # arg_dict['network_name'] = kwargs['network_name']
            # kwargs.pop('network_name')
        # else:
            # raise Exception('network_name not found, network_name is a mandatory argument')
        return (arg_dict, kwargs)

    def get_mandatory_command_args(self, kwargs): #NewChange
        ''' 
            get_mandatory_command_args will the return mandatory arguemnts.
        '''
        arg_dict = {}
        if "mode" in kwargs.keys():
            arg_dict['mode'] = kwargs['mode']
            kwargs.pop('mode')
        else:
            raise Exception('mode not found, mode is mandatory argument')
        if "agent_name" in kwargs.keys():
            arg_dict['agent_name'] = kwargs['agent_name']
            kwargs.pop('agent_name')
        else:
            raise Exception('agent_name not found, agent_name is mandatory argument')
        if "commandName" in kwargs.keys():
            arg_dict['commandName'] = kwargs['commandName']
            kwargs.pop('commandName')
        else:
            raise Exception('commandName not found, commandName is mandatory argument')
        return (arg_dict, kwargs)
    
    def get_mandatory_client_args(self, kwargs):
        '''
            get_mandatory_args will the return mandatory arguemnts.
        '''
        arg_dict = {}
        if "mode" in kwargs.keys():
            arg_dict['mode'] = kwargs['mode']
            kwargs.pop('mode')
        else:
            raise Exception('mode not found, mode is mandatory argument')
        if "agentName" in kwargs.keys():
            arg_dict['agentName'] = kwargs['agentName']
            kwargs.pop('agentName')
        else:
            raise Exception('role not found, role is mandatory argument')
        # if "network_name" in kwargs.keys():
            # arg_dict['network_name'] = kwargs['network_name']
            # kwargs.pop('network_name')
        # else:
            # raise Exception('network_name not found, network_name is a mandatory argument')
        return (arg_dict, kwargs)

    def add_communities(self, rt_handle, session_url, community_option_list):
        '''
            add_communities will add community as HTTP client or server.
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        for community_option_dict in community_option_list:
            self.perform_generic_post(rt_handle, community_list_url, community_option_dict)
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        return community_list[-1]

    def add_activities_updated(self, rt_handle, session_url, activity_list_per_community, community_list):
        '''
            add_activities_updated will add the activities to the test.
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        for communivt_name, activity_list in activity_list_per_community.items():
            if community_list is None:
                raise Exception('Community %s cannot be found.' % communivt_name)
            activity_list_url = "%s/%s/activityList" % (community_list_url, community_list['objectID'])
            network_list_url = "%s/%s/network" % (community_list_url, community_list['objectID'])
            traffic_list_url = "%s/%s/traffic" % (community_list_url, community_list['objectID'])
            for activity_type in activity_list:
                options = {}
                options.update({'protocolAndType': activity_type})
                self.perform_generic_post(rt_handle, activity_list_url, options)
            self.change_name(rt_handle, network_list_url, communivt_name.split("@")[0])
            self.change_name(rt_handle, traffic_list_url, communivt_name.split("@")[-1])
        return activity_list_url

    def change_name(self, rt_handle, url, name):
        '''
            change_name will change the name of agent such as http clinet and server.
        '''
        data = {"name": name}
        self.perform_generic_patch(rt_handle, url, data)

    def get_agent_name(self, rt_handle, item_list):
        '''
            get_agent_name will return the name of the agent.
        '''
        community_list = rt_handle.invoke('http_get', url=item_list)
        return community_list[0]['name']

    def get_activity_args(self, value_dict):
        '''
            get_activity_args will return all activity args.
        '''
        activity_list = ["userIpMapping", "timerGranularity", "enableConstraint", "constraintValue",
                         "objectivePercent", "secondaryConstraintValue", "userObjectiveType", "destinationIpMapping",
                         "name", "secondaryConstraintType", "userObjectiveValue", "constraintType"]
        ret_dict = {}
        for key in value_dict:
            if activity_list.count(key):
                ret_dict[key] = value_dict[key]
        for key in activity_list:
            if key in value_dict.keys():
                value_dict.pop(key)
        return (ret_dict, value_dict)

    def get_agent_args(self, value_dict):
        '''
            get_agent_args will return agent argument.
        '''
        ret_dict = {}
        activity_list = ['vlanPriority', 'validateCertificate', 'enableDecompressSupport', 'exactTransactions', 'enableHttpsProxy',
                         'perHeaderPercentDist', 'enableSsl', 'enablePerConnCookieSupport', 'cookieRejectProbability', 'disableMacValidation',
                         'enableUnidirectionalClose', 'enableAuth', 'piggybackAck', 'httpsTunnel', 'enableEsm',
                         'certificate', 'sequentialSessionReuse', 'browserEmulationName', 'enableSslSendCloseNotify', 'cookieJarSize',
                         'dontUseUpgrade', 'maxPipeline', 'contentLengthDeviationTolerance', 'caCert', 'restObjectType',
                         'maxSessions', 'enableHttpProxy', 'disableDnsResolutionCache', 'enableTrafficDistributionForCC', 'enableTos',
                         'precedenceTOS', 'ipPreference', 'maxHeaderLen', 'flowPercentage', 'maxStreams',
                         'reliabilityTOS', 'sslRecordSize', 'privateKey', 'maxPersistentRequests', 'enablemetaRedirectSupport',
                         'delayTOS', 'enableIntegrityCheckSupport', 'commandTimeout', 'commandTimeout_ms', 'privateKeyPassword',
                         'enableConsecutiveIpsPerSession', 'followHttpRedirects', 'tcpCloseOption', 'enableVlanPriority', 'esm',
                         'httpVersion', 'enablesslRecordSize', 'sslReuseMethod', 'tcpFastOpen', 'throughputTOS', 'sslVersion', 'enableCookieSupport',
                         'enableLargeHeader', 'clientCiphers', 'enableHttpsTunnel', 'enableAchieveCCFirst', 'tos',
                         'httpProxy', 'keepAlive', 'urlStatsCount', 'enableCRCCheckSupport', 'httpsProxy', ]
        for key in value_dict:
            if activity_list.count(key):
                ret_dict[key] = value_dict[key]
        for key in activity_list:
            if key in value_dict.keys():
                value_dict.pop(key)
        return (ret_dict, value_dict)

    def get_agent_protocol_args(self, protocol, value_dict, name):
        '''
            get_agent_args will return agent argument.
        '''
        ret_dict = {}
        activity_list = self.get_protocol_args(protocol, name)
        for key in value_dict:
            if activity_list.count(key):
                ret_dict[key] = value_dict[key]
        for key in activity_list:
            if key in value_dict.keys():
                value_dict.pop(key)
        return (ret_dict, value_dict)

    def get_protocol_args(self, protocol, name):
        '''
            This method will retrun the arguments based on protocol and name.
        '''
        args = {"FTP_activity":['secondaryEnableConstraint', 'enableConstraint', 'constraintValue', 'objectivePercent', 'timelineId', 'secondaryConstraintValue', 'enable', 'userObjectiveType', 'destinationIpMapping', 'name', 'secondaryConstraintType', 'cpsObjectiveBehavior', 'userObjectiveValue', 'constraintType'], "FTP_agent":['enableTos', 'cmdListLoops', 'commandTimeout', 'enableEsm', 'ipPreference', 'flowPercentage', 'vlanPriority', 'tos', 'reliabilityTOS', 'fileList', 'delayTOS', 'precedenceTOS', 'mode', 'throughputTOS', 'esm', 'password', 'enableVlanPriority', 'userName'], "DNS_activity":['secondaryEnableConstraint', 'enableConstraint', 'constraintValue', 'objectivePercent', 'timelineId', 'secondaryConstraintValue', 'enable', 'userObjectiveType', 'destinationIpMapping', 'name', 'cpsObjectiveBehavior', 'secondaryConstraintType', 'userObjectiveValue', 'constraintType'], "DNS_agent":['lowerLayerTransport', 'publicKeyPath', 'version', 'responseTimeout', 'noWaitForResp', 'numberOfRetries'], 
                "HTTP_agent_server":['cmdListLoops', 'vlanPriority', 'validateCertificate','maxResponseDelay','docrootChunkSize','enableTls13Support','disableMacValidation','rstTimeout','enableChunkedRequest','enableEsm','enableHTTP2','certificate','enableNewSslSupport','tos','enableSslSendCloseNotify','enableMD5Checksum','httpPort','httpsPort','caCert','esm','enableTos','precedenceTOS','flowPercentage','enableChunkEncoding','privateKey','sslRecordSize','reliabilityTOS','delayTOS','privateKeyPassword','urlStatsCount','tcpCloseOption','enableVlanPriority','enableIntegrityCheck','enablesslRecordSize','dhParams','throughputTOS','requestTimeout','dontExpectUpgrade','ServerCiphers','enableDHsupport','enablePerServerPerURLstat','urlPageSize','highPerfWithSU','acceptSslConnections','minResponseDelay'], "HTTP_activity":["userIpMapping", "timerGranularity", "enableConstraint", "constraintValue", "objectivePercent", "secondaryConstraintValue", "userObjectiveType", "destinationIpMapping", "name", "secondaryConstraintType", "userObjectiveValue", "constraintType"], "HTTP_agent":['vlanPriority', 'validateCertificate', 'enableDecompressSupport', 'exactTransactions', 'enableHttpsProxy', 'perHeaderPercentDist', 'enableSsl', 'enablePerConnCookieSupport', 'cookieRejectProbability', 'disableMacValidation', 'enableUnidirectionalClose', 'enableAuth', 'piggybackAck', 'httpsTunnel', 'enableEsm', 'certificate', 'sequentialSessionReuse', 'browserEmulationName', 'enableSslSendCloseNotify', 'cookieJarSize', 'dontUseUpgrade', 'maxPipeline', 'contentLengthDeviationTolerance', 'caCert', 'restObjectType', 'maxSessions', 'enableHttpProxy', 'disableDnsResolutionCache', 'enableTrafficDistributionForCC', 'enableTos', 'precedenceTOS', 'ipPreference', 'maxHeaderLen', 'flowPercentage', 'maxStreams', 'reliabilityTOS', 'sslRecordSize', 'privateKey', 'maxPersistentRequests', 'enablemetaRedirectSupport', 'delayTOS', 'enableIntegrityCheckSupport', 'commandTimeout', 'commandTimeout_ms', 'privateKeyPassword', 'enableConsecutiveIpsPerSession', 'followHttpRedirects', 'tcpCloseOption', 'enableVlanPriority', 'esm', 'httpVersion', 'enablesslRecordSize', 'sslReuseMethod', 'tcpFastOpen', 'throughputTOS', 'sslVersion', 'enableCookieSupport', 'enableLargeHeader', 'clientCiphers', 'enableHttpsTunnel', 'enableAchieveCCFirst', 'tos', 'httpProxy', 'keepAlive', 'urlStatsCount', 'enableCRCCheckSupport', 'httpsProxy'], "FTP_agent_server":['enableTos', 'cmdListLoops', 'enableEsm', 'flowPercentage', 'vlanPriority', 'tos', 'reliabilityTOS', 'ftpPort', 'delayTOS', 'precedenceTOS', 'throughputTOS', 'esm', 'enableVlanPriority']}
        var = "%s_%s" % (protocol, name)
        return args[var]


    def clear_agents_command_list(self, rt_handle, session_url, agent_name_list):
        '''
            This method clears all commands from the command list of the agent names provided.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name_list the list of agent names for which the command list will be cleared.
        '''
        delete_params = {}
        for agent_name in agent_name_list:
            command_list_url = self.get_command_list_url_for_agent_name(rt_handle, session_url, agent_name)
            if command_list_url:
                self.perform_generic_delete(rt_handle, command_list_url, delete_params)

    def get_command_list_url_for_agent_name(self, rt_handle, session_url, agent_name):
        '''
            This method is used to get the commandList url for a provided agent name.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    agent_url = "%s/%s/agent" % (activity_list_url, activity['objectID'])
                    agent = rt_handle.invoke('http_get', url=agent_url, option=1)
                    for link in agent['links']:
                        if link['rel'] in ['actionList', 'commandList']:
                            command_list_url = link['href'].replace("/api/v0/", "")
                            return command_list_url
                        if link['rel'] in ['pm']:
                            pm_list_url = link['href'].replace("/api/v0/", "")
                            pm_list = rt_handle.invoke('http_get', url=pm_list_url, option=1)
                            for link in pm_list['links']:
                                cmd_list_url = link['href'].replace("/api/v0/", "")
                                cmd_list = rt_handle.invoke('http_get', url=cmd_list_url, option=1)
                                if isinstance(cmd_list, list):
                                    if "commandType" in cmd_list[0].keys():
                                        return cmd_list_url
                                if "links" in cmd_list.keys():
                                    for link in cmd_list['links']:
                                        cmd_list_url = link['href'].replace("/api/v0/", "")
                                        cmd_list = rt_handle.invoke('http_get', url=cmd_list_url, option=1)
                                        if isinstance(cmd_list, list):
                                            if "commandType" in cmd_list[0].keys():
                                                return cmd_list_url

    def change_objective(self, rt_handle, session_url, agent_name, value_dict):
        '''
            This method is used to get the commandList url for a provided agent name.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        try:
            community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
            community_list = rt_handle.invoke('http_get', url=community_list_url)
            for community in community_list:
                activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
                activity_list = rt_handle.invoke('http_get', url=activity_list_url)
                for activity in activity_list:
                    if activity['name'] == agent_name:
                        for key, value in value_dict.items():
                            data = {key:value}
                            self.perform_generic_patch(rt_handle, activity_list_url, data)
        except Exception as err:
            return {"status":0, "log": err}

    def change_agent_configs(self, rt_handle, session_url, agent_name, value_dict):
        '''
            This method is used to get the commandList url for a provided agent name.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    agent_url = "%s/%s/agent" % (activity_list_url, activity['objectID'])
                    for key, value in value_dict.items():
                        data = {key:value}
                        self.perform_generic_patch(rt_handle, agent_url, data)

    def add_commands(self, rt_handle, session_url, command_dict):
        '''
            This method is used to add commands to a certain list of provided agents.
            Args:
            - session_url is the address of the session that should run the test
            - command_dict is the Python dict that holds the mapping between agent name and specific commands.
            (command_dict format -> { agent name : [ { field : value } ] })
        '''
        for agent_name in command_dict.keys():
            command_list_url = self.get_command_list_url_for_agent_name(rt_handle, session_url, agent_name)
            if command_list_url:
                for command_param_dict in command_dict[agent_name]:
                    self.perform_generic_post(rt_handle, command_list_url, command_param_dict)
    
    def change_command_config(self, rt_handle, session_url, agent_name, kwargs):
        '''
            This method is used to add commands to a certain list of provided agents.
            Args:
            - session_url is the address of the session that should run the test
            - command_dict is the Python dict that holds the mapping between agent name and specific commands.
            (command_dict format -> { agent name : [ { field : value } ] })
        '''
        command_list_url = self.get_command_list_url_for_agent_name(rt_handle, session_url, agent_name)
        command_list = rt_handle.invoke('http_get', url=command_list_url)
        for item in command_list:
            if item['commandType'] == kwargs['command_type']:
                command_type_url =  "%s/%s" % (command_list_url, item['objectID'])
                data = {"arguments":self.generate_path(rt_handle, kwargs['arguments'])}
                self.perform_generic_patch(rt_handle, command_type_url, data)


    def get_activity_list_url(self, rt_handle, session_url, kwargs):
        '''
            get_activity_list_url will return the url of activity.
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if kwargs['role'] == comminuty['role']:
                activity_list_url = "%s/%s/activityList" % (community_list_url, comminuty['objectID'])
                if activity_list_url is None:
                    raise Exception("could not find the url for %s", kwargs['role'])
                return activity_list_url

    def get_args(self, types, value_dict, comp_lst=[]):
        '''
        This method will remove the prefix and return Ixload args based on type
        '''
        ret_dict = {}
        old_dict = copy.deepcopy(value_dict)
        for key in old_dict.keys():
            if types in key:
                new_key = re.sub(types, "", key, count=1)
                if comp_lst:
                    if new_key in comp_lst:
                        ret_dict[new_key] = value_dict[key]
                    else:
                        ret_dict[key] = value_dict[key]
                else:
                    ret_dict[new_key] = value_dict[key]
                value_dict.pop(key)
        return (ret_dict, value_dict)

    def get_list_args(self, types, value_list):
        '''
        This method will remove the prefix and return Ixload args based on type
        '''
        ret_list = []
        for key in reversed(value_list):
            if types in key:
                #new_key = key.strip(types)
                new_key = key.replace(types, "", 1)
                ret_list.append(new_key)
                value_list.remove(key)
        return (ret_list, value_list)

    def configure_ethernet(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure ethernet stack configuration"
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_list_utl = "%s/%s/network/stack" % (community_list_url, comminuty['objectID'])
                if "medium" in kwargs.keys():
                    ethernet_card_phy_url = "%s/%s/network/stack/cardDualPhy" % (community_list_url, comminuty['objectID'])
                    data = {"medium":kwargs["medium"]}
                    self.perform_generic_patch(rt_handle, ethernet_card_phy_url, data)
                    kwargs.pop("medium")
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch_operation(rt_handle, ethernet_list_utl, data)

    def configure_mac(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure mac configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_child_url = "%s/%s/network/stack/childrenList" % (community_list_url, comminuty['objectID'])
                ethernet_child_list = rt_handle.invoke('http_get', url=ethernet_child_url)
                mac_url = "%s/%s/macRangeList" % (ethernet_child_url, ethernet_child_list[0]['objectID'])
                data = {"enabled":"true"}
                self.perform_generic_patch_operation(rt_handle, mac_url, data)
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch_operation(rt_handle, mac_url, data)

    def configure_tcp(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure tcp configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                tcp_child_url = "%s/%s/network/globalPlugins" % (community_list_url, comminuty['objectID'])
                tcp_child_list = rt_handle.invoke('http_get', url=tcp_child_url)
                for index in range(len(tcp_child_list)):
                    if tcp_child_list[index]['itemType'] == 'TCPPlugin':
                        tcp_url = "%s/%s" % (tcp_child_url, tcp_child_list[index]['objectID'])
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch(rt_handle, tcp_url, data)

    def configure_vlan(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure vlan configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_child_url = "%s/%s/network/stack/childrenList" % (community_list_url, comminuty['objectID'])
                ethernet_child_list = rt_handle.invoke('http_get', url=ethernet_child_url)
                vlan_url = "%s/%s/vlanRangeList" % (ethernet_child_url, ethernet_child_list[0]['objectID'])
                data = {"enabled":"true"}
                self.perform_generic_patch_operation(rt_handle, vlan_url, data)
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch_operation(rt_handle, vlan_url, data)
    
    def get_community_name(self, rt_handle, name):
        community = name.split('@')
        community_name = community[1]+"@"+community[0]
        return community_name

    def configure_ip(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure vlan configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_child_url = "%s/%s/network/stack/childrenList" % (community_list_url, comminuty['objectID'])
                ethernet_child_list = rt_handle.invoke('http_get', url=ethernet_child_url)
                ip_child_url = "%s/%s/childrenList" % (ethernet_child_url, ethernet_child_list[0]['objectID'])
                ip_child_list = rt_handle.invoke('http_get', url=ip_child_url)
                if ip_child_list[0]['itemType'] == "EmulatedRouterPlugin":
                    ip_child2_url = "%s/%s/childrenList" % (ip_child_url, ip_child_list[0]['objectID'])
                    ip_child2_list = rt_handle.invoke('http_get', url=ip_child2_url)
                    ip_url = "%s/%s/rangeList" % (ip_child2_url, ip_child2_list[0]['objectID'])
                else:
                    ip_url = "%s/%s/rangeList" % (ip_child_url, ip_child_list[0]['objectID'])
                data = {"enabled":"true"}
                self.perform_generic_patch_operation(rt_handle, ip_url, data)
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch_operation(rt_handle, ip_url, data)
    
    def get_ip(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure vlan configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_child_url = "%s/%s/network/stack/childrenList" % (community_list_url, comminuty['objectID'])
                ethernet_child_list = rt_handle.invoke('http_get', url=ethernet_child_url)
                ip_child_url = "%s/%s/childrenList" % (ethernet_child_url, ethernet_child_list[0]['objectID'])
                ip_child_list = rt_handle.invoke('http_get', url=ip_child_url)
                if ip_child_list[0]['itemType'] == "EmulatedRouterPlugin":
                    ip_child2_url = "%s/%s/childrenList" % (ip_child_url, ip_child_list[0]['objectID'])
                    ip_child2_list = rt_handle.invoke('http_get', url=ip_child2_url)
                    ip_url = "%s/%s/rangeList" % (ip_child2_url, ip_child2_list[0]['objectID'])
                else:
                    ip_url = "%s/%s/rangeList" % (ip_child_url, ip_child_list[0]['objectID'])
                return (rt_handle.invoke('http_get', url=ip_url))
    
    def get_port(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure vlan configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                port_url = "%s/%s/network/portList" % (community_list_url, comminuty['objectID'])
                port_list = rt_handle.invoke('http_get', url=port_url)
                port_child_url = "%s/%s" % (port_url, port_list[0]['objectID'])
                port_child_list = rt_handle.invoke('http_get', url=port_child_url, option=1)
                return (port_child_list)

    def remove_items(self, data, prefix, args_list):
        '''
        '''
        ret_dict = {}
        if isinstance(data, dict):
            data = [data]
        if "links" in data[0]:
            data[0].pop('links')
        if "objectID" in data[0]:
            data[0].pop('objectID')
        if "itemType" in data[0]:
            data[0].pop('itemType')
        if "restObjectType" in data[0]: 
            data[0].pop('restObjectType')
        for key in data[0].keys():
            new_key = prefix + "_" + key
            if new_key in args_list:
                ret_dict[new_key] =  data[0][key]
        return ret_dict
    
    def configure_emulated_router(self, rt_handle, session_url, network_name, kwargs):
        '''
        This method will configure vlan configs
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for comminuty in community_list:
            if network_name == comminuty['name']:
                ethernet_child_url = "%s/%s/network/stack/childrenList" % (community_list_url, comminuty['objectID'])
                ethernet_child_list = rt_handle.invoke('http_get', url=ethernet_child_url)
                ip_child_url = "%s/%s/childrenList" % (ethernet_child_url, ethernet_child_list[0]['objectID'])
                ip_child_list = rt_handle.invoke('http_get', url=ip_child_url)
                if kwargs['mode'] == "create":
                    er_url = "%s/%s/operations/insertParentPlugin" % (ip_child_url, ip_child_list[0]['objectID'])
                    data = {"pluginType": "EmulatedRouterPlugin"}
                    self.perform_generic_operation(rt_handle, er_url, data)
                kwargs.pop('mode')
                ip_child_list = rt_handle.invoke('http_get', url=ip_child_url)
                er_url = "%s/%s/rangeList" % (ip_child_url, ip_child_list[0]['objectID'])
                for key, value in kwargs.items():
                    data = {key:value}
                    self.perform_generic_patch(rt_handle, er_url, data)

    def remove_chassis_list(self, rt_handle, session_url, chassis_listl):
        '''
        This method will remove chassis from connected list of Ixload.
        '''
        chassis_list_url = "%s/ixload/chassisChain/chassisList" % (session_url)
        chassis_list = rt_handle.invoke('http_get', url=chassis_list_url)
        for chassis_name in chassis_list:
            if chassis_listl:
                if chassis_name['name'] in chassis_listl:
                    data = {}
                    self.perform_generic_delete(rt_handle, chassis_list_url, data)
                    chassis_listl.remove(chassis_name['name'])
        if chassis_listl:
            raise Exception("could not find the chassis for %s", chassis_listl)
        
    def change_agent_command_configs(self, rt_handle, session_url, mand_args, value_dict):
        '''
            This method is used to get the commandList url for a provided agent name.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == mand_args['agent_name']:
                    agent_url = "%s/%s/agent/actionList" % (activity_list_url, activity['objectID'])
                    agent_url_list = rt_handle.invoke('http_get', url=agent_url)
                    for agent in agent_url_list:
                        if mand_args['commandName'] == agent['cmdName']:
                            agent_url_id = "%s/%s/agent/actionList/%s" % (activity_list_url, activity['objectID'],agent['objectID'])
                            for key, value in value_dict.items():
                                data = {key:value}
                                self.perform_generic_patch(rt_handle, agent_url_id, data)

    def emulation_protocol(self, rt_handle, session_url, network_name, protocol, method, kwargs):
        '''
            Create or modify or commnad to the Protocol Emulation for HTTP, FTP,
        '''
        
        agent_list = []
        agent_action_list = {}
        
        activity_list = {}
        if kwargs['mode'] == "create":
            mand_args, kwargs = self.get_mandatory_args(kwargs)
            if "no_of_agent" in kwargs.keys():
                no_of_agent = int(kwargs['no_of_agent'])
                kwargs.pop('no_of_agent')
            else:
                raise Exception('no_of_agent not found, no_of_agent is a mandatory argument')
            for agent_num in range(no_of_agent):
                agent_num = agent_num * 1
                agent = "%s %s" % (protocol, mand_args['role'])
                agent_list.append(agent)
            activities = {network_name:agent_list}
            communities = [{}]
            community = self.add_communities(rt_handle, session_url, communities)
            activity_url = self.add_activities_updated(rt_handle, session_url, activities, community)
            if 'agent_name' in kwargs.keys():
                self.change_name(rt_handle, activity_url, kwargs['agent_name'])
                kwargs.pop('agent_name')
            agent_name = self.get_agent_name(rt_handle, activity_url)
            if len(kwargs) > 0:
                if  mand_args['role'] == "Server":
                    self.configure_server(rt_handle, session_url, protocol, agent_name, kwargs)
                activity_list, kwargs = self.get_agent_protocol_args(protocol, kwargs, "activity")
                agent_action_list, kwargs = self.get_agent_protocol_args(protocol, kwargs, "agent")
                timeline_args, kwargs = self.get_timeline_args(kwargs)
                new_commands = {agent_name : [kwargs]}
                self.clear_agents_command_list(rt_handle, session_url, new_commands.keys())
                if len(activity_list) > 0:
                    self.change_objective(rt_handle, session_url, agent_name, activity_list)
                if len(agent_action_list) > 0:
                    if method == "type1":
                        self.change_agent_configs(rt_handle, session_url, agent_name, agent_action_list)
                    if method == "type2":
                        self.change_agent_configs_type2(rt_handle, session_url, agent_name, agent_action_list)
                if len(timeline_args)> 0 :
                    self.configure_time_line(rt_handle, session_url, timeline_args)
                if len(kwargs) > 0:
                    new_commands = {agent_name : [kwargs]}
                    self.add_commands(rt_handle, session_url, new_commands)
                
        elif kwargs['mode'] == "modify":
            mand_args, kwargs = self.get_mandatory_args(kwargs)
            activity_url = self.get_activity_list_url(rt_handle, session_url, mand_args)
            if len(kwargs) > 0:
                agent_name = self.get_agent_name(rt_handle, activity_url)
                activity_list, kwargs = self.get_activity_args(kwargs)
                timeline_args, kwargs = self.get_timeline_args(kwargs)
                if len(activity_list) > 0:
                    self.change_objective(rt_handle, session_url, agent_name, activity_list)
                agent_action_list, kwargs = self.get_agent_protocol_args(protocol, kwargs, "agent_server")
                if len(agent_action_list) > 0:    
                    if method == "type1":
                        self.change_agent_configs(rt_handle, session_url, agent_name, agent_action_list)
                    if method == "type2":
                        self.change_agent_configs_type2(rt_handle, session_url, agent_name, agent_action_list)
                agent_args_list, kwargs = self.get_agent_args(kwargs)
                if len(agent_args_list) > 0:    
                    if method == "type1":
                        self.change_agent_configs(rt_handle, session_url, agent_name, agent_args_list)
                    if method == "type2":
                        self.change_agent_configs_type2(rt_handle, session_url, agent_name, agent_args_list)
                if len(timeline_args)> 0 :
                    self.configure_time_line(rt_handle, session_url, timeline_args)
                if "command_type" in kwargs:
                    self.change_command_config(rt_handle, session_url, agent_name, kwargs)
        elif kwargs['mode'] == "modify_command":
            mand_args, kwargs = self.get_mandatory_command_args(kwargs)
            self.change_agent_command_configs(rt_handle, session_url, mand_args, kwargs)
        elif kwargs['mode'] == "add_command":
            mand_args, kwargs = self.get_mandatory_client_args(kwargs)
            if len(kwargs) > 0:
                data = {'role':'Client'}
                activity_url = self.get_activity_list_url(rt_handle, session_url, data)
                new_commands = {mand_args['agentName'] : [kwargs]}
                self.add_commands(rt_handle, session_url, new_commands)
            else:
                raise Exception('command arguments not found, please provide command arguments to configure')
    
    def generate_path(self, rt_handle, supported_file):
        if ("\\" in rt_handle.file_path):
            supported_file_name = supported_file.split("\\")[-1]
            filePath = rt_handle.file_path + '\\' + supported_file_name
            return filePath
        else:
            supported_file_name = supported_file.split("/")[-1]
            filePath = rt_handle.file_path + '/' + supported_file_name
            return filePath
        

    def change_agent_configs_type2(self, rt_handle, session_url, agent_name, value_dict):
        '''
            This method is used to get the commandList url for a provided agent name.
            Args:
            - session_url is the address of the session that should run the test
            - agent_name is the agent name for which the commandList address is provided
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    if 'cmdListLoops' or 'flowPercentage' in value_dict.keys():
                        agent_url = "%s/%s/agent" % (activity_list_url, activity['objectID'])
                        for key, value in value_dict.items():
                            if key in ['cmdListLoops', 'flowPercentage']:
                                data = {key: value}
                                self.perform_generic_patch(rt_handle, agent_url, data)
                                value_dict.pop(key)
                    else:
                        agent_url = "%s/%s/agent/pm/advancedOptions" % (activity_list_url, activity['objectID'])
                        for key, value in value_dict.items():
                            data = {key: value}
                            self.perform_generic_patch(rt_handle, agent_url, data)

    def remove_port(self, rt_handle, session_url, port_list_per_community):
        '''
        This method will remove ports which is assign to Traffic/Network.
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % (session_url)
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            port_list_for_community = port_list_per_community.get(community['name'])
            port_list_url = "%s/%s/network/portList" % (community_list_url, community['objectID'])
            if port_list_for_community is not None:
                data = {}
                self.perform_generic_delete(rt_handle, port_list_url, data)

    def configure_server(self, rt_handle, session_url, protocol, agent_name, kwargs):
        '''
            This method will configure Server configurations
        '''
        if protocol == "HTTP":
            self.configure_http_server(rt_handle, session_url, agent_name, kwargs)
        elif protocol == "FTP":
            self.configure_ftp_server(rt_handle, session_url, agent_name, kwargs)
            
    def configure_ftp_server(self, rt_handle, session_url, agent_name, kwargs):
        '''
            This method will configure FTP server configuration.
        '''
        agent_action_list, kwargs = self.get_agent_protocol_args("FTP", kwargs, "agent_server")
        if len(agent_action_list) > 0:
            self.change_agent_configs(rt_handle, session_url, agent_name, agent_action_list)
        if len(kwargs) > 0:
            self.configure_real_file_list(rt_handle, session_url, agent_name, kwargs)

    def configure_http_server(self, rt_handle, session_url, agent_name, kwargs):
        '''
            This method will configure HTTP server configuration.
        '''
        agent_action_list, kwargs = self.get_agent_protocol_args("HTTP", kwargs, "agent_server")
        web_list, kwargs = self.get_args("wl_", kwargs)
        custom_payload_list, kwargs = self.get_args("cpl_", kwargs)
        cookie_list, kwargs = self.get_args("cl_", kwargs)
        cookie_content_list, kwargs = self.get_args("ccl_", kwargs)
        if len(agent_action_list) > 0:
            self.change_agent_configs(rt_handle, session_url, agent_name, agent_action_list)
        if len(web_list) > 0:
            self.configure_web_page_list(rt_handle, session_url, agent_name, web_list)
        if len(custom_payload_list) > 0:
            self.configure_custom_payload(rt_handle, session_url, agent_name, custom_payload_list)
        if len(cookie_list) > 0:
            self.configure_cookie_list(rt_handle, session_url, agent_name, cookie_list, cookie_content_list)

    def configure_web_page_list(self, rt_handle, session_url, agent_name, kwargs):
        '''
        This method will configure HTTP server Weblist
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    web_list_url = "%s/%s/agent/webPageList" % (activity_list_url, activity['objectID'])
                    self.perform_generic_post(rt_handle, web_list_url, kwargs)

    def configure_custom_payload(self, rt_handle, session_url, agent_name, kwargs):
        '''
        This method will configure HTTP server Custom payload list
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    custom_payload_url = "%s/%s/agent/customPayloadList" % (activity_list_url, activity['objectID'])
                    self.perform_generic_post(rt_handle, custom_payload_url, kwargs)

    def configure_cookie_list(self, rt_handle, session_url, agent_name, kwargs, cookie_content_list):
        '''
        This method will configure HTTP server Custom payload list
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    cookie_list_url = "%s/%s/agent/cookieList" % (activity_list_url, activity['objectID'])
                    self.perform_generic_post(rt_handle, cookie_list_url, kwargs)
                    cookie_list = rt_handle.invoke('http_get', url=cookie_list_url)
                    cookie_content_url = "%s/%s/cookieContentList" % (cookie_list_url, cookie_list[-1]['objectID'])
                    self.perform_generic_post(rt_handle, cookie_content_url, cookie_content_list)

    def configure_real_file_list(self, rt_handle, session_url, agent_name, kwargs):
        '''
        This method will configure HTTP server Custom payload list
        '''
        community_list_url = "%s/ixload/test/activeTest/communityList" % session_url
        community_list = rt_handle.invoke('http_get', url=community_list_url)
        for community in community_list:
            activity_list_url = "%s/%s/activityList" % (community_list_url, community['objectID'])
            activity_list = rt_handle.invoke('http_get', url=activity_list_url)
            for activity in activity_list:
                if activity['name'] == agent_name:
                    file_list_url = "%s/%s/agent/realFileList" % (activity_list_url, activity['objectID'])
                    self.perform_generic_post(rt_handle, file_list_url, kwargs)

    def get_session_status(self, rt_handle, session_url):
        '''
            This method will return the status of Ixload session.
        '''
        reply = rt_handle.invoke('http_get', url=session_url, option=1)
        if reply['isActive'] == True:
            return session_url
