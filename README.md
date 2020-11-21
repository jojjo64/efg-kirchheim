# EFG Kirchheim automation
This github project is holding all Automation Task files for EFG Kirchheim/Teck

## EFG WiFi Automation
EFG WiFi automation automates MAC address filter updates to a Unifi CloudKey.

### Usage

    usage: efg_wifi_automation.py [-h] [--configfile CONFIGFILE] macfile wifi_name
    
    EFG WiFi automation: update Unifi Cloud Key mac address filter
    
    positional arguments:
      macfile               the name of the file with mac addresses
      wifi_name             the Cloud Key WiFi name (SSID) to work on
    
    optional arguments:
      -h, --help            show this help message and exit
      --configfile CONFIGFILE
                            our configfile

### Configfile

You need to configure the configfile as follows:

    [CloudKey]
    host = <ip>
    user = <user>
    password = <password>
    
* set the cloud key IP into the `host` var
* set user and password of a CloudKey user with administrative rights into the `user` and `password` vars