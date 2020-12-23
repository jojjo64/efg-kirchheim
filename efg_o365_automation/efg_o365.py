# --------------------------------------------------------------------------------------
# A replacement for the planner.py file of the O365 python package
#
# As of 2020-12 the planner.py implementation is incomplete in that
#  * it does not implement a class & methods to get task details
#  * it does not copy all attributes from the MS graph REST API call
#  * it only implements methods to get a task object but no methods for updating
#
# 2020-12 J. Brauer
# --------------------------------------------------------------------------------------

import argparse
import configparser
import copy
import logging
import sys
from pathlib import Path

import requests
from O365 import Account
from O365.utils import ApiComponent




class EFGTaskDetail(ApiComponent):
   '''
      the O365 Planner Task Detail object representation
   '''
   _endpoints = {}
   
   def __init__ (self, *, parent=None, con=None, **kwargs):
      """ A Microsoft planner task details object
      :param parent: parent object
      :type parent: EFGTask
      :param Connection con: connection to use if no parent specified
      :param Protocol protocol: protocol to use if no parent specified
       (kwargs)
      :param str main_resource: use this resource instead of parent resource
       (kwargs)
      """
      if parent and con:
         raise ValueError('Need a parent or a connection but not both')
      self.con = parent.con if parent else con
      
      cloud_data = kwargs.get('data', {})
      
      self.object_id = cloud_data.get('id')
      
      # Choose the main_resource passed in kwargs over parent main_resource
      main_resource = kwargs.pop('main_resource', None) or (
         getattr(parent, 'main_resource', None) if parent else None)
      
      main_resource = '{}{}'.format(main_resource, '')
      
      super().__init__(
         protocol=parent.protocol if parent else kwargs.get('protocol'),
         main_resource=main_resource)
      
      # copy the task detail values to object attributes
      # for a list of attributes refer to
      for key, value in cloud_data.items():
         # print(f'key {key} value {value}')
         setattr(self, key, value)




class EFGTask(ApiComponent):
   '''
      the O365 Planner Task object representation with methods
   '''
   _endpoints = {
      'get_task_details': '/planner/tasks/%id%/details',
      'patch_task': '/planner/tasks/%id%',
   }
   
   taskdetail_constructor = EFGTaskDetail
   
   def __init__ (self, *, parent=None, con=None, **kwargs):
      """ A Microsoft planner task
      :param parent: parent object
      :type parent: Planner
      :param Connection con: connection to use if no parent specified
      :param Protocol protocol: protocol to use if no parent specified
       (kwargs)
      :param str main_resource: use this resource instead of parent resource
       (kwargs)
      """
      # print(f'Task parent is {parent} con is {con}')
      if parent and con:
         raise ValueError('Need a parent or a connection but not both')
      self.con = parent.con if parent else con
      
      cloud_data = kwargs.get(self._cloud_data_key, {})
      
      # Choose the main_resource passed in kwargs over parent main_resource
      main_resource = kwargs.pop('main_resource', None) or (
         getattr(parent, 'main_resource', None) if parent else None)
      
      main_resource = '{}{}'.format(main_resource, '')
      
      super().__init__(
         protocol=parent.protocol if parent else kwargs.get('protocol'),
         main_resource=main_resource)
      
      for key, value in cloud_data.items():
         # print(f'key {key} value {value}')
         setattr(self, key, value)
   
   #
   def get_task_details (self):
      '''
         get the task details for the current task object
      
         :return: a Task Detail object for the task details of this task object
      '''
      url = self.build_url(self._endpoints.get('get_task_details').replace('%id%', self.id))
      
      response = self.con.get(url)
      
      if not response:
         return None
      
      data = response.json()
      
      return self.taskdetail_constructor(parent=self, **{'data': data})
   
   #
   def update_task_percent_complete (self):
      '''
         update the task completion status with the percentComplete object attribute value
      '''
      
      url = self.build_url(self._endpoints.get('patch_task').replace('%id%', self.id))
      
      response = self.con.patch(url,
                                {'percentComplete': self.percentComplete},
                                headers={'If-Match': getattr(self, '@odata.etag')})
      # TODO: add error handling
      print(f'response {response.__dict__}')
   
   #
   def set_task_completed (self):
      '''
         set task to 100% complete and update (patch) the task
      '''
      self.percentComplete = 100
      self.update_task_percent_complete()




