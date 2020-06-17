# coding:utf-8

import connect as c
import re
import sys
import time

host = '10.203.1.200'
port = '22'
user = 'root'
password = 'password'
timeout = 3

mount_point = '/mnt'


class HostTest(object):
    def __init__(self, unique_id):
        self.ssh = c.ConnSSH(host, port, user, password, timeout)
        self.id = unique_id

    def iscsi_login(self):
        login_result = self.ssh.excute_command(
            'iscsiadm -m discovery -t st -p 10.203.1.199 -l')
        login_result = login_result.decode('utf-8')
        if login_result:
            re_login = re.compile(
                'Login to.*portal: (10.203.1.199).*successful')
            re_result = re_login.findall(login_result)
            if re_result:
                print('iscsi login succeed')
                return True
            else:
                print('iscsi login failed')
                sys.exit()

    def find_session(self):
        f_cmd = 'iscsiadm -m session'
        f_result = self.ssh.excute_command(f_cmd)
        f_result = f_result.decode('utf-8')
        if f_result:
            re_fsession = re.compile('tcp:.*(10.203.1.199):.*')
            re_result = re_fsession.findall(f_result)
            if re_result:
                return True
            else:
                self.iscsi_login()

    def _find_device(self, command_result):
        # re_find_id_dev = re.compile(
        #     r'\:(\d*)\].*NETAPP[ 0-9a-zA-Z.]*(/dev/sd[a-z]{1,3})')
        re_find_id_dev = re.compile(
            r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})')
        re_result = re_find_id_dev.findall(command_result)
        # print(re_result)

        # [('0', '/dev/sdb'), ('1', '/dev/sdc')]
        if re_result:
            dic_result = dict(re_result)
            if str(self.id) in dic_result.keys():
                dev_path = dic_result[str(self.id)]
                return dev_path

    def explore_disk(self):
        if self.ssh.excute_command('/usr/bin/rescan-scsi-bus.sh'):
            lsscsi_result = self.ssh.excute_command('lsscsi')
            if lsscsi_result and lsscsi_result is not True:
                dev_path = self._find_device(lsscsi_result.decode('utf-8'))
                # print(dev_path)
                if dev_path:
                    return dev_path
                else:
                    print("did not find the new LUN from VersaPLX")
                    sys.exit()
            else:
                print("command 'lsscsi' failed")
                sys.exit()
        else:
            print('scan failed')
            sys.exit()

    def find_explore(self):
        if self.find_session:
            dev_path = self.explore_disk()
            return dev_path

    def _judge_format(self, arg_bytes):
        re_done = re.compile(r'done')
        string = arg_bytes.decode('utf-8')
        if len(re_done.findall(string)) == 4:
            return True

    def format_mount(self):
        dev_name = self.find_explore()
        format_cmd = f'mkfs.ext4 {dev_name} -F'
        cmd_result = self.ssh.excute_command(format_cmd)
        if self._judge_format(cmd_result):
            mount_cmd = f'mount {dev_name} {mount_point}'
            if self.ssh.excute_command(mount_cmd) == True:
                return True
            else:
                print(f"mount {dev_name} to {mount_point} failed")
                sys.exit()
        else:
            print("format disk %s failed" % dev_name)
            sys.exit()

    def _get_dd_perf(self, arg_str):
        re_performance = re.compile(r'.*s, ([1-9.]* [A-Z]B/s)')
        string = arg_str.decode('utf-8')
        re_result = re_performance.findall(string)
        perf = re_result
        return perf[0]

    def write_test(self):
        test_cmd = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        if test_result:
            return self._get_dd_perf(test_result)

    def read_test(self):
        test_cmd = f'dd if={mount_point}/t.dat of=/dev/zero bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        if test_result:
            return self._get_dd_perf(test_result)


if __name__ == "__main__":
    test = HostTest(21)
    command_result = '''[2:0:0:0]    cd/dvd  NECVMWar VMware SATA CD00 1.00  /dev/sr0
    [32:0:0:0]   disk    VMware   Virtual disk     2.0   /dev/sda 
    [33:0:0:15]  disk    LIO-ORG  res_lun_15       4.0   /dev/sdb 
    [33:0:0:21]  disk    LIO-ORG  res_luntest_21   4.0   /dev/sdc '''
    print(command_result)
    test._find_device(str(command_result))
