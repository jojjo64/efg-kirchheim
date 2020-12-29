import argparse
import configparser
import logging
import sys
from pathlib import Path

from efg_o365 import MSTeamsAutomationNotifications, ManageEFGWiFiPlannerTasks
from efg_wifi_automation import Manage_MACFilter




class EFGAutomation(object):
   '''
      the EFG automation class offers a CLI to call and orchestrate all automation tasks
   '''

   def _read_config (self):
      '''
         read all required EFG automation parameters
      '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
   
      # check if config file exists, else raise an exception
      f = Path(self.configfile)
      if not f.is_file():
         raise ValueError(f'configfile "{self.configfile}" not found!')
   
      # set up the config parser and read in our config file
      config = configparser.ConfigParser()
      config.read(self.configfile)
   
      # check for existence of keys we need
      # NOTE: all these stmts will throw a KeyError exception if either the section or one of the keys does not exist
      efgautomation_config = config['EFGAutomation']
      self.send_msteams_status_messages = efgautomation_config.getboolean('send_msteams_status_messages')
      self.send_msteams_error_messages = efgautomation_config.getboolean('send_msteams_error_messages')

   def __init__(self, mstnotifications, configfile='efg_automation.ini', wifi_name=None):
      '''
         object initialization:
          * store parameters
          * parse our config
          
         :param mstnotifications: the already set up MS Teams Notification Environment
         :param configfile: our config file
         :param wifi_name: (optional) the WiFi Name (SSID) to work on (else the default from the config is taken)
      '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      
      self.mstnotifications = mstnotifications
      self.configfile = configfile
      self.wifi_name = wifi_name
      self._read_config()
      
   def process_wifi_mac_tasks(self):
      '''
         process all open WiFi MAC address management tasks listed in MS Planner
      '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      
      self.manage_planner_tasks = ManageEFGWiFiPlannerTasks(self.configfile)
      self.manage_wifi = Manage_MACFilter('mac_addresses.txt', self.configfile, self.wifi_name)
      
      # loop thru all open MAC address tasks
      i = 0
      for task in self.manage_planner_tasks.get_all_open_EFGWiFiAutomation_planner_tasks():
         # either add a new MAC address...
         if task.efg_mac_command == 'addmac':
            self.manage_wifi.add_mac_to_mac_filter(
               task._task_details.efg_mac_address,
               task.efg_mac_comment
            )
         # ... or remove a MAC address
         elif task.efg_mac_command == 'delmac':
            self.manage_wifi.remove_mac_from_mac_filter(
               task._task_details.efg_mac_address
            )
         else:
            raise ValueError(f'efg_mac_command "{task.efg_mac_command}" task {task.__dict__} is invalid!!!')
         # set task to completed
         task.set_task_completed()
         i += 1
         
      # if the config directs us to send a status message, prepare and send one...
      if self.send_msteams_status_messages:
         if i == 0:
            statusmessage = 'No open WiFi MAC tasks found...'
         else:
            statusmessage = f'processed {i} WiFi MAC tasks...'
         logger.info(statusmessage)
         self.mstnotifications.send_info_message(statusmessage)
         



def process_wifi_mac_tasks(args):
   '''
      wrapper to fire up the EFGAutomation class and kick off WiFi MAC task processing
      embed the EFGAutomation call in a try / except clause to catch a possible exception
      the MS Teams notification environment is set up as well to report an exception if we encounter one
   
      :param args: the validated command line args
   '''
   logger = logging.getLogger()
   logger.info('EFGAutomation process_wifi_mac_tasks starts...')
   try:
      mstnotifications = MSTeamsAutomationNotifications(args.configfile)
   except Exception as e:
      logger.exception(f'caught exception {e} in setting up MSTeamsAutomationNotifications!!!')
   else:
      try:
         a = EFGAutomation(mstnotifications, configfile=args.configfile, wifi_name=args.wifi_name)
         a.process_wifi_mac_tasks()
      # in case of an exception: raise an alert. Here we could as well send a mail or whatever alerting we prefer...
      except Exception as e:
         errmsg = f'Caught exception "{e}" in EFGAutomation-->process_wifi_mac_tasks!'
         logger.critical(errmsg)
         mstnotifications.send_error_message(errmsg)
      else:
         logger.info('EFGAutomation process_wifi_mac_tasks ends without error')




if __name__ == "__main__":
   '''
      the EFG Automation CLI
   '''
   logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()
   
   # process arguments
   parser = argparse.ArgumentParser(description='the EFG Automation CLI')

   # introduce a subparser in case we get more commands in the future (never say never :-)
   subparsers = parser.add_subparsers(dest='command')
   
   # the WiFi automation commands
   wifimacparser = subparsers.add_parser('process_wifi_mac_tasks', help='process all open WiFi MAC filter list tasks')
   # the config file
   wifimacparser.add_argument("--configfile",
                              help="our configfile (default is efg_automation.ini)",
                              default='efg_automation.ini'
   )
   wifimacparser.add_argument("--wifi_name",
                              help="the WiFi name (SSID) to work on (optional -- if not given, the config default is used)",
                              default=None
   )
   args = parser.parse_args(sys.argv[1:])

   # WiFi automation tasks
   if args.command == 'process_wifi_mac_tasks':
      process_wifi_mac_tasks(args)
   else:
      errmsg = f'unknown command "{args.command}"!!!'
      logger.critical(errmsg)
      raise ValueError(errmsg)
