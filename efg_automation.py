import argparse
import logging
import sys




class EFGAutomation(object):
   '''
   
   '''




if __name__ == "__main__":
   '''
      the EFG Automation CLI
   '''
   logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(name)s.%(lineno)s[%(levelname)s]: %(message)s')
   logger = logging.getLogger()
   
   # process arguments
   parser = argparse.ArgumentParser(description='EFG WiFi automation: update Unifi Cloud Key mac address filter')
   parser.add_argument("--configfile",
                       help="our configfile",
                       default='efg_automation.ini'
                       )
   args = parser.parse_args(sys.argv[1:])
   
   # do main processing
   try:
      a = EFGAutomation()
   # in case of an exception: raise an alert. Here we could as well send a mail or whatever alerting we prefer...
   except Exception as e:
      logger.critical(f'Caught exception {e} in call process_wifi_mac_filter_update!')
   else:
      logger.info(f'MAC address file {args.macfile} processed successfully.')