class EFGPlanner(ApiComponent):
   """ A microsoft planner class
       In order to use the API following permissions are required.
       Delegated (work or school account) - Group.Read.All, Group.ReadWrite.All
   """
   
   _endpoints = {
      'get_my_tasks': '/me/planner/tasks',
   }
   task_constructor = EFGTask
   
   def __init__ (self, *, parent=None, con=None, **kwargs):
      """ A Planner object
      :param parent: parent object
      :type parent: Account
      :param Connection con: connection to use if no parent specified
      :param Protocol protocol: protocol to use if no parent specified
       (kwargs)
      :param str main_resource: use this resource instead of parent resource
       (kwargs)
      """
      if parent and con:
         raise ValueError('Need a parent or a connection but not both')
      self.con = parent.con if parent else con
      # print(f'Planner con is {self.con}')
      
      # Choose the main_resource passed in kwargs over the host_name
      main_resource = kwargs.pop('main_resource',
                                 '')  # defaults to blank resource
      super().__init__(
         protocol=parent.protocol if parent else kwargs.get('protocol'),
         main_resource=main_resource)
   
   def __str__ (self):
      return self.__repr__()
   
   def __repr__ (self):
      return 'Microsoft Planner'
   
   def get_my_tasks (self, *args):
      ''' returns a list of tasks assigned to the logged in user '''
      
      url = self.build_url(self._endpoints.get('get_my_tasks'))
      
      response = self.con.get(url)
      
      if not response:
         return None
      
      data = response.json()
      
      return [
         self.task_constructor(parent=self, **{self._cloud_data_key: task})
         for task in data.get('value', [])]




