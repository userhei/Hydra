#  coding: utf-8
import paramiko
import time
import telnetlib


class ConnSSH(object):
    def __init__(self, host, port, username, password, timeout):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._username = username
        self._password = password
        self.SSHConnection = None
        self._connect()

    def _connect(self):
        try:
            objSSHClient = paramiko.SSHClient()
            objSSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            objSSHClient.connect(self._host, port=self._port,
                                 username=self._username,
                                 password=self._password,
                                 timeout=self._timeout)
            # time.sleep(1)
            # print('success')
            # objSSHClient.exec_command("\x003")
            self.SSHConnection = objSSHClient
        except Exception as e:
            print(e)

    def excute_command(self, command):
        stdin, stdout, stderr = self.SSHConnection.exec_command(command)
        data = stdout.read()
        if len(data) > 0:
            return data

        err = stderr.read()
        if len(err) > 0:
            print(err.strip())
            return err
        if data == b'':
            return True

    def close(self):
        self.SSHConnection.close()


class ConnTelnet(object):
    def __init__(self, host, port, username, password, timeout):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self.telnet = telnetlib.Telnet()
        self._connect()

    def _connect(self):
        try:
            self.telnet.open(self._host, self._port)
        except:
            print('%sconnect fail' % self._host)
            return False

        self.telnet.read_until(b'Username:', timeout=1)
        self.telnet.write(b'\n')
        self.telnet.write(self._username.encode() + b'\n')

        self.telnet.read_until(b'Password:', timeout=1)
        self.telnet.write(self._password.encode() + b'\n')

        rely = self.telnet.read_very_eager().decode()
        if 'Login invalid' not in rely:
            print('%slogin success' % self._host)
            return True
        else:
            print('%slogin fail' % self._host)
            return False

    # 定义exctCMD函数,用于执行命令
    def excute_command(self, cmd):
        self.telnet.write(cmd.encode().strip() + b'\r')
        time.sleep(2)
        rely = self.telnet.read_very_eager().decode()
        print(rely, end='')

    def close(self):
        self.telnet.close()


if __name__ == '__main__':
    pass
# telnet
    # host='10.203.1.231'
    # Port='23'
    # username='root'
    # password='Feixi@123'
    # timeout=10
    # test_TN=telnetConn(host, Port,username, password, timeout)
    # test_TN._connect()
    # test_TN.exctCMD('lun show')
    # test_TN.close()
# ssh
    # host='10.203.1.200'
    # port='22'
    # username='root'
    # password='password'
    # timeout=10
    # ssh=SSHConn(host, port, username, password, timeout)
    # ssh._connect()
    # strout=ssh.exctCMD('df')
    # print(re.findall('1024',strout))
    # ssh.close()
