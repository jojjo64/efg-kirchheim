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
   def get_current_mac_filter_list (self, wifi_id):
      '''
         get the current MAC address filter list for a particular WiFi (WLAN)
         for whathever reason the REST API endpoint that gets called via _get_wifi_settings() returns a list
         of results, so we blindly take the 0th (first) element in the list and return the mac_filter_list list
      
         :param wifi_id: the id of the WLAN to get the MAC address list for
         :return: the MAC address list for the WLAN given by id
      '''
      return self._get_wifi_settings(wifi_id)[0]['mac_filter_list']
   
   #
   def _update_wifi_settings (self, wifi_id, params):
      '''
         general interface to update WiFi settings
         
         :param wifi_id:
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
   def update_wifi_activate_deactivate_mac_filter (self, wifi_id, enabled=True):
      """ either activate or deactivate MAC filtering """
      assert enabled in (True, False), 'parameter error: enabled must be either True or False!'
      self._update_wifi_settings(wifi_id, params={'mac_filter_enabled': enabled})

   #
   def update_wifi_set_mac_filter_policy (self, wifi_id, policy='allow'):
      """ set MAC filtering to either allow (whitelist) or deny (blacklist) mode """
      assert policy in ('allow', 'deny'), 'parameter error: policy can only be "allow" or "deny"!'
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
   def set_wifi_mac_filter_list (self, wifi_id, mac_address_list):
      '''
         set (overwrite) the wifi MAC address filter
      
         :param wifi_id: the id of the WLAN to add the MAC address to the current filter
         :param mac_address_list: the list of MACs to set the filter to
      '''
      self._validate_mac_filter_list(mac_address_list)
      self._update_wifi_settings(wifi_id, params={'mac_filter_list': mac_address_list})
   
   #
   def add_mac_to_mac_filter (self, wifi_id, mac_address):
      '''
         add a MAC address to the current MAC filter list
         
         :param wifi_id: the id of the WLAN to add the MAC address to the current filter
         :param mac_address: the MAC address to add
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # get the current list of MACs in the MAC address filter
      # if the MAC to add is not contained, add it and update the entire list
      mac_address_list = self.get_current_mac_filter_list(wifi_id)
      if mac_address not in mac_address_list:
         mac_address_list.append(mac_address)
         logger.info(f'MAC address {mac_address} was not in MAC list -- added...')
         self.set_wifi_mac_filter_list(wifi_id, mac_address_list)
      else:
         logger.warning(f'MAC address {mac_address} already contained in MAC list -- no action taken...')
         # ToDo: add exception
   
   #
   def remove_mac_from_mac_filter (self, wifi_id, mac_address):
      '''
         remove a MAC address from the current MAC filter list

         :param wifi_id: the id of the WLAN to remove the MAC address from the current filter
         :param mac_address: the MAC address to remove
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # get the current list of MACs in the MAC address filter
      # if the MAC to remove is contained, remove it and update the entire list
      mac_address_list = self.get_current_mac_filter_list(wifi_id)
      if mac_address in mac_address_list:
         mac_address_list.remove(mac_address)
         logger.info(f'MAC address {mac_address} was in MAC list -- removed...')
         self.set_wifi_mac_filter_list(wifi_id, mac_address_list)
      else:
         logger.warning(f'MAC address {mac_address} NOT found in MAC list -- no action taken...')
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
      self.cloudkey_default_wifi_name = cloudkey_config['default_wifi_name']
      self.cloudkey_user = cloudkey_config['user']
      self.cloudkey_password = cloudkey_config['password']




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
            mac_address = l.split('#')[0].strip()
            comment = l.split('#')[1].strip()
            self.mac_address_list.append(mac_address)
            self.mac_address_list_extended[mac_address] = comment
   
   def write_macfile (self):
      '''
         write the MAC address file with both mac addresses and comments back to disk
         prepend with a file header
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')

      file_header = '''# -----------------------------------------------------------------------------
# MAC address file
#  * MAC addresses must have the format hh:hh:hh:hh:hh:hh
#  * MAC addresses must start in col 1, one MAC per line
#  * line comments are allowed (starting with a # in col 1)
#  * inline comments (after the MAC, separated with a #) are allowed as well
#  * all comments will be removed during processing
# -----------------------------------------------------------------------------
'''
      with open(self.macfile, 'w') as f:
         f.write(file_header)
         for mac_address, comment in self.mac_address_list_extended.items():
            f.write(f'{mac_address}   # {comment}\n')
   
   def add_mac (self, mac_address, comment):
      ''' add a MAC to both the simple list and the extended dict and update file '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      if mac_address not in self.mac_address_list:
         self.mac_address_list.append(mac_address)
      self.mac_address_list_extended[mac_address] = comment
      self.write_macfile()
   
   def remove_mac (self, mac_address):
      ''' remove a MAC from both the simple list and the extended dict and update file '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      if mac_address in self.mac_address_list:
         self.mac_address_list.remove(mac_address)
      if mac_address in self.mac_address_list_extended.keys():
         del self.mac_address_list_extended[mac_address]
      self.write_macfile()
   
   def __init__ (self, macfile=None):
      ''' NOTE: no MAC address validation done, only file processing '''
      logger = logging.getLogger()
      logger.debug(f'{sys._getframe().f_code.co_name}/{self.__class__.__name__} starts...')
      
      self.macfile = macfile
      self.mac_address_list = []
      self.mac_address_list_extended = {}
      self._process_macfile()




