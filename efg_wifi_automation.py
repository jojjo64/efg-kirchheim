import argparse
import configparser
import logging
import re
import sys
from pathlib import Path

from pyunifi.controller import Controller as pyunifi_Controller




class pyunifi_WiFi_Controller(pyunifi_Controller):
   '''
      An extension to pyunifi: add methods required for Unifi Cloud Key automation at the EFG Kirchheim.
      Extensions are:
      
       * added methods to change WiFi configuration settings
   '''
   
   #
   def _get_wifi_settings (self, wifi_id):
      '''
         get the config settings for a particular WiFi (WLAN)
      
         :param wifi_id: the id of the WLAN to get the settings for
         :return: all settings for the WLAN given by id
      '''
      return self._api_read(f'rest/wlanconf/{wifi_id}')
   
   #
   def get_current_mac_filter_list (self, wifi_name):
      '''
         get the current MAC address filter list for a particular WiFi (WLAN)
         for whathever reason the REST API endpoint that gets called via _get_wifi_settings() returns a list
         of results, so we blindly take the 0th (first) element in the list and return the mac_filter_list list
         FIX: convert the MACs to all lowercase for comparisons during a remove MAC operation
      
         :param wifi_name: the name of the WLAN to get the MAC address list for
         :return: the MAC address list for the WLAN given by id
      '''
      wifi_id = self.get_wifi_id_by_name(wifi_name)
      return list(map(lambda x: x.lower() if type(x) is str else x,
                      self._get_wifi_settings(wifi_id)[0]['mac_filter_list']))
   
   #
   def _update_wifi_settings (self, wifi_id, params):
      '''
         general interface to update WiFi settings
         
         :param wifi_id: the id of the WLAN to update the settings for
         :param params: params must hold a dict of valid wifi config key/value pairs
         :return:
      '''
      self._api_update(f'rest/wlanconf/{wifi_id}', params=params)
   
   #
   def get_wifi_id_by_name (self, name):
      """ get the internal wifi ID by searching for the WiFi name in the WiFi config"""
      for wifi_net in self.get_wlan_conf():
         if wifi_net['name'] == name:
            return wifi_net['_id']
      raise ValueError(f'No WiFi with name (SSID) "{name}" found!')

   #
   def update_wifi_activate_deactivate_mac_filter (self, wifi_name, enabled=True):
      """ either activate or deactivate MAC filtering """
      assert enabled in (True, False), 'parameter error: enabled must be either True or False!'
      # get the wifi id for the wifi name
      wifi_id = self.get_wifi_id_by_name(wifi_name)
      self._update_wifi_settings(wifi_id, params={'mac_filter_enabled': enabled})

   #
   def update_wifi_set_mac_filter_policy (self, wifi_name, policy='allow'):
      """ set MAC filtering to either allow (whitelist) or deny (blacklist) mode """
      assert policy in ('allow', 'deny'), 'parameter error: policy can only be "allow" or "deny"!'
      wifi_id = self.get_wifi_id_by_name(wifi_name)
      self._update_wifi_settings(wifi_id, params={'mac_filter_policy': policy})

   def _validate_mac_filter_list(self, mac_address_list):
      '''
         validates a list of MAC addresses. If a MAC address has an invalid format, raise a
         ValueError :exception
      '''
      assert type(mac_address_list) in (tuple, list), 'parameter error: mac_address_list must be tuple or list!'
      
      for i, m in enumerate(mac_address_list):
         # regex from https://stackoverflow.com/questions/7629643/how-do-i-validate-the-format-of-a-mac-address
         # however removed dash as a separator -- we only accept colons as a separator...
         if not re.match("[0-9a-f]{2}([:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", m.lower()):
            raise ValueError(f'MAC address at list index {i}: invalid MAC address "{m}"!')
   
   #
   def set_wifi_mac_filter_list (self, wifi_name, mac_address_list):
      '''
         set (overwrite) the wifi MAC address filter
      
         :param wifi_name: the name of the WLAN to get the MAC address list for
         :param mac_address_list: the list of MACs to set the filter to
      '''
      # get the wifi id for the wifi name
      wifi_id = self.get_wifi_id_by_name(wifi_name)
      self._validate_mac_filter_list(mac_address_list)
      self._update_wifi_settings(wifi_id, params={'mac_filter_list': mac_address_list})
   
   #
   def add_mac_to_mac_filter (self, wifi_name, mac_address):
      '''
         add a MAC address to the current MAC filter list
         
         :param wifi_name: the name of the WLAN to get the MAC address list for
         :param mac_address: the MAC address to add
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')

      # get the current list of MACs in the MAC address filter
      # if the MAC to add is not contained, add it and update the entire list
      mac_address_list = self.get_current_mac_filter_list(wifi_name)
      if mac_address.lower() not in mac_address_list:
         mac_address_list.append(mac_address.lower())
         logger.info(f'MAC address {mac_address.lower()} was not in MAC list -- added...')
         self.set_wifi_mac_filter_list(wifi_name, mac_address_list)
      else:
         logger.warning(f'MAC address {mac_address.lower()} already contained in MAC list -- no action taken...')
         # ToDo: add exception
   
   #
   def remove_mac_from_mac_filter (self, wifi_name, mac_address):
      '''
         remove a MAC address from the current MAC filter list
         FIX: convert the MACs to all lowercase for comparisons during a remove MAC operation

         :param wifi_name: the name of the WLAN to get the MAC address list for
         :param mac_address: the MAC address to remove
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # get the current list of MACs in the MAC address filter
      # if the MAC to remove is contained, remove it and update the entire list
      mac_address_list = self.get_current_mac_filter_list(wifi_name)
      if mac_address.lower() in mac_address_list:
         mac_address_list.remove(mac_address.lower())
         logger.info(f'MAC address {mac_address.lower()} was in MAC list -- removed...')
         self.set_wifi_mac_filter_list(wifi_name, mac_address_list)
      else:
         logger.warning(f'MAC address {mac_address.lower()} NOT found in MAC list -- no action taken...')
         # ToDo: add exception




