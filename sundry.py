
#  coding: utf-8
import sys
import re
import time
import os
import getpass
import traceback
import socket

def pe(print_str):
    'print and exit'
    print(print_str)
    sys.exit()

class GetDiskPath(object):
    def __init__(self, lun_id, re_string, lsscsi_result, str_target,logger):
        self.logger = logger
        self.id = str(lun_id)
        self.re_string = re_string
        self.target = str_target
        self.lsscsi_result = lsscsi_result.decode('utf-8')

    def find_device(self):
        '''
        Use re to get the blk_dev_name through lun_id
        '''
        self.logger.write_to_log('GetDiskPath','host','find_device',self.logger.host)
        re_find_path_via_id = re.compile(self.re_string)
        self.logger.write_to_log('GetDiskPath','regular_before','find_device',self.lsscsi_result)
        re_result = re_find_path_via_id.findall(self.lsscsi_result)
        self.logger.write_to_log('GetDiskPath', 'regular_after', 'find_device', re_result)
        if re_result:
            dict_stor = dict(re_result)
            if self.id in dict_stor.keys():
                blk_dev_name = dict_stor[self.id]
                self.logger.write_to_log('GetDiskPath','return','find_device',blk_dev_name)
                return blk_dev_name

    def explore_disk(self):
        '''
            Scan and get the device path from VersaPLX or Host
        '''

        if self.lsscsi_result and self.lsscsi_result is not True:
            dev_path = self.find_device()
            if dev_path:
                self.logger.write_to_log('GetDiskPath','return','explore_disk',dev_path)
                return dev_path
            else:
                self.logger.write_to_log('GetDiskPath', 'print', 'explore_disk', (f'Did not find the new LUN from {self.target}'))
                pe(f'Did not find the new LUN from {self.target}')
        else:
            self.logger.write_to_log('GetDiskPath', 'print', 'explore_disk',
                                     (f'Command "lsscsi" failed on {self.target}'))

            pe(f'Command "lsscsi" failed on {self.target}')

        
def record_exception(func):
    """
    Decorator
    Get exception, throw the exception after recording
    :param func:Command binding function
    """
    def wrapper(self,*args):
        try:
            return func(self,*args)
        except Exception as e:
            self.logger.write_to_log('result_to_show', 'ERR', '', str(traceback.format_exc()))
            raise e
    return wrapper


def get_transaction_id():
    return int(time.time())

def get_username():
    return getpass.getuser()

def get_hostname():
    return socket.gethostname()

# Get the path of the program
def get_path():
    return os.getcwd()