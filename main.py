from nmap3 import Nmap
import pandas as pd
import ipaddress
import configparser
import pathlib, os
import time
import datetime
import platform

# Check if running on Windows for sound notifications
if platform.system() == "Windows":
    import winsound

# Initialize Nmap, configuration, and paths
config = configparser.ConfigParser()
py_path = pathlib.Path(__file__).parent.resolve()

# Lists and dictionaries to store data
addresses = []  # List of IP addresses
subnets = []  # List of subnets to scan
nmap = Nmap()  # Nmap object for scanning

ip_results = {}  # Dictionary to store scan results for each IP address

DIR_DATA = os.path.join(py_path, "data")

# Function to create the 'data' directory if it doesn't exist
def directories():
    dir_check_data = os.path.isdir(DIR_DATA)

    if dir_check_data == False:
        os.mkdir(os.path.join(DIR_DATA))
        print("Data folder created.")


# Function to create the configuration file if it doesn't exist
def config_create():
    if not os.path.exists(os.path.join(py_path, "config.ini")):
        config.add_section("SEARCH SETTINGS")
        config.set("SEARCH SETTINGS", "IDENTIFY SERVICE VERSION", "False")
        config.set("SEARCH SETTINGS", "STEALTH SEARCH", "False")

        config.add_section("DATA SETTINGS")
        config.set("DATA SETTINGS", "VIEW DATA", "False")
        config.set("DATA SETTINGS", "MAX ROW", "100")

        config.add_section("MISC SETTINGS")
        config.set("MISC SETTINGS", "DEFAULT USAGE", "1")
        config.set("MISC SETTINGS", "SLEEP", "3")
        config.set("MISC SETTINGS", "IP ONLY MODE", "False")

        with open((os.path.join(py_path, "config.ini")), "w") as configfile:
            config.write(configfile)
    return config


# Read configuration from the 'config.ini' file
config.read(os.path.join(py_path, "config.ini"))


# Function to input initial IP addresses
def initial():
    print(
        """
          Please provide the IPs one at a time
          This will add the items to a list
          Once you have finished adding either enter blank or type 'next'
          """
    )
    while True:
        address = input("IP: ")
        if address == "" or address == "next":
            print(
                f"""
    The following addresses have been added: 
                  {subnets}
"""
            )
            break
        if config["MISC SETTINGS"]["IP ONLY MODE"] == "False":
            if address not in subnets:
                subnets.append(address)
        else:
            try:
                ipaddress.ip_address(address)
                if address not in subnets:
                    subnets.append(address)
            except ValueError:
                print("Not a valid address!")


# Function for the main scanning logic
def main():
    while True:
        # Choose manual or automated scanning
        usage_type = input(
            """
                        please select an option:
                        [1]manual
                        [2]automated
                        =========================
                        """
        ).lower()
        if (
            usage_type == "1"
            or usage_type == "2"
            or usage_type == "manual"
            or usage_type == "automated"
            or usage_type == ""
        ):
            if usage_type == "":
                default = config["MISC SETTINGS"]["DEFAULT USAGE"]
                print(f"No option selected, defaulting to [{default}]")
                usage_type = default
            loop = True

            # Check for conflicting search settings
            if (
                config["SEARCH SETTINGS"]["STEALTH SEARCH"] == "True"
                and config["SEARCH SETTINGS"]["Identify Service Version"] == "True"
            ):
                print(
                    'Stealth and cpe cannot be active at the same time! ignoring "Identify Service Version"'
                )

            # Set Nmap arguments based on configuration
            if (
                config["SEARCH SETTINGS"]["Identify Service Version"] == "True"
                and config["SEARCH SETTINGS"]["STEALTH SEARCH"] == "False"
            ):
                print(
                    """
        |===========================================================|
        |Please be PATIENT detecting cpe takes longer to proccess...|
        |===========================================================|
    """
                )
                sub_scan_arg = "-sV"

            else:
                sub_scan_arg = "-O"

            break
        else:
            print("\ninvalid usage type!\n")

    while loop == True:
        if not subnets:
            print(
                """\n
                  |================================|
                  |      No Subnets provided!      |
                  |         SHUTTING DOWN!         |
                  |================================|
                  """
            )
            break

        if usage_type == "1" or usage_type == "manual":
            loop = False

        for i in subnets:
            now = datetime.datetime.now().strftime("%Y-%m-%d @%H:%M")
            target_subnet = i
            if config["SEARCH SETTINGS"]["STEALTH SEARCH"] == "True":
                sub_scan = nmap.nmap_stealth_scan(target_subnet, arg=sub_scan_arg)

                if "error" in sub_scan:
                    print(f'{sub_scan["msg"]} [Stealth Mode Enabled]')
                else:
                    print("Performing Stealth Search...")
            else:
                if "/" in target_subnet:
                    sub_scan = nmap.scan_top_ports(target_subnet, args=sub_scan_arg)
                else:
                    sub_scan = nmap.nmap_subnet_scan(target_subnet, args=sub_scan_arg)
            for host, info in sub_scan.items():

                try:
                    state = info["state"]["state"]

                    if state == "up":
                        os_name = info["osmatch"][0]["name"]
                        os_accuracy = info["osmatch"][0]["accuracy"]
                        operating_system = [{"os": os_name, "os accuracy": os_accuracy + "%"}]
                        df_device_info = pd.DataFrame.from_dict(operating_system)
                        df_net_info = pd.DataFrame.from_dict(info["ports"])
                          
                        df_dir = os.path.join(DIR_DATA, f"{host}_scan.csv")
                        
                        if host in ip_results:

                            old_df = ip_results[host]
                            if df_net_info.equals(old_df):
                                pass
                            else:
                                df_changes = df_net_info.compare(old_df)
                                for _, row in df_changes.iterrows():
                                    print(f"[{now}] Changes for {host} on Port {row.name}: {row['self']} to {row['other']}\n{df_changes}")

                                ip_results[host] = df_net_info

                                df = pd.concat(
                                    [df_device_info, df_net_info], ignore_index=True
                                )
                                df = df.set_index("os")

                                df.to_csv(df_dir)

                                if config["DATA SETTINGS"]["VIEW DATA"] == "True":
                                    print(f"\n[{now}] {host}\n{df}")
                        else:

                            ip_results[host] = df_net_info

                            df = pd.concat(
                                [df_device_info, df_net_info], ignore_index=True
                            )
                            df = df.set_index("os")

                            print(f"[{now}] Initial scan for {host}:\n{df}")
                            df.to_csv(df_dir)

                            if config["DATA SETTINGS"]["VIEW DATA"] == "True":
                                print(f"\n[{now}] {host}\n{df}")

                    if host not in addresses and state == "up":
                        addresses.append(host)
                        print(f"[{now}] new address found: {host}")

                        if platform.system() == "Windows":
                            try:
                                winsound.PlaySound("ping.wav", winsound.SND_FILENAME)
                            except:
                                print("FAILED TO PLAY SOUND!")
                except:
                    pass

        if loop == True:
            time.sleep(int(config["MISC SETTINGS"]["SLEEP"]))
            print(f"\n\n[{now}] Searching for new IPs...")


# Entry point of the script
if __name__ == "__main__":
    directories()
    config_create()
    pd.set_option("display.max_rows", int(config["DATA SETTINGS"]["MAX ROW"]))
    initial()
    main()