class Manage_MACFilter(object):
   '''
      the class to manage the CloudKey MAC Filter
      it manages (orchestrates) the methods of the classes above
   '''
   
   def __init__ (self, macfile, configfile, wifi_name):
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
      # if no WiFi name was given as arg, take the default from our config
      if self.wifi_name is None:
         self.wifi_name = self.config.cloudkey_default_wifi_name
         logger.debug(
            f'no wifi name given on command line -- falling back to config default "{self.config.cloudkey_default_wifi_name}"...')
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
      # get the id of the WiFi name/SSID we apply the changes to
      self.wifi_id = self.cloudkey_connect.get_wifi_id_by_name(self.wifi_name)
   
   def get_macs (self):
      '''
         :return: the list of current MAC addresses
      '''
      return self.cloudkey_connect.get_current_mac_filter_list(self.wifi_id)
   
   #
   def add_mac_to_mac_filter (self, mac_address, comment):
      '''
         add a MAC to a MAC filter
         add the MAC as well to the contents of the MAC address backup file
      
         :param mac_address: the MAC address to add
         :param comment: a comment for the MAC (usually the owner name)
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # add the new MAC to both the CloudKey and the backup MAC address file
      self.cloudkey_connect.add_mac_to_mac_filter(self.wifi_id, mac_address)
      self.mac_object.add_mac(mac_address, comment)
   
   #
   def remove_mac_from_mac_filter (self, mac_address):
      '''
         remove a MAC from a MAC filter
         remove the MAC as well from the contents of the MAC address backup file

         :param mac_address: the MAC address to add
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # add the new MAC to both the CloudKey and the backup MAC address file
      self.cloudkey_connect.remove_mac_from_mac_filter(self.wifi_id, mac_address)
      self.mac_object.remove_mac(mac_address)
   
   #
   def set_wifi_mac_filter_from_file (self):
      '''
         set the WiFi MAC address filter to the contents of a file
         any existing MAC filter content is overwritten
      '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      # ...and finally apply the new MAC address list
      self.cloudkey_connect.set_wifi_mac_filter_list(self.wifi_id, self.mac_object.mac_address_list)
      logger.info(
         f'Successfully updated MAC filter for WiFi {self.wifi_name}: Applied {len(self.mac_object.mac_address_list)} MAC addresses.')




if __name__ == "__main__":
   '''
      the EFG Wifi Automation CLI
   '''
   logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()
   
   # process arguments
   parser = argparse.ArgumentParser(description='EFG WiFi automation: manage Unifi Cloud Key mac address filter')
   parser.add_argument("command",
                       choices=('show_macs', 'set_mac_filter'),
                       help="the command to execute",
                       )
   parser.add_argument("--wifi_name",
                       help="the Cloud Key WiFi name (SSID) to work on (optional -- if not given, the config default is used)",
                       default=None,
                       )
   parser.add_argument("--macfile",
                       help="the name of the file with mac addresses (not required for the 'show_macs' command)",
                       )
   parser.add_argument("--configfile",
                       help="our configfile",
                       default='efg_automation.ini'
                       )
   args = parser.parse_args(sys.argv[1:])
   
   if args.command == 'show_macs':
      macmanageobj = Manage_MACFilter(
         None,
         args.configfile,
         args.wifi_name
      )
      print(f'\n\nMAC addresses for WiFi WLAN with SSID {macmanageobj.wifi_name}:')
      print('===========================================================')
      for mac in macmanageobj.get_macs():
         print(f'   {mac}')
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