class EFGFCloudKeyConfig(object):
   '''
      simple class to process our configuration file
      we use the python builtin configparser for processing an INI file with key/value pairs grouped in sections
   '''
   
   def __init__(self, configfile=None):
      ''' process config file, pull out our vars '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      
      # check if config file exists, else raise an exception
      f = Path(configfile)
      if not f.is_file():
         raise ValueError(f'configfile "{configfile}" not found!')
      
      # set up the config parser and read in our config file
      config = configparser.ConfigParser()
      config.read(configfile)
      
      # check for existence of keys we need
      # NOTE: all these stmts will throw a KeyError exception if either the section or one of the keys does not exist
      cloudkey_config = config['CloudKey']
      self.cloudkey_host = cloudkey_config['host']
      self.cloudkey_user = cloudkey_config['user']
      self.cloudkey_password = cloudkey_config['password']
      self.cloudkey_update_mac_file_on_add_remove = cloudkey_config.getboolean('update_mac_file_on_add_remove')






class EFGMACFile(object):
   '''
      simple class to process the MAC address file
      the class has
      
       * a list with the mac addresses (self.mac_address_list)
       * a dict with mac addresses and comments (self.mac_address_list_extended)
       
      the dict will be used when the list of MACs is written back to the mac address file
      the idea behind maintaining a file is:
      
       * in case of a fatal event in the Cloud Key (e.g. memory error) the entire list of MACs is lost
         (ok you should have a daily backup of the entire config -- in that case you are okay and don t need
         the restore function offered here)
       * to restore the list, simply take the file and load it via CLI using the "set_mac_filter" command
   '''

   def __init__ (self, macfile=None):
      ''' NOTE: no MAC address validation done, only file processing '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
   
      self.macfile = macfile
      self.mac_address_list = {}
      self.mac_address_list_extended = {}
      self._process_macfile()

   def _process_macfile(self):
      ''' open file, ignore / remove comments and return a list of MACs '''
      # check if macfile exists, else raise an exception
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      f = Path(self.macfile)
      if not f.is_file():
         raise ValueError(f'macfile "{self.macfile}" not found!')

      with open(self.macfile) as f:
         self.macfilelines = f.readlines()
         for l in self.macfilelines:
            # ignore empty / blank lines
            if l is None or l == '': continue
            # ignore comment lines starting with hash in col 1
            if l.startswith('#'): continue
            # if we have an inline comment, e.g.
            #    aa:bb:cc:dd:ee:ff      # John Doe
            # split it away and remove blanks
            mac_address_wifi_name = l.split('#')[0].strip()
            mac_address = mac_address_wifi_name.split(';')[0].strip()
            wifi_name = mac_address_wifi_name.split(';')[1].strip()
            comment = l.split('#')[1].strip()
            if wifi_name not in self.mac_address_list.keys():
               self.mac_address_list[wifi_name] = []
            self.mac_address_list[wifi_name].append(mac_address)
            if wifi_name not in self.mac_address_list_extended:
               self.mac_address_list_extended[wifi_name] = {}
            self.mac_address_list_extended[wifi_name][mac_address] = comment
   
   def write_macfile (self):
      '''
         write the MAC address file with both mac addresses and comments back to disk
         prepend with a file header
         FIX: convert MACs to lowercase
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')

      file_header = '''# -----------------------------------------------------------------------------
