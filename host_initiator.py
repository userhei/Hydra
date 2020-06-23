# coding:utf-8

import connect as c
import re
import sys
import time
import sundry as s

vplx_ip = '10.203.1.199'
host = '10.203.1.200'
port = '22'
user = 'root'
password = 'password'
timeout = 3

mount_point = '/mnt'


class HostTest(object):
    '''
    Format, write, and read iSCSI LUN
    '''

    def __init__(self, unique_id,logger):
        self.logger = logger
        self.ssh = c.ConnSSH(host, port, user, password, timeout,logger)
        self.id = unique_id
        self.logger.host = host # 给logger对象的host属性附上这个模块的host

    def iscsi_login(self):
        '''
        Discover iSCSI and login to session
        '''
        login_cmd = f'iscsiadm -m discovery -t st -p {vplx_ip} -l'
        login_result = self.ssh.excute_command(login_cmd)
        if login_result:
            login_result = login_result.decode('utf-8')
            self.logger.write_to_log('HostTest','regular_before','iscsi_login',login_result)
            re_login = re.compile(
                f'Login to.*portal: ({vplx_ip}).*successful')
            re_result = re_login.findall(login_result)
            self.logger.write_to_log('HostTest','regular_after','iscsi_login',re_result)

            if re_result:
                self.logger.write_to_log('HostTest','re_result_to_return','iscsi_login',True)
                return True
            else:
                self.logger.write_to_log('HostTest','print','iscsi_login',(f'iscsi login to {vplx_ip} failed'))
                s.pe(f'iscsi login to {vplx_ip} failed')

    def find_session(self):
        '''
        Execute the command and check up the status of session
        '''
        session_cmd = 'iscsiadm -m session'
        session_result = self.ssh.excute_command(session_cmd)
        if session_result:
            session_result = session_result.decode('utf-8')
            self.logger.write_to_log('HostTest','regular_before','find_session',session_result)
            re_session = re.compile(f'tcp:.*({vplx_ip}):.*')
            re_result = re_session.findall(session_result)
            self.logger.write_to_log('HostTest', 'regular_after', 'find_session', re_result)
            if re_result:
                self.logger.write_to_log('HostTest','re_result_to_return','find_session')
                return True

    # def _find_device(self, command_result):
    #     '''
    #     Use re to find device_path
    #     '''
    #     re_find_id_dev = re.compile(
    #         r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})')
    #     re_result = re_find_id_dev.findall(command_result)

    #     # [('0', '/dev/sdb'), ('1', '/dev/sdc')]
    #     if re_result:
    #         dic_result = dict(re_result)
    #         if str(self.id) in dic_result.keys():
    #             dev_path = dic_result[str(self.id)]
    #             return dev_path

    def explore_disk(self):
        '''
         Scan and get the device path from VersaPLX
        '''
        lsscsi_result = None
        if self.ssh.excute_command('/usr/bin/rescan-scsi-bus.sh'):
            time.sleep(0.5)
            lsscsi_result = self.ssh.excute_command('lsscsi') # 什么情况下是True
        else:
            self.logger.write_to_log('HostTest','print','explore_disk',(f'Scan new LUN failed on VersaPLX'))
            s.pe(f'Scan new LUN failed on VersaPLX')
        re_find_id_dev = r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
        result = s.GetDiskPath(self.id, re_find_id_dev, lsscsi_result, 'VersaPLX',self.logger).explore_disk()
        self.logger.write_to_log('HostTest','return','explore_disk',result)
        return result

    def _judge_format(self, arg_bytes):
        '''
        Determine the format status
        '''
        re_done = re.compile(r'done')
        string = arg_bytes.decode('utf-8')
        self.logger.write_to_log.write('HostTest','regular_before','_judge_format',string)
        self.logger.write_to_log.write('HostTest','regular_after','_judge_format',re_done.findall(string))
        if len(re_done.findall(string)) == 4:
            self.logger.write_to_log('HostTest','return','_judge_format',True)
            return True
        # Vince
        else:
            self.logger.write_to_log('HostTest','return','_judge_format',None)

    def format_mount(self, dev_name):
        '''
        Format disk and mount disk
        '''
        format_cmd = f'mkfs.ext4 {dev_name} -F'
        cmd_result = self.ssh.excute_command(format_cmd)
        if self._judge_format(cmd_result):
            mount_cmd = f'mount {dev_name} {mount_point}'
            if self.ssh.excute_command(mount_cmd) == True:
                self.logger.write_to_log('HostTest', 'return', 'format_mount', True)
                return True
            else:
                self.logger.write_to_log('HostTest', 'print', 'format_mount', s.pe(f"mount {dev_name} to {mount_point} failed"))
                s.pe(f"mount {dev_name} to {mount_point} failed")

        else:
            self.logger.write_to_log('HostTest','print','format_mount',("format disk %s failed" % dev_name))
            s.pe("format disk %s failed" % dev_name)

    def _get_dd_perf(self, arg_str):
        '''
        Use re to get the speed of test
        '''
        re_performance = re.compile(r'.*s, ([0-9.]* [A-Z]B/s)')
        string = arg_str.decode('utf-8')
        self.logger.write_to_log('HostTest','regular_before','_get_dd_perf',string)
        re_result = re_performance.findall(string)
        self.logger.write_to_log('HostTest', 'regular_after', '_get_dd_perf', re_result)
        perf = re_result
        if perf:
            self.logger.write_to_log('HostTest', 'return', '_get_dd_perf', perf[0])
            return perf[0]
        else:
            self.logger.write_to_log('HostTest', 'print', '_get_dd_perf', ('Can not get test result'))
            s.pe('Can not get test result')

    def write_test(self):
        '''
        Execute command for write test
        '''
        test_cmd = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        time.sleep(0.5)
        if test_result:
            result = self._get_dd_perf(test_result)
            self.logger.write_to_log('HostTest', 'return', 'write_test',result)
            return result

    def read_test(self):
        '''
        Execute command for read test
        '''
        test_cmd = f'dd if={mount_point}/t.dat of=/dev/zero bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        if test_result:
            result = self._get_dd_perf(test_result)
            self.logger.write_to_log('HostTest', 'return', 'read_test',result)
            return result

    def get_test_perf(self):
        '''
        Calling method to read&write test
        '''
        write_perf = self.write_test()
        print(f'write speed: {write_perf}')
        self.logger.write_to_log('HostTest', 'print', 'get_test_perf', (f'write speed: {write_perf}'))
        time.sleep(0.5)
        read_perf = self.read_test()
        print(f'read speed: {read_perf}')
        self.logger.write_to_log('HostTest', 'print', 'get_test_perf', (f'read speed: {read_perf}'))

    def start_test(self):
        if not self.find_session:
            self.iscsi_login()
        dev_name = self.explore_disk()
        mount_status = self.format_mount(dev_name)
        if mount_status:
            self.get_test_perf()
        else:
            self.logger.write_to_log('HostTest', 'print', 'start_test', (f'Device {dev_name} mount failed'))
            s.pe(f'Device {dev_name} mount failed')


if __name__ == "__main__":
    test = HostTest(21)
    command_result = '''[2:0:0:0]    cd/dvd  NECVMWar VMware SATA CD00 1.00  /dev/sr0
    [32:0:0:0]   disk    VMware   Virtual disk     2.0   /dev/sda 
    [33:0:0:15]  disk    LIO-ORG  res_lun_15       4.0   /dev/sdb 
    [33:0:0:21]  disk    LIO-ORG  res_luntest_21   4.0   /dev/sdc '''
    print(command_result)
