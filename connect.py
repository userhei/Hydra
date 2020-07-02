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
        self._host = host
        self._port = port
        self._timeout = timeout
        self._username = username
        self._password = password
        self.SSHConnection = None
        self._connect()


    def _connect(self):
        self.logger.write_to_log('INFO','info','start','',f'connect to VersaPLX via SSH.host:{self._host},port:{self._port},username:{self._username},password:{self._password}')
        try:
            objSSHClient = paramiko.SSHClient()
            objSSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            objSSHClient.connect(self._host, port=self._port,
                                 username=self._username,
                                 password=self._password,
                                 timeout=self._timeout)
            self.SSHConnection = objSSHClient
        except Exception as e:
            self.logger.write_to_log('INFO', 'error', 'done', '',(str(traceback.format_exc())))
            s.pwe(self.logger,f'Connect to {self._host} failed with error: {e}',level='warning')

    def excute_command(self, command):
        '1, o and data; 2, x and err; 3, 0 and no_data'
        cmd_id = s.get_cmd_id()
        self.logger.write_to_log('OPRT','cmd','ssh',cmd_id,command)
        stdin, stdout, stderr = self.SSHConnection.exec_command(command)
        data = stdout.read()
        if len(data) > 0:
            self.logger.write_to_log('DATA','output',command,cmd_id,1)
            return (data)

        err = stderr.read()
        if len(err) > 0:
            print(err.strip())
            self.logger.write_to_log('INFO','info','print','',(err.strip()))
            self.logger.write_to_log('DATA','output','cmd',cmd_id,2)
            return (err)

        if data == b'':
            self.logger.write_to_log('DATA','output','cmd',cmd_id,3)
            return True

    def close(self):
        self.SSHConnection.close()
        self.logger.write_to_log('INFO', 'info', 'done','', 'Close SSH connection')


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
            self.logger.write_to_log('INFO','info','start','',f'connect storage via telnet.host:{self._host},port:{self._port},username:{self._username},password:{self._password}')
            self.telnet.open(self._host, self._port)
            self.telnet.read_until(b'Username:', timeout=1)
            self.telnet.write(self._username.encode() + b'\n')
            self.telnet.read_until(b'Password:', timeout=1)
            self.telnet.write(self._password.encode() + b'\n')

        except Exception as e:
            self.logger.write_to_log('INFO', 'error', 'done','', (str(traceback.format_exc())))
            s.pwe(self.logger,f'Connect to {self._host} failed with error: {e}',level='warning')

    # 定义exctCMD函数,用于执行命令
    def excute_command(self, cmd):
        # log: NetApp_ex_cmd
        cmd_id = s.get_cmd_id()
        self.logger.write_to_log('OPRT','cmd','telnet',cmd_id,cmd.encode().strip() + b'\r')
        self.telnet.write(cmd.encode().strip() + b'\r')
        time.sleep(0.25)
        print('cmd',cmd.encode().strip() + b'\r')

    def close(self):
        self.telnet.close()
        self.logger.write_to_log('INFO', 'info', 'done', '','Close Telnet connection.')

if __name__ == '__main__':
# telnet
    host='10.203.1.231'
    port='22'
    username='root'
    password='Feixi@123'
    timeout=5
    ssh=ConnSSH(host, port, username, password, timeout)
    strout=ssh.excute_command('?')
    w = strout.decode('utf-8')
    print(type(w))
    print(w.split('\n'))
    pprint.pprint(w)
    time.sleep(2)
    strout=ssh.excute_command('lun show -m')
    pprint.pprint(strout)


    # telnet
    # host='10.203.1.231'
    # Port='23'
    # username='root'
    # password='Feixi@123'
    # timeout=10

    pass
