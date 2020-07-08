#  coding: utf-8
import connect
import time
from logdb import LogDB
import consts
import sundry

global ID
global STRING
global replay
global TID

host = '10.203.1.231'
port = 23
username = 'root'
password = 'Feixi@123'
timeout = 3

# [time],[transaction_id],[display],[type_level1],[type_level2],[d1],[d2],[data]

class Storage:
    '''
    Create LUN and map to VersaPLX
    '''

    def __init__(self,logger):
        if replay == 'no':
            self.logger = logger
            print('Start to configure LUN on NetApp Storage')
            self.logger.write_to_log('T', 'INFO', 'info', 'start', '', 'Start to configure LUN on NetApp Storage')
            self.telnet_conn = connect.ConnTelnet(host, port, username, password, timeout,logger)
            # print('Connect to storage NetApp')
            self.lun_name = f'{STRING}_{ID}'
        elif replay == 'yes':
            print('Start to configure LUN on NetApp Storage')
            self.lun_name = f'{STRING}_{ID}'


    def lun_create(self):
        '''
        Create LUN with 10M bytes in size
        '''
        info_msg = f'create lun, name: {self.lun_name}'
        lc_cmd = f'lun create -s 10m -t linux /vol/esxi/{self.lun_name}'
        if replay == 'no':
            oprt_id = sundry.get_oprt_id()
            print(f'  Start to {info_msg}')
            self.logger.write_to_log('T','INFO','info','start','',f'  Start to {info_msg}')
            self.logger.write_to_log('T', 'OPRT', 'cmd', 'telnet', oprt_id, lc_cmd)
            self.telnet_conn.execute_command(lc_cmd)
            print(f'  Create LUN {self.lun_name} successful')
            self.logger.write_to_log('T','INFO','info','finish','',f'  Create LUN {self.lun_name} successful')
        elif replay == 'yes':
            db = LogDB()
            consts.set_value('ID',db.get_id(TID,f'  Start to {info_msg}'))
            # print(f'  Create LUN {self.lun_name} successful')
            id = consts.get_value('ID')[0]
            print(id)
            id_max = db.get_id(TID,f'  Create LUN {self.lun_name} successful')[0]
            for i in range(id,id_max+1):
                info = db.get_data_via_id(i)
                if info:print(info[0])


    def lun_map(self):
        '''
        Map lun of specified lun_id to initiator group
        '''
        info_msg = f'map LUN, LUN name: {self.lun_name}, LUN ID: {ID}'
        lm_cmd = f'lun map /vol/esxi/{self.lun_name} hydra {ID}'

        if replay == 'no':
            print(f'  Start to {info_msg}')
            self.logger.write_to_log('T','INFO','info','start','',f'  Start to {info_msg}')
            self.telnet_conn.execute_command(lm_cmd)
            print(f'  Finish with {info_msg}')
            self.logger.write_to_log('T','INFO','info','finish','',f'  Finish with {info_msg}')
        elif replay == 'yes':
            db = LogDB()
            consts.set_value('ID', db.get_id(TID, f'  Start to {info_msg}'))
            id = consts.get_value('ID')[0]
            print(id)
            id_max = db.get_id(TID, f'  Finish with {info_msg}')[0]
            for i in range(id,id_max+1):
                info = db.get_data_via_id(i)
                if info:print(info[0])
            import sys
            sys.exit()

    def lun_create_verify(self):
        pass

    def lun_map_verify(self):
        pass


if __name__ == '__main__':
    test_stor = Storage('18', 'luntest')
    test_stor.lun_create()
    test_stor.lun_map()
    # test_stor.telnet_conn.close()
    pass
