import os, time, sys
from ixload import IxLoad
import yaml


def configure_ixload(config_file, http_client, http_server, objective , save_file):
    ix = IxLoad()
    print ("Connecting to Ixload")
    ix_conn = ix.connect(gateway_server="10.20.179.197", gateway_port="8080", ixload_version="9.30.0.331")
    print (ix_conn)
    rxf_file_path="C:/Users/waseebai/Documents/tencent/ixload/ixload/" + config_file
    print (ix.load_config(rxf_file_path=rxf_file_path))
    for conf in http_client:
        print (ix.emulation_http(conf) )
        for commamd in conf['Commands']:
            print(ix.emulation_http(commamd))
    for serv in http_server:
        print (ix.emulation_http(serv))
    
    for obj in objective:
        print (ix.emulation_http(obj))
    
    portlist_per_community = {"Traffic1@Network1" : ["1/11/3"], "Traffic2@Network2": ["1/11/7"]}
    print(ix.add_chassis(chassis_list="10.39.46.4",portlist_per_community=portlist_per_community))
    print(ix.stats_config(polling_interval=2, file_path='C:\\ProgramData\\Ixia\\IxLoadGateway'))
    
    print(ix.set_config(force=1))
    print(ix.start_test())
    stat_name1 = {"HTTP_Client":["HTTP Simulated Users"]}
    file_path = "C:/Users/waseebai/Documents/tencent/ixload/ixload/"
    file_name = "HTTP_Client_stats"
    time.sleep(120)
    stats= ix.poll_csv_stats(stats_to_display=stat_name1, file_name=file_name, file_path=file_path, username="admin", password="admin", server=1, parse=0)
    print(stats)
    rxf_file_path="C:/Users/waseebai/Documents/tencent/ixload/ixload/" + save_file
    print (ix.save_config(rxf_file_path=rxf_file_path, server=1))
    print(ix.disconnect())


def load_yaml():
    config_params = {}
    yaml_to_import = os.path.dirname(__file__) + "/Test-Config.yaml"
    testinfo = yaml.load(open(yaml_to_import), Loader=yaml.FullLoader)
    #for key, values in testinfo.items():
    #    for test in values:
    for test in testinfo['TestConfigurations']:
            config_file = test['Testcase']['RxfName']
            http_client = test['Testcase']['Http_client']
            http_server = test['Testcase']['Http_server']
            objective = test['Testcase']['ObjectiveSettings']
            save_file = test['Testcase']['SaveName']
            configure_ixload(config_file, http_client, http_server, objective, save_file)

# def test_script():
#     data = parse_yaml()

if __name__ == "__main__":
    load_yaml()