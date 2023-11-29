from nmap3 import Nmap
import winsound
import pandas as pd, numpy as np
import ipaddress
import configparser
import pathlib, os
import time
import datetime

config = configparser.ConfigParser()
py_path = pathlib.Path(__file__).parent.resolve()

pd.set_option('display.max_rows', 100)
addresses = []
subnets = []
nmap = Nmap()

def directories():
    DIR_DATA = os.path.join(py_path,'data')
    dir_check_data = os.path.isdir(DIR_DATA)

    if dir_check_data == False:
        os.mkdir(os.path.join(DIR_DATA))
        print('Data folder created.')

def config_create():
    if not os.path.exists(os.path.join(py_path, "config.ini")):
        config.add_section("SETTINGS")
        config.set("SETTINGS", "IDENTIFY SERVICE VERSION", "False")
        config.set("SETTINGS", "SLEEP", "10")
        config.set("SETTINGS", "DEFAULT USAGE", "1")
        config.set("SETTINGS", "VIEW DATA", "False")
        config.set("SETTINGS", "IP ONLY MODE", "False")


        with open((os.path.join(py_path, "config.ini")), "w") as configfile:
            config.write(configfile)
    return config

config.read(os.path.join(py_path, "config.ini"))

def initial():
    print('''
          Please provide the IPs one at a time
          This will add the items to a list
          Once you have finished adding either enter blank or type 'next'
          ''')
    while True:
        address = input('IP: ')
        if address == '' or address == 'next':
            print(f'''
    The following addresses have been added: 
                  {subnets}
''')
            break
        if config['SETTINGS']['IP ONLY MODE'] == 'False':
            if address not in subnets:
                subnets.append(address)
        else:
            try:
                ipaddress.ip_address(address)
                if address not in subnets:
                    subnets.append(address)
            except ValueError:
                print('Not a valid address!')

def main():
    while True:
        usage_type = input('''
                        please select an option:
                        [1]manual
                        [2]automated
                        =========================
                        ''').lower()
        if usage_type == '1' or usage_type == '2' or usage_type == 'manual' or usage_type == 'automated' or usage_type =='':
            if usage_type == '':
                default = config["SETTINGS"]["DEFAULT USAGE"]
                print(f'No option selected, defaulting to [{default}]')
                usage_type = default
            loop = True
            if config['SETTINGS']["Identify Service Version"] == 'True':
                print('''
        |===========================================================|
        |Please be PATIENT detecting cpe takes longer to proccess...|
        |===========================================================|
    ''')
                sub_scan_arg='-O -sV'
            else: sub_scan_arg='-O'
            break
        else: print('\ninvalid usage type!\n')
    
    while loop == True:
        if subnets == []:
            break
        if usage_type == '1' or usage_type == 'manual':
            loop = False
        for i in subnets:
            now = datetime.datetime.now().strftime("%Y-%m-%d @%H:%M")
            target_subnet = i

            sub_scan = nmap.nmap_subnet_scan(target_subnet,args=sub_scan_arg)
            for host, info in sub_scan.items():
                try:
                    state = info['state']['state']
                    if state == 'up':
                        os_name = info['osmatch'][0]['name']
                        os_accuracy = info['osmatch'][0]['accuracy']
                        os = [{'os' : os_name, 'os accuracy' : os_accuracy+'%'}]
                        df_device_info = pd.DataFrame.from_dict(os)
                        df_net_info = pd.DataFrame.from_dict(info['ports'])
                        df = pd.concat([df_device_info, df_net_info], ignore_index=True)
                        df = df.set_index('os')
                        replace_empty_list = lambda x: np.nan if isinstance(x, list) and not x else x
                        df = df.map(replace_empty_list)
                        df.to_csv('data/'+f'{host}_scan.csv')

                        if config['SETTINGS']["VIEW DATA"] == 'True':
                            print(f'\n{host}\n{df}')

                    if host not in addresses and state == 'up':
                        addresses.append(host)
                        print(f'[{now}] new address found: {host}')
                        try:
                            winsound.PlaySound('ping.wav', winsound.SND_FILENAME)
                        except: print('FAILED TO PLAY SOUND!')
                except:
                    pass

        if loop == True:
            time.sleep(int(config['SETTINGS']["SLEEP"]))
            print(f'[{now}] Searching for new IPs...')

if __name__ == "__main__":
    subnets = ['192.168.1.0','google.com']
directories()
config_create()
initial()
main()