# coding:utf-8

import connect as c
import re
import sys
import time

vplx_ip = '10.203.1.199'
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
        login_cmd = f'iscsiadm -m discovery -t st -p {vplx_ip} -l'
        login_result = self.ssh.excute_command(login_cmd)
        if login_result:
            login_result = login_result.decode('utf-8')
            re_login = re.compile(
                f'Login to.*portal: ({vplx_ip}).*successful')
            re_result = re_login.findall(login_result)
            if re_result:
                return True
            else:
                s.pe(f'iscsi login to {vplx_ip} failed')

    def find_session(self):
        session_cmd = 'iscsiadm -m session'
        session_result = self.ssh.excute_command(session_cmd)
        if session_result:
            session_result = session_result.decode('utf-8')
            re_session = re.compile(f'tcp:.*({vplx_ip}):.*')
            re_result = re_session.findall(session_result)
            if re_result:
                return True

    def _find_device(self, command_result):
        re_find_id_dev = re.compile(
            r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})')
        re_result = re_find_id_dev.findall(command_result)

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

    def _judge_format(self, arg_bytes):
        re_done = re.compile(r'done')
        string = arg_bytes.decode('utf-8')
        if len(re_done.findall(string)) == 4:
            return True

    def format_mount(self,dev_name):
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

    def get_test_perf(self):
        write_perf = self.write_test()
        print(f'write speed: {write_perf}')
        time.sleep(0.5)
        read_perf = self.read_test()
        print(f'read speed: {read_perf}')

    def start_test(self):
        if not self.find_session:
            self.iscsi_login()
        dev_name = self.explore_disk()
        mount_status = self.format_mount(dev_name)
        if mount_status:
            self.get_test_perf()
        else:
            s.pe(f'Device {dev_name} mount failed')

if __name__ == "__main__":
    test = HostTest(21)
    command_result = '''[2:0:0:0]    cd/dvd  NECVMWar VMware SATA CD00 1.00  /dev/sr0
    [32:0:0:0]   disk    VMware   Virtual disk     2.0   /dev/sda 
    [33:0:0:15]  disk    LIO-ORG  res_lun_15       4.0   /dev/sdb 
    [33:0:0:21]  disk    LIO-ORG  res_luntest_21   4.0   /dev/sdc '''
    print(command_result)
    test._find_device(str(command_result))
