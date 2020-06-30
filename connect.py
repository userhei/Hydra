#  coding: utf-8
import paramiko
import time
import telnetlib
import sys
import sundry as s
import pprint
import traceback


class ConnSSH(object):
    '''
    ssh connect to VersaPLX
    '''

    def __init__(self, host, port, username, password, timeout,logger):
        self.logger = logger
        self.logger.d1 = host
        self._host = host
        self._port = port
        self._timeout = timeout
        self._username = username
        self._password = password
        self.SSHConnection = None
        self._connect()
        print('init.......')


    def _connect(self):
        self.logger.write_to_log('INFO','info','','start to connect VersaPLX via SSH')
        try:
            objSSHClient = paramiko.SSHClient()
            objSSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.logger.write_to_log('DATA','input','ssh_connect',[self._host,self._port,self._username,self._password,self._timeout])  #怎么记
            # log : SSH_connect [host,port,username,password,timeout]
            objSSHClient.connect(self._host, port=self._port,
                                 username=self._username,
                                 password=self._password,
                                 timeout=self._timeout)
            # 如何验证SSH连接成功
            # log : SSH_connect_result [T/F]
            self.logger.write_to_log('DATA','output','ssh_connect','SSH SUCCESS')
            self.SSHConnection = objSSHClient
        except Exception as e:
            self.logger.write_to_log('INFO', 'error', '', (str(traceback.format_exc())))
            s.pwe(self.logger,f'Connect to {self._host} failed with error: {e}')

    def execute_command(self, command):
        '1, o and data; 2, x and err; 3, 0 and no_data'

        self.logger.write_to_log('DATA','input','cmd',command)
        stdin, stdout, stderr = self.SSHConnection.exec_command(command)
        data = stdout.read()
        if len(data) > 0:
            self.logger.write_to_log('DATA','output',command,(1,data))
            return {'sts':1, 'rst':data}

        err = stderr.read()
        if len(err) > 0:
            print(err.strip())
            self.logger.write_to_log('INFO','info','',(err.strip()))
            self.logger.write_to_log('DATA','output',command,(2, err))
            return {'sts':0, 'rst':err}

        if data == b'':
            self.logger.write_to_log('DATA','output',command,(3, ''))
            return {'sts':1, 'rst':data}

    def close(self):
        self.SSHConnection.close()
        self.logger.write_to_log('INFO', 'info', '', 'Close SSH connection')


class ConnTelnet(object):
    '''
    telnet connect to NetApp 
    '''

    def __init__(self, host, port, username, password, timeout,logger):
        self.logger = logger
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self.telnet = telnetlib.Telnet()
        self._connect()

    def _connect(self):
        try:
            self.logger.write_to_log('INFO','info','','start to connect VersaPLX via telnet')
            # log : telnet_open
            self.telnet.open(self._host, self._port)
            self.logger.write_to_log('DATA', 'input', 'telnet_open', (self._host, self._port))
            # log: telnet_open_result 这个有没有结果的
            # log : username
            date_read1 =  self.telnet.read_until(b'Username:', timeout=1)
            self.logger.write_to_log('DATA','output','telnet_read_until',date_read1)
            self.logger.write_to_log('DATA','input','telnet_write',self._username.encode() + b'\n')
            self.telnet.write(self._username.encode() + b'\n')
            # 写入之后的结果怎么判断，

            date_read2 = self.telnet.read_until(b'Password:', timeout=1)
            self.logger.write_to_log('DATA','output','telnet_read_until',date_read2)
            self.logger.write_to_log('DATA','input','telnet_write',self._password.encode() + b'\n')
            self.telnet.write(self._password.encode() + b'\n')

        except Exception as e:
            self.logger.write_to_log('INFO', 'error', '', (str(traceback.format_exc())))
            s.pwe(self.logger,f'Connect to {self._host} failed with error: {e}')

    # 定义exctCMD函数,用于执行命令
    def execute_command(self, cmd):
        # log: NetApp_ex_cmd
        self.logger.write_to_log('DATA','input','cmd',cmd.encode().strip() + b'\r')
        self.telnet.write(cmd.encode().strip() + b'\r')
        # 命令的结果的记录？
        # self.logger.write_to_log('Telnet','telnet_ex_cmd','','time_sleep:0.25')
        time.sleep(0.25)
        rely = self.telnet.read_very_eager().decode()# ?
        # self.logger.write_to_log('Telnet',)

    def close(self):
        self.telnet.close()
        self.logger.write_to_log('INFO', 'info', '', 'Close Telnet connection.')

if __name__ == '__main__':
# telnet
    host='10.203.1.231'
    port='22'
    username='root'
    password='Feixi@123'
    timeout=5
    ssh=ConnSSH(host, port, username, password, timeout)
    strout=ssh.execute_command('?')
    w = strout.decode('utf-8')
    print(type(w))
    print(w.split('\n'))
    pprint.pprint(w)
    time.sleep(2)
    strout=ssh.execute_command('lun show -m')
    pprint.pprint(strout)


    # telnet
    # host='10.203.1.231'
    # Port='23'
    # username='root'
    # password='Feixi@123'
    # timeout=10

    pass
