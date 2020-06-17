#  coding: utf-8
import connect
import time

host = '10.203.1.231'
port = 23
username = 'root'
password = 'Feixi@123'
timeout = 3


class Storage:
    def __init__(self, unique_id, unique_name):
        self.telnet_conn = connect.ConnTelnet(
            host, port, username, password, timeout)
        self.lun_name = f'{unique_name}_{unique_id}'
        self.lun_id = unique_id

    def lun_create(self):
        lc_cmd = f'lun create -s 10m -t linux /vol/esxi/{self.lun_name}'
        self.telnet_conn.excute_command(lc_cmd)

    def lun_map(self):
        lm_cmd = f'lun map /vol/esxi/{self.lun_name} hydra {self.lun_id}'
        self.telnet_conn.excute_command(lm_cmd)

    def lun_create_verify(self):
        pass

    def lun_map_verify(self):
        pass


if __name__ == '__main__':
    pass
    # test_stor = Storage('13', 'lun')
    # test_stor.lun_create()
    # test_stor.lun_map()
    # test_stor.telnet_conn.close()
