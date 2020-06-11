import connect
import time
import sys
import os
import re


class VplxDrbd(object):
    def __init__(self, lun_id):
        host = '10.203.1.199'
        port = 22
        username = 'root'
        password = 'password'
        timeout = 10
        self.ssh = connect.SSHConn(host, port, username, password, timeout)
        self.ssh._connect()
        self.lun_id = lun_id
        self.res_name = 'r'+str(lun_id)
        self.blk_dev_name = None
        self.drbd_device_name = 'drbd'+str(lun_id)

    def discover_new_lun(self):
        self.ssh.exctCMD('rescan-scsi-bus.sh')
        time.sleep(1)
        str_out = self.ssh.exctCMD('lsscsi')
        str_out = str_out.decode('utf-8')
        re_vplx_id_path = re.compile(
            r'''\:(\d*)\].*NETAPP[ 0-9a-zA-Z.]*([/a-z]*)''')
        stor_result = re_vplx_id_path.findall(str_out)
        result_tuple = stor_result[self.lun_id]
        assert_lun_id = result_tuple[0]
        print(assert_lun_id)
        if self.lun_id == assert_lun_id:
            self.blk_dev_name = result_tuple[1]
            print(self.blk_dev_name)
        else:
            sys.exit()

    # drdb--vi

    def prepare_config_file(self):
        context = r'''resource <{0}> {{
        on maxluntarget {{
        device /dev/<{1}>;
        disk /dev/<{2}>;
        address 10.203.1.199:7789;
        meta-disk internal;
        }} }}'''.format(self.res_name, self.drbd_device_name, self.blk_dev_name)

    def drdb_init(self):
        self.ssh.exctCMD(r'drbdadm create-md %s' % self.res_name)

    def drdb_up(self):
        self.ssh.exctCMD(f'drdbadm up {self.res_name}')

    def drdb_primary(self):
        self.ssh.exctCMD(f'drbdadm primary --force {self.res_name}')

    def drdb_status_verify(self):
        result = self.ssh.exctCMD(f'drbdadm status {self.res_name}')
        result = result.decode('utf-8')
        if result:
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(re_display)
            status = re_result[0]
            if status == 'UpToDate':
                return True
            else:
                sys.exit()


class VplxCrm(VplxDrbd):
    def __init__(self):
        self.LUN_NAME = self.res_name
        self.COLOCATION_NAME = f'co_{self.LUN_NAME}'
        self.TARGET_IQN = "iqn.2020-06.com.example:test-max-lun"
        self.INITIATOR_IQN = "iqn.1993-08.org.debian:01:885240c2d86c"
        self.TARGET_NAME = 't_test'
        self.ORDER_NAME = f'or_{self.LUN_NAME}'

    def iscisi_lun_create(self):
        command = f'crm conf primitive {self.LUN_NAME} \
        iSCSILogicalUnit params target_iqn=“{self.TARGET_IQN}” \
        implementation=lio-t lun={self.lun_id} path={self.blk_dev_name} \
        allowed_initiators=“{self.INITIATOR_IQN}” \
        op start timeout=40 interval=0 op stop timeout=40 interval=0 \
        op monitor timeout=40 interval=50 meta target-role=Stopped'
        self.ssh.exctCMD(command)

    def iscsi_lun_setting(self):
        comm_col = f'crm conf colocation {self.COLOCATION_NAME} inf: {self.LUN_NAME} {self.TARGET_NAME}'
        self.ssh.exctCMD(comm_col)
        comm_ord = f'crm conf order {self.ORDER_NAME} {self.TARGET_NAME} {self.LUN_NAME}'
        self.ssh.exctCMD(comm_ord)

    def iscsi_lun_start(self):
        comm_start = 'crm res start {self.LUN_NAME}'
        self.ssh.exctCMD(comm_start)
