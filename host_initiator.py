# coding:utf-8

import connect as c
import re
import sys
import time
import sundry as s

global SSH
global ID

vplx_ip = '10.203.1.199'
host = '10.203.1.200'
port = '22'
user = 'root'
password = 'password'
timeout = 3

mount_point = '/mnt'

def init_ssh(logger):
    global SSH
    if not SSH:
        SSH = connect.ConnSSH(host, port, user, password, timeout, logger)
    else:
        pass

class HostTest(object):
    '''
    Format, write, and read iSCSI LUN
    '''

    def __init__(self, logger):
        
        self.logger = logger
        # self.logger.host = host # 给logger对象的host属性附上这个模块的host
        init_ssh(self.logger)

    def iscsi_login(self):
        '''
        Discover iSCSI and login to session
        '''
        # self.logger.write_to_log('INFO','info','',f'start to discover iscsi and login to {vplx_ip}')
        login_cmd = f'iscsiadm -m discovery -t st -p {vplx_ip} -l'
        login_result = SSH.execute_command(login_cmd)

        if login_result:
            login_result = login_result.decode('utf-8')
            re_login = re.compile(
                f'Login to.*portal: ({vplx_ip}).*successful')
            re_result = re_login.findall(login_result)
            # self.logger.write_to_log('DATA','output','re_result',re_result)

            if re_result:
                return True
            else:
                s.pwe(self.logger,f'iscsi login to {vplx_ip} failed')

    def find_session(self):
        '''
        Execute the command and check up the status of session
        '''
        # self.logger.write_to_log('INFO', 'info', '', 'start to execute the command and check up the status of session')
        session_cmd = 'iscsiadm -m session'
        session_result = SSH.execute_command(session_cmd)
        if session_result:
            session_result = session_result.decode('utf-8')
            re_session = re.compile(f'tcp:.*({vplx_ip}):.*')
            re_result = re_session.findall(session_result)
            # self.logger.write_to_log('DATA', 'output', 're_result', re_result)
            if re_result:
                # self.logger.write_to_log('HostTest','return','find_session',True)
                return True
        self.logger.write_to_log('INFO','info','','find_session end')

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
    #         if str(ID) in dic_result.keys():
    #             dev_path = dic_result[str(ID)]
    #             return dev_path

    def explore_disk(self):
        '''
         Scan and get the device path from VersaPLX
        '''
        self.logger.write_to_log('INFO','info','','start to explore_disk')
        lsscsi_result = None
        if SSH.execute_command('/usr/bin/rescan-scsi-bus.sh'):
            time.sleep(0.5)
            lsscsi_result = SSH.execute_command('lsscsi') # 什么情况下是True
        else:
            s.pwe(self.logger,f'Scan new LUN failed on VersaPLX')
        re_find_id_dev = r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
        result = s.get_disk_dev(ID, re_find_id_dev, result_lsscsi, 'VersaPLX',self.logger)
        self.logger.write_to_log('INFO','info',result,'explore_disk end')
        return result

    def _judge_format(self, arg_bytes):
        '''
        Determine the format status
        '''
        self.logger.write_to_log('INFO','info','','start to determine the format status')
        re_done = re.compile(r'done')
        string = arg_bytes.decode('utf-8')
        # self.logger.write_to_log('HostTest','regular_before','_judge_format',string)
        self.logger.write_to_log('DATA','output','re_result',re_done.findall(string))
        if len(re_done.findall(string)) == 4:
            return True
        self.logger.write_to_log('INFO','info','','_judge_format end')

    def format_mount(self, dev_name):
        '''
        Format disk and mount disk
        '''
        self.logger.write_to_log('INFO','info','',f'start to format disk {dev_name} and mount disk {dev_name}')
        format_cmd = f'mkfs.ext4 {dev_name} -F'
        cmd_result = SSH.execute_command(format_cmd)
        if self._judge_format(cmd_result):
            mount_cmd = f'mount {dev_name} {mount_point}'
            if SSH.execute_command(mount_cmd) == True:
                #self.logger.write_to_log('HostTest', 'return', 'format_mount', True)
                return True
            else:
                s.pwe(self.logger,f"mount {dev_name} to {mount_point} failed")

        else:
            s.pwe(self.logger,"format disk %s failed" % dev_name)

    def _get_dd_perf(self, arg_str):
        '''
        Use re to get the speed of test
        '''
        self.logger.write_to_log('INFO','info','','start to get the speed of test')
        re_performance = re.compile(r'.*s, ([0-9.]* [A-Z]B/s)')
        string = arg_str.decode('utf-8')
        re_result = re_performance.findall(string)
        self.logger.write_to_log('DATA', 'output', 're_result', re_result)
        perf = re_result
        if perf:
            # self.logger.write_to_log('DATA', 'output', 'return', perf[0])
            return perf[0]
        else:
            s.pwe(self.logger,'Can not get test result')

    def write_test(self):
        '''
        Execute command for write test
        '''
        self.logger.write_to_log('INFO','info','','start to execute command for write test')
        test_cmd = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        test_result = SSH.execute_command(test_cmd)
        time.sleep(0.5)
        if test_result:
            result = self._get_dd_perf(test_result)
            return result
        self.logger.write_to_log('INFO', 'info', '', 'write test end')

    def read_test(self):
        '''
        Execute command for read test
        '''
        self.logger.write_to_log('INFO','info','','start to execute command for read test')
        test_cmd = f'dd if={mount_point}/t.dat of=/dev/zero bs=512k count=16'
        test_result = SSH.execute_command(test_cmd)
        if test_result:
            result = self._get_dd_perf(test_result)
            # self.logger.write_to_log('HostTest', 'return', 'read_test',result)
            return result
        self.logger.write_to_log('INFO','info','','read test end')

    def get_test_perf(self):
        '''
        Calling method to read&write test
        '''
        self.logger.write_to_log('INFO', 'info', '', 'start calling method to read&write test')
        write_perf = self.write_test()
        print(f'write speed: {write_perf}')
        self.logger.write_to_log('INFO', 'info', '', (f'write speed: {write_perf}'))
        time.sleep(0.5)
        read_perf = self.read_test()
        print(f'read speed: {read_perf}')
        self.logger.write_to_log('INFO', 'info', '', (f'read speed: {read_perf}'))

    def start_test(self):
        self.logger.write_to_log('INFO', 'info', '', 'start to test')
        if not self.find_session():
            self.iscsi_login()
        dev_name = self.explore_disk()
        mount_status = self.format_mount(dev_name)
        if mount_status:
            self.get_test_perf()
        else:
            s.pwe(self.logger,f'Device {dev_name} mount failed')


if __name__ == "__main__":
    test = HostTest(21)
    command_result = '''[2:0:0:0]    cd/dvd  NECVMWar VMware SATA CD00 1.00  /dev/sr0
    [32:0:0:0]   disk    VMware   Virtual disk     2.0   /dev/sda 
    [33:0:0:15]  disk    LIO-ORG  res_lun_15       4.0   /dev/sdb 
    [33:0:0:21]  disk    LIO-ORG  res_luntest_21   4.0   /dev/sdc '''
    print(command_result)
