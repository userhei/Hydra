import connect
import time


class Storage:
    def __init__(self, lun_name):
        host = '10.203.1.231'
        Port = 23
        username = 'root'
        password = 'Feixi@123'
        timeout = 10
        self.telnet_conn = connect.TNConn(
            host, Port, username, password, timeout)
        self.telnet_conn._connect()
        self.lun_name = lun_name

    def lun_create(self):
        lc_cmd = r'lun create -s 10m -t linux /vol/esxi/%s' % self.lun_name
        self.telnet_conn.exctCMD(lc_cmd)

    def lun_map(self, lun_id):
        lm_cmd = rf'lun map /vol/esxi/{self.lun_name} hydra {lun_id}'
        self.telnet_conn.exctCMD(lm_cmd)

    def lun_create_verify(self):
        pass

    def lun_map_verify(self):
        pass