class EFGPlannerConfig(object):
   '''
      simple class to process our configuration file
      we use the python builtin configparser for processing an INI file with key/value pairs grouped in sections
   '''
   
   def __init__ (self, configfile=None):
      ''' process config file, pull out our vars '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # check if config file exists, else raise an exception
      f = Path(configfile)
      if not f.is_file():
         raise ValueError(f'configfile "{configfile}" not found!')
      
      # set up the config parser and read in our config file
      config = configparser.ConfigParser()
      config.read(configfile)
      
      # check for existence of keys we need
      # NOTE: all these stmts will throw a KeyError exception if either the section or one of the keys does not exist
      planner_config = config['O365_Planner']
      self.efg_tenant = planner_config['tenant']
      self.app_id = planner_config['app_id']
      self.app_token = planner_config['app_token']
      self.planner_wifi_automation_bucket_id = planner_config['wifi_automation_bucket_id']




class ManageEFGWiFiPlannerTasks(object):
   '''
      manage (orchestrate) the methods of the classes above
   '''
   
   def __init__ (self, configfile, **kwargs):
      '''
      
         :param configfile:
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self.kwargs = kwargs
      # get our config
      self.configfile = configfile
      self.config = EFGPlannerConfig(configfile=self.configfile)
      # establish O365 access with our app and tenant settings
      self.account = Account((self.config.app_id, self.config.app_token), tenant_id=self.config.efg_tenant)
      self.open_tasks = []
      # usually we reuse the stored oauth token so we should usually run into the else branch here
      # NOTE: if we are NOT authenticated the code flow blocks here until an interactive user has
      # granted app access with the granting URL offered here and has pasted back the grant confirmation URL
      # here
      # however once an app has been granted and the stored oauth token exists (o365_token.txt) then the
      # token is valid for 90 days, and if the app is reused within these 90 days to access O365 then
      # token lifetime is extended to another 90 days (according to the MS docs).
      if not self.account.is_authenticated:
         if self.kwargs.get('do_initial_auth', None):
            if self.account.authenticate(scopes=['basic', 'tasks_all']):
               logger.info('Authenticated (initial)!')
            else:
               logger.critical('Authentication failed!!!')
         else:
            logger.critical('(Re)Authentication required but "do_initial_auth" not set!!!')
            # TODO: add alering, e.g. via e-mail or TEAMS Chat...
      else:
         logger.info('Authenticated (reuse token)!')
   
   def get_all_open_WiFiAutomation_planner_tasks (self):
      '''
         get all open tasks for WiFi automation (identify them by bucket and percent complete == 0)
         get task details as well and add a reference as "efg_task_details" attribute to the task object
         
         :return:
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      planner = EFGPlanner(parent=self.account)
      for task in planner.get_my_tasks():
         # logger.debug(f'task: {task.__dict__}')
         # only handle tasks with EFGAutomation Planner Board bucket id
         if task.bucketId != self.config.planner_wifi_automation_bucket_id: continue
         # ignore completed tasks
         if task.percentComplete == 100: continue
         task.efg_task_details = task.get_task_details()
         self.open_tasks.append(task)
      return self.open_tasks




class EFGWiFiAutomationNotifications(object):
   '''
      the class for sending notifications (infos, alerts, ...) for the EFG WiFi Automation
      currently we use a webook to send messages to a MS Teams Channel
   '''
   
   def _read_config (self):
      '''
         read all required notification parameters
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # check if config file exists, else raise an exception
      f = Path(self.configfile)
      if not f.is_file():
         raise ValueError(f'configfile "{self.configfile}" not found!')
      
      # set up the config parser and read in our config file
      config = configparser.ConfigParser()
      config.read(self.configfile)
      
      # check for existence of keys we need
      # NOTE: all these stmts will throw a KeyError exception if either the section or one of the keys does not exist
      notification_config = config['EFG_Notifications']
      self.msteams_webhook = notification_config['msteams_webhook']
      self.msteams_adaptive_card_info = notification_config['msteams_adaptive_card_info']
      self.msteams_adaptive_card_warning = notification_config['msteams_adaptive_card_warning']
      self.msteams_adaptive_card_error = notification_config['msteams_adaptive_card_error']
   
   def __init__ (self, configfile=None):
      '''
         initialize -- mainly: read our config
      
         :param configfile:
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self.configfile = configfile
      self._read_config()
   
   def _send_message (self, type=None, message=None):
      '''
         send a message to a MS Teams Chat webhook URL
         the message JSON body is from a configuration file and has a placeholder __MESSAGE__ for the message
         to pass to MS Teams Chat
         so we replace that placeholder with the message to send...
      
         :param type: the message type (info, warning, error)
         :param message: the message to send
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      if type == 'info':
         message = copy.deepcopy(self.msteams_adaptive_card_info).replace('__MESSAGE__', message)
      elif type == 'warning':
         message = copy.deepcopy(self.msteams_adaptive_card_warning).replace('__MESSAGE__', message)
      elif type == 'error':
         message = copy.deepcopy(self.msteams_adaptive_card_error).replace('__MESSAGE__', message)
      else:
         raise ValueError(f'invalid message type: "{type}"!!!')
      
      logger.debug(f'message: {message}')
      headers = {'content-type': 'application/json'}
      # important: use UTF-8 encoding for proper German umlaut representation...
      result = requests.post(self.msteams_webhook, headers=headers, data=message.encode('utf-8'))
      logger.debug(f'result is {result}')
   
   def send_info_message (self, message):
      '''
         send an info message (this is a shortcut to _send_message)
      
         :param message: the message to send
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self._send_message(type='info', message=message)
   
   def send_warning_message (self, message):
      '''
         send a warning message (this is a shortcut to _send_message)

         :param message: the message to send
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self._send_message(type='warning', message=message)
   
   def send_error_message (self, message):
      '''
         send an error message (this is a shortcut to _send_message)

         :param message: the message to send
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self._send_message(type='error', message=message)




if __name__ == "__main__":
   '''
      the EFG O365 Planner Tasks CLI
   '''
   logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()
   
   # process arguments
   parser = argparse.ArgumentParser(description='EFG O365 Planner Task automation: manage Planner Tasks')
   parser.add_argument("command",
                       choices=('show_open_tasks',),
                       help="the command to execute",
                       )
   parser.add_argument("--configfile",
                       help="our configfile",
                       default='efg_automation.ini'
                       )
   args = parser.parse_args(sys.argv[1:])
   
   if args.command == 'show_open_tasks':
      o365manageobj = ManageEFGWiFiPlannerTasks(
         args.configfile,
      )
      print(f'\n\nOpen Planner Tasks for WiFi Automation:')
      print('==============================================')
      for task in o365manageobj.get_all_open_WiFiAutomation_planner_tasks():
         print(f'   id "{task.id}" title "{task.title}" description "{task.efg_task_details.description}"')