# MAC address file
#  * MAC addresses must have the format hh:hh:hh:hh:hh:hh
#  * MAC addresses must start in col 1, one MAC per line
#  * then - separated with a semicolon - the WiFi name (SSID) has to follow
#  * line comments are allowed (starting with a # in col 1)
#  * inline comments (after the MAC, separated with a #) are allowed as well
#  * all comments will be removed during processing
# -----------------------------------------------------------------------------
'''
      with open(self.macfile, 'w') as f:
         f.write(file_header)
         for wifi_name in self.mac_address_list_extended.keys():
            for mac_address, comment in self.mac_address_list_extended[wifi_name].items():
               f.write(f'{mac_address.lower()};{wifi_name}   # {comment}\n')

   def get_mac_list_for_wifi_name(self, wifi_name):
      ''' return the mac address list for the WiFi name (SSID) '''
      return self.mac_address_list[wifi_name]
   
   def add_mac (self, mac_address, wifi_name, comment):
      '''
         add a MAC to both the simple list and the extended dict and update file
         FIX: convert the MACs to all lowercase for comparisons during a remove MAC operation
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      if wifi_name not in self.mac_address_list.keys():
         self.mac_address_list[wifi_name] = []
      if mac_address.lower() not in self.mac_address_list[wifi_name]:
         self.mac_address_list[wifi_name].append(mac_address.lower())
      if wifi_name not in self.mac_address_list_extended.keys():
         self.mac_address_list_extended[wifi_name] = {}
      self.mac_address_list_extended[wifi_name][mac_address.lower()] = comment
      self.write_macfile()
   
   def remove_mac (self, mac_address, wifi_name):
      '''
         remove a MAC from both the simple list and the extended dict and update file
         FIX: convert the MACs to all lowercase for comparisons during a remove MAC operation
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      if wifi_name in self.mac_address_list.keys():
         if mac_address.lower() not in self.mac_address_list[wifi_name]:
            self.mac_address_list[wifi_name].remove(mac_address.lower())
      if wifi_name in self.mac_address_list_extended.keys():
         if mac_address.lower() in self.mac_address_list_extended[wifi_name].keys():
            del self.mac_address_list_extended[wifi_name][mac_address.lower()]
      self.write_macfile()




class Manage_MACFilter(object):
   '''
      the class to manage the CloudKey MAC Filter
      it manages (orchestrates) the methods of the classes above
   '''
   
   def __init__ (self, macfile, configfile, wifi_name = None):
      '''
         store all parameters
         initialize the config and MAC address objects
         connect to the CloudKey and get the id of the WiFi given by name
      
         :param macfile: the file with the MAC addresses
         :param wifi_name: the WiFi name / SSID to update
         :param configfile: our configuration file (holding data how to access the Cloud Key)
      '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      
      self.macfile = macfile
      self.configfile = configfile
      self.wifi_name = wifi_name
      
      # read in our config
      self.config = EFGFCloudKeyConfig(configfile=configfile)
      # read in the MAC address file
      if self.macfile is not None:
         self.mac_object = EFGMACFile(macfile=macfile)
      # connect to the CloudKey
      self.cloudkey_connect = pyunifi_WiFi_Controller(
         self.config.cloudkey_host,
         self.config.cloudkey_user,
         self.config.cloudkey_password,
         ssl_verify=False
      )

   def get_macs (self):
      '''
         :return: the list of current MAC addresses
      '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      result = self.cloudkey_connect.get_current_mac_filter_list(self.wifi_name)
      logger.debug(f'result: {result}')
      return result
   
   #
   def add_mac_to_mac_filter (self, wifi_name, mac_address, comment):
      '''
         add a MAC to a MAC filter
         add the MAC as well to the contents of the MAC address backup file
      
         :param wifi_name: the WiFi name (SSID) to work on
         :param mac_address: the MAC address to add
         :param comment: a comment for the MAC (usually the owner name)
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # add the new MAC to both the CloudKey and (if configured) the backup MAC address file
      self.cloudkey_connect.add_mac_to_mac_filter(wifi_name, mac_address)
      if self.config.cloudkey_update_mac_file_on_add_remove:
         self.mac_object.add_mac(mac_address, wifi_name, comment)
   
   #
   def remove_mac_from_mac_filter (self, wifi_name, mac_address):
      '''
         remove a MAC from a MAC filter
         remove the MAC as well from the contents of the MAC address backup file

         :param wifi_name: the WiFi name (SSID) to work on
         :param mac_address: the MAC address to add
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # remove the MAC to both the CloudKey and (if configured) the backup MAC address file
      self.cloudkey_connect.remove_mac_from_mac_filter(wifi_name, mac_address)
      if self.config.cloudkey_update_mac_file_on_add_remove:
         self.mac_object.remove_mac(mac_address, wifi_name)
   
   #
   def set_wifi_mac_filter_from_file (self):
      '''
         set the WiFi MAC address filter to the contents of a file
         any existing MAC filter content is overwritten
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # ...and finally apply the new MAC address list
      self.cloudkey_connect.set_wifi_mac_filter_list(self.wifi_name, self.mac_object.get_mac_list_for_wifi_name(self.wifi_name))
      logger.info(
         f'Successfully updated MAC filter for WiFi {self.wifi_name}: Applied {len(self.mac_object.mac_address_list)} MAC addresses.')




