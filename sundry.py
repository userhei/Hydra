
#  coding: utf-8
import sys
import re

def pe(print_str):
    'print and exit'
    print(print_str)
    sys.exit()

def find_device(re_find_id_dev, lun_id, ls_result):
    '''
    Use re to get the blk_dev_name through lun_id
    '''
    re_vplx_id_path = re.compile(re_find_id_dev)
    stor_result = re_vplx_id_path.findall(ls_result)
    if stor_result:
        dict_stor = dict(stor_result)
        if str(lun_id) in dict_stor.keys():
            blk_dev_name = dict_stor[str(lun_id)]
            return blk_dev_name

