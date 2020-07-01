#  coding: utf-8
import connect
import time

global ID
global STRING

host = '10.203.1.231'
port = 23
username = 'root'
password = 'Feixi@123'
timeout = 3


class Storage:
    '''
    Create LUN and map to VersaPLX
    '''

    def __init__(self,logger):
        self.logger = logger
        self.telnet_conn = connect.ConnTelnet(
            host, port, username, password, timeout,logger)
        # print('Connect to storage NetApp')
        self.lun_name = f'{STRING}_{ID}'


    def lun_create(self):
        '''
        Create LUN with 10M bytes in size
        '''
        # self.logger.write_to_log('INFO','info','',f'start to create lun {self.lun_name}')
        lc_cmd = f'lun create -s 10m -t linux /vol/esxi/{self.lun_name}'
        self.telnet_conn.execute_command(lc_cmd)
        print('Create LUN successful on NetApp Storage')
        # self.logger.write_to_log('INFO','info','',('Create LUN successful on NetApp Storage'))

    def lun_map(self):
        '''
        Map lun of specified lun_id to initiator group
        '''
        # self.logger.write_to_log('INFO','info','',f'start to map lun {self.lun_name}')
        lm_cmd = f'lun map /vol/esxi/{self.lun_name} hydra {ID}'
        self.telnet_conn.execute_command(lm_cmd)
        print('LUN map successful on NetApp Storage')
        # self.logger.write_to_log('INFO', 'info', '', ('LUN map successful on NetApp Storage'))

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
