# EFG Kirchheim Automation

This github project is holding all Automation Task files for EFG Kirchheim/Teck. It comprises of three parts:

* the WiFi automation (Unifi Cloud Key automation)
* the Office365 MS Planner automation
* an umbrella app `efg_automation.py` that orchestrates the entire automation process using the parts listed above

The automation flow is as follows:

* a frontend request process with approval (which is not part of this git project) triggers an MS Flow workflow
* the MS Flow workflow creates a Planner task (the task must have a defined format) in a Planner plan
  dedicated to the MAC address filter automation
* that s the place where we start here:
   * all open Planner tasks from the MS Planner plan are read
   * for each task (ADDMAC or DELMAC) the MAC address contained in the task gets either added or deleted to the Unifi
     Cloud Key MAC filter list
   * finally the MS Planner task is set to completed

## Configuration file `efg_automation.ini`

The `efg_automation.ini` configuration file holds settings for all automation parts. Refer to the example configuration
file to learn the file layout. 

## EFG Office365 Automation: The `efg_o365.py` module

The EFG Office365 Automation can read MS Planner tasks for ADDing or DELeting MACs and - after the task has been
completed - sets the task to completed. This requires an API setup in the MS O365 Admin area. It has a restricted
command set from command line and offers more functions when used as a python module.

Information and Alert Messages can be sent to a MS Teams Channel via a webhook (that needs to be configured in MS Teams)
.

The EFG Office365 Automation module is based on and extends the `O365` package available from pypi.


## EFG WiFi Automation The `efg_wifi_automation.py` module

The EFG WiFi Automation automates MAC address filter updates to a Unifi CloudKey. It has a restricted command set from
command line and offers more functions when used as a python module.

The EFG WiFi Automation module is based on and extends the `pyunifi` package available from pypi.


## Detailed documentation

A detailed documentation in **asciidoc** format is available here: 

   [EFG Automation Detailed Documentation](docs/efg_automation.adoc)
   
Please refer to this document for Installation and Setup instructions.