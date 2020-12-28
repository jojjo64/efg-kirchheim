# EFG Kirchheim Automation

This github project is holding all Automation Task files for EFG Kirchheim/Teck. It comprises of three parts:

* the WiFi automation (Unifi Cloud Key automation)
* the Office365 MS Planner automation
* an umbrella app `efg_automation.py` that orchestrates the entire automation process using the parts listed above

The automation flow is as follows:

* a frontend request process with approval (which is not part of this git project) triggers an MS Flow workflow
* the MS Flow workflow creates a Planner task (the task must have a defined format) in a Planner board (bucket)
  dedicated to the MAC address filter automation
* that s the place where we start here:
   * all open Planner tasks from the MS Planner bucket are read
   * for each task (ADDMAC or DELMAC) the MAC address contained in the task gets either added or deleted to the Unifi
     Cloud Key MAC filter list
   * finally the MS Planner task is set to completed

## Configuration file `efg_automation.ini`

The `efg_automation.ini` configuration file holds settings for all automation parts. Refer to the example configuration
file to learn the file layout. The subchapters will give details on required config file settings for each of the
automation parts.

## EFG Office365 Automation

The EFG Office365 Automation can read MS Planner tasks for ADDing or DELeting MACs and - after the task has been
completed - sets the task to completed. This requires an API setup in the MS O365 Admin area. It has a restricted
command set from command line and offers more functions when used as a python module.

Information and Alert Messages can be sent to a MS Teams Channel via a webhook (that needs to be configured in MS Teams)
.

### Usage from Command Line

      usage: efg_o365.py [-h] [--configfile CONFIGFILE] {show_open_tasks}
      
      EFG O365 Planner Task automation: manage Planner Tasks
      
      positional arguments:
        {show_open_tasks}     the command to execute
      
      optional arguments:
        -h, --help            show this help message and exit
        --configfile CONFIGFILE
                              our configfile

### Required Configfile Settings

The required settings for the MS O365 Automation are:

      [O365_Planner]
      tenant = <yourtenant>
      app_id = <app_id>
      app_token = <app_token>
      wifi_automation_bucket_id = <bucket_id>

* the app requires an app registration. The `O365` python package available from pypi is used as a base. Refer 
  to https://github.com/O365/python-o365#authentication-steps 
  and follow the instructions titled "Authenticate on behalf of a user" to register this app.
* from the app registration you receive the values for `tenant`, `app_id` and `app_token`
* the `wifi_automation_bucket_id` should refer to the MS Planner bucket where you place your tasks for WiFi automation

## EFG WiFi Automation

The EFG WiFi Automation automates MAC address filter updates to a Unifi CloudKey. It has a restricted command set from
command line and offers more functions when used as a python module.

### Usage from Command Line

      usage: efg_wifi_automation.py [-h] [--wifi_name WIFI_NAME] [--macfile MACFILE]
                                    [--configfile CONFIGFILE]
                                    {show_macs,set_mac_filter}
      
      EFG WiFi automation: manage Unifi Cloud Key mac address filter
      
      positional arguments:
        {show_macs,set_mac_filter}
                              the command to execute
      
      optional arguments:
        -h, --help            show this help message and exit
        --wifi_name WIFI_NAME
                              the Cloud Key WiFi name (SSID) to work on (optional --
                              if not given, the config default is used)
        --macfile MACFILE     the name of the file with mac addresses (not required
                              for the 'show_macs' command)
        --configfile CONFIGFILE
                              our configfile

Usage Notes:

* if you do not specify the `--wifi_name` parameter, the WiFi name (SSID) of the config file (key `default_wifi_name`)
  will be used
* the `show_macs` command shows the MAC addresses set in the WiFi filter of the SSID in question
* the `set_mac_filter` command sets (= completely overwrites) the MAC address filter of the SSID in question

### Required Configfile Settings

The required settings for the WiFi Automation are:

    [CloudKey]
    host = <ip>
    user = <user>
    default_wifi_name = <yourdefaultSSID>
    password = <password>

* set the cloud key IP into the `host` var
* you can set the default WLAN name (SSID) here in the config, then you do not have to specify that on the command line
* set user and password of a CloudKey user with administrative rights into the `user` and `password` vars

### MAC address file

The rules for setting up a MAC address file are:

* each MAC address has to be on a separate line in the file
* the only allowed delimiter between two hex values is a colon `:`
* line comments are allowed: they must start with a hash `#` in column 1 of a line
* inline comments following a MAC address are allowed as well:
   * they must be separated from the MAC address by one or more blanks
   * they must start with a hash `#`
* blank lines are allowed as well and will be ignored

An example MAC address file showing these conventions looks like this:

    # John Doe
    aa:bb:cc:dd:ee:ff
    11:22:33:44:55:66      # Jane Doe
