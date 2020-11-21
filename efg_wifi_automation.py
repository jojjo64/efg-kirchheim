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
   def _update_wifi_settings (self, wifi_id, params):
      """ general interface to update WiFi settings, params must hold a dict of valid wifi key/value pairs """
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
      """ update the wifi MAC address filter """
      self._validate_mac_filter_list(mac_address_list)
      self._update_wifi_settings(wifi_id, params={'mac_filter_list': mac_address_list})




class EFGFCloudKeyConfig(object):
   '''
      simple class to process our configuration file
      we use the python builtin configparser for processing an INI file with key/value pairs grouped in sections
   '''
   
   def __init__(self, configfile=None):
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
      cloudkey_config = config['CloudKey']
      self.cloudkey_host = cloudkey_config['host']
      self.cloudkey_user = cloudkey_config['user']
      self.cloudkey_password = cloudkey_config['password']




class EFGMACFile(object):
   '''
      simple class to process the MAC address file
   '''
   def _process_macfile(self):
      ''' open file, ignore / remove comments and return a list of MACs '''
      # check if macfile exists, else raise an exception
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      f = Path(self.macfile)
      if not f.is_file():
         raise ValueError(f'macfile "{self.macfile}" not found!')
      
      maclist = []
      
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
            maclist.append(l.split('#')[0].strip())
         
      return maclist
      
   def __init__(self, macfile = None):
      ''' NOTE: no MAC address validation done, only file processing '''
      logger = logging.getLogger()
      logger.debug(sys._getframe().f_code.co_name + ' starts...')
      
      self.macfile = macfile
      self.mac_address_list = self._process_macfile()
      



def process_wifi_mac_filter_update(macfile, wifi_name, configfile):
   '''
      process the MAC address filter update including all preparation tasks
   
      :param macfile: the file with the MAC addresses
      :param wifi_name: the WiFi name / SSID to update
      :param configfile: our configuration file (holding data how to access the Cloud Key)
   '''
   logger = logging.getLogger()
   logger.debug(sys._getframe().f_code.co_name + ' starts...')
   
   # read in our config
   config = EFGFCloudKeyConfig(configfile = configfile)
   # read in the MAC address file
   mac_object = EFGMACFile(macfile=macfile)
   # connect to the Cloud Key
   cloudkey_connect = pyunifi_WiFi_Controller(
      config.cloudkey_host,
      config.cloudkey_user,
      config.cloudkey_password,
      ssl_verify=False
   )
   # get the id of the WiFi name/SSID we apply the changes to
   wifi_id = cloudkey_connect.get_wifi_id_by_name(wifi_name)
   # ...and finally apply the new MAC address list
   cloudkey_connect.set_wifi_mac_filter_list(wifi_id, mac_object.mac_address_list)
   logger.info(f'Successfully updated MAC filter for WiFi {wifi_name}: Applied {len(mac_object.mac_address_list)} MAC addresses.')




if __name__ == "__main__":
   '''
      the EFG Wifi Automation CLI
   '''
   logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()

   # process arguments
   parser = argparse.ArgumentParser(description='EFG WiFi automation: update Unifi Cloud Key mac address filter')
   parser.add_argument("macfile",
                       help="the name of the file with mac addresses",
                      )
   parser.add_argument("wifi_name",
                       help="the Cloud Key WiFi name (SSID) to work on",
                      )
   parser.add_argument("--configfile",
                       help="our configfile",
                       default='efg_automation.ini'
                      )
   args = parser.parse_args(sys.argv[1:])
   
   # do main processing
   try:
      process_wifi_mac_filter_update(
         args.macfile,
         args.wifi_name,
         args.configfile
      )
   # in case of an exception: raise an alert. Here we could as well send a mail or whatever alerting we prefer...
   except Exception as e:
      logger.critical(f'Caught exception {e} in call process_wifi_mac_filter_update!')
   else:
      logger.info(f'MAC address file {args.macfile} processed successfully.')
   
