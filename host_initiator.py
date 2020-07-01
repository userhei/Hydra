# coding:utf-8

import connect
import re
import sys
import time
import sundry as s

SSH = None
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

def umount_mnt(logger):
    SSH.execute_command('umount /mnt')

def iscsi_login(logger):
    '''
    Discover iSCSI and login to session
    '''
    # self.logger.write_to_log('INFO','info','',f'start to discover iscsi and login to {vplx_ip}')
    cmd_iscsi_login = f'iscsiadm -m discovery -t st -p {vplx_ip} -l'
    result_iscsi_login = SSH.execute_command(cmd_iscsi_login)

    if result_iscsi_login['sts']:
        result_iscsi_login = result_iscsi_login['rst'].decode('utf-8')
        re_login = re.compile(
            f'Login to.*portal: ({vplx_ip}).*successful')
        re_result = re_login.findall(result_iscsi_login)
        # self.logger.write_to_log('DATA','output','re_result',re_result)

        if re_result:
            return True
        else:
            s.pwe(self.logger,f'iscsi login to {vplx_ip} failed')

def find_session(logger):
    '''
    Execute the command and check up the status of session
    '''
    # self.logger.write_to_log('INFO', 'info', '', 'start to execute the command and check up the status of session')
    cmd_session = 'iscsiadm -m session'
    result_session = SSH.execute_command(cmd_session)
    if result_session['sts']:
        result_session = result_session['rst'].decode('utf-8')
        re_session = re.compile(f'tcp:.*({vplx_ip}):.*')
        re_result = re_session.findall(result_session)
        # self.logger.write_to_log('DATA', 'output', 're_result', re_result)
        if re_result:
            # self.logger.write_to_log('HostTest','return','find_session',True)
            return True


def discover_new_lun(logger):
    '''
    Scan and find the disk from NetApp
    '''
    # self.logger.write_to_log('INFO','info','',f'start to discover_new_lun for id {ID}')
    cmd_rescan = '/usr/bin/rescan-scsi-bus.sh'
    result_rescan = SSH.execute_command(cmd_rescan)
    if result_rescan['sts']:
        cmd_lsscsi = 'lsscsi'
        result_lsscsi = SSH.execute_command(cmd_lsscsi)
        if result_lsscsi['sts']:
            result_lsscsi = result_lsscsi['rst'].decode('utf-8')
        else:
            print(f'command {cmd_lsscsi} execute failed')
        #log DAT:output:cmd:lsscsi:result_lsscsi
    # if SSH.execute_command('/usr/bin/rescan-scsi-bus.sh'):#新的返回值有状态和数值,以状态判断,记录数值
    #     result_lsscsi = SSH.execute_command('lsscsi')
    else:
        s.pwe(self.logger,f'Scan new LUN failed on NetApp')
    re_find_id_dev = r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
    blk_dev_name = s.get_disk_dev(str(ID), re_find_id_dev, result_lsscsi, 'NetApp',logger)
    
    print(f'Find device {blk_dev_name} for LUN id {ID}')
    # self.logger.write_to_log('INFO', 'info', '', f'Find device {blk_dev_name} for LUN id {ID}')
    return blk_dev_name

class HostTest(object):
    '''
    Format, write, and read iSCSI LUN
    '''

    def __init__(self, logger):
        
        self.logger = logger
        # self.logger.host = host # 给logger对象的host属性附上这个模块的host
        init_ssh(self.logger)
        umount_mnt(self.logger)
        if not find_session(logger):
            iscsi_login(logger)


        # self.logger.write_to_log('INFO','info','','find_session end')

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

    # def explore_disk(self):
    #     '''
    #      Scan and get the device path from VersaPLX
    #     '''
    #     # self.logger.write_to_log('INFO','info','','start to explore_disk')
    #     # lsscsi_result = None
    #     cmd_rescan
    #     if SSH.execute_command('/usr/bin/rescan-scsi-bus.sh'):
    #         time.sleep(0.5)
    #         lsscsi_result = SSH.execute_command('lsscsi')# 什么情况下是True
    #         if lsscsi_result['sts']:
    #             lsscsi_result = lsscsi_result['rst']
    #         else:
    #             print('lsscsi comand failed')
    #     else:
    #         s.pwe(self.logger,f'Scan new LUN failed on VersaPLX')
    #     re_find_id_dev = r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
    #     disk_path = s.get_disk_dev(ID, re_find_id_dev, result_lsscsi, 'VersaPLX',self.logger)
    #     # self.logger.write_to_log('INFO','info',result,'explore_disk end')
    #     return disk_path

    def _judge_format(self, string):
        '''
        Determine the format status
        '''
        # self.logger.write_to_log('INFO','info','','start to determine the format status')
        re_done = re.compile(r'done')
        # self.logger.write_to_log('HostTest','regular_before','_judge_format',string)
        # self.logger.write_to_log('DATA','output','re_result',re_done.findall(string))
        if len(re_done.findall(string)) == 4:
            return True
        # self.logger.write_to_log('INFO','info','','_judge_format end')

    def format_mount(self, dev_name):
        '''
        Format disk and mount disk
        '''
        # self.logger.write_to_log('INFO','info','',f'start to format disk {dev_name} and mount disk {dev_name}')
        cmd_format = f'mkfs.ext4 {dev_name} -F'
        result_format = SSH.execute_command(cmd_format)
        if result_format['sts']:
            result_format = result_format['rst'].decode('utf-8')
            if self._judge_format(result_format):
                cmd_mount = f'mount {dev_name} {mount_point}'
                result_mount = SSH.execute_command(cmd_mount)
                if result_mount['sts']:
                    #self.logger.write_to_log('HostTest', 'return', 'format_mount', True)
                    return True
                else:
                    s.pwe(self.logger,f"mount {dev_name} to {mount_point} failed")

            else:
                s.pwe(self.logger,"format disk %s failed" % dev_name)
        else:
            print('format failed')

    def _get_dd_perf(self, cmd_dd):
        '''
        Use re to get the speed of test
        '''
        # cmd_dd = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        result_dd = SSH.execute_command(cmd_dd)
        # print(result_dd)
        # if result_dd['sts'] and not result_dd['sts']:
        result_dd = result_dd['rst'].decode('utf-8')
    # self.logger.write_to_log('INFO','info','','start to get the speed of test')
        re_performance = re.compile(r'.*s, ([0-9.]* [A-Z]B/s)')
        re_result = re_performance.findall(result_dd)
    # self.logger.write_to_log('DATA', 'output', 're_result', re_result)
        if re_result:
            # self.logger.write_to_log('DATA', 'output', 'return', perf[0])
            dd_perf = re_result[0]
            return dd_perf
        else:
            s.pwe(self.logger,'Can not get test result') 

    def get_test_perf(self):
        '''
        Calling method to read&write test
        '''
        cmd_dd_write = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        cmd_dd_read = f'dd if={mount_point}/t.dat of=/dev/zero bs=512k count=16'
        # self.logger.write_to_log('INFO', 'info', '', 'start calling method to read&write test')
        write_perf = self._get_dd_perf(cmd_dd_write)
        print(f'write speed: {write_perf}')
        # self.logger.write_to_log('INFO', 'info', '', (f'write speed: {write_perf}'))
        time.sleep(0.5)
        read_perf = self._get_dd_perf(cmd_dd_read)
        print(f'read speed: {read_perf}')
        # self.logger.write_to_log('INFO', 'info', '', (f'read speed: {read_perf}'))

    def start_test(self):
        # self.logger.write_to_log('INFO', 'info', '', 'start to test')
        dev_name = discover_new_lun(self.logger)
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