if __name__ == "__main__":
   '''
      the EFG Wifi Automation CLI
   '''
   
   # process arguments
   parser = argparse.ArgumentParser(description='EFG WiFi automation: manage Unifi Cloud Key mac address filter')
   parser.add_argument("command",
                       choices=('show_macs', 'set_mac_filter'),
                       help="the command to execute",
                       )
   parser.add_argument("--wifi_name",
                       help="the Cloud Key WiFi name (SSID) to work on",
                       required=True,
                       )
   parser.add_argument("--macfile",
                       help="the name of the file with mac addresses (not required for the 'show_macs' command)",
                       )
   parser.add_argument("--configfile",
                       help="our configfile (default is efg_automation.ini)",
                       default='efg_automation.ini'
                       )
   parser.add_argument("--debug",
                       help="print debug output",
                       default=False,
                       action='store_true',
                       )
   parser.add_argument("--info",
                       help="print info output",
                       default=False,
                       action='store_true',
                       )
   args = parser.parse_args(sys.argv[1:])
   
   # depending on parameters set either debug or info output
   if args.debug:
      logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                          format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   elif args.info:
      logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                          format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()

   if args.command == 'show_macs':
      macmanageobj = Manage_MACFilter(
         None,
         args.configfile,
         args.wifi_name
      )
      print(f'\n\nMAC addresses for WiFi WLAN with SSID {macmanageobj.wifi_name}:')
      print('===========================================================')
      for mac in macmanageobj.get_macs():
         print(f'   "{mac}"')
   elif args.command == 'set_mac_filter':
      # do main processing
      try:
         macmanageobj = Manage_MACFilter(
            args.macfile,
            args.configfile,
            args.wifi_name
         )
         macmanageobj.set_wifi_mac_filter_from_file()
      # in case of an exception: raise an alert. Here we could as well send a mail or whatever alerting we prefer...
      except Exception as e:
         logger.critical(f'Caught exception {e} in call set_wifi_mac_filter_from_file!')
      else:
         logger.info(f'MAC address file {args.macfile} processed successfully.')
