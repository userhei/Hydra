#encoding=utf-8
import connect
import time
import sys
import os
import re


host = '10.203.1.199'
port = '22'
user = 'root'
password = 'password'
timeout = 3


class VplxDrbd(object):
    def __init__(self, unique_id, unique_name):
        host = '10.203.1.199'
        port = 22
        username = 'root'
        password = 'password'
        timeout = 10
        self.ssh = connect.ConnSSH(host, port, username, password, timeout)
        self.lun_id = unique_id
        self.res_name = f'res{unique_id}'#
        self.blk_dev_name = None
        self.drbd_device_name = f'drbd{unique_id}'

    def discover_new_lun(self):
        self.ssh.excute_command('rescan-scsi-bus.sh')
        time.sleep(1)
        str_out = self.ssh.excute_command('lsscsi')
        if str_out:
            str_out = str_out.decode('utf-8')
            re_vplx_id_path = re.compile(
                r'''\:(\d*)\].*NETAPP[ 0-9a-zA-Z.]*(/dev/sd\w*)''')
            stor_result = re_vplx_id_path.findall(str_out)
            # print(stor_result)
            if stor_result:
                result_dict = dict(stor_result)
                if str(self.lun_id) in result_dict.keys():
                    self.blk_dev_name = result_dict[str(self.lun_id)]
                    print('Query to map new LUN succeeded')
                else:
                    print('LUN does not exist')
                    sys.exit()
            else:
                print('check NETAPP fail')
                sys.exit()
        else:
            print('lsscsi check fail')
            sys.exit()

    def prepare_config_file(self):
        context = [rf'resource {self.res_name} {{',
                    rf'\ \ \ \ on maxluntarget {{',
                    rf'\ \ \ \ device /dev/{self.drbd_device_name}\;',
                    rf'\ \ \ \ disk {self.blk_dev_name}\;',
                    rf'\ \ \ \ address 10.203.1.199:7789\;',
                    rf'\ \ \ \ meta-disk internal\;',
                    rf'\ \ \ \ node-id 0\;'
                    r'} }']
                  

        for echo_command in context:
            echo_result=self.ssh.excute_command(f'echo {echo_command} >> /etc/drbd.d/{self.res_name}.res')
            if echo_result is True:
                continue
            else:
                print('fail to prepare drbd config file..')
                sys.exit()


    def _drbd_init(self):
        drbd_init=self.ssh.excute_command(f'drbdadm create-md {self.res_name}')
        print(drbd_init)
        if  drbd_init is not True:# re
            print('init success')
            return True
        else:
            print(f'drbd resource {self.res_name} initialize failed')
            sys.exit()

    def _drbd_up(self):
        drbd_up=self.ssh.excute_command(f'drbdadm up {self.res_name}')
        if  drbd_up is True:
            print('up success')
            return True
        else:
            print(f'drbd resource {self.res_name} up failed')
    def _drbd_primary(self):
        drbd_primary=self.ssh.excute_command(f'drbdadm primary --force {self.res_name}')
        if drbd_primary is True:
            print('primary success')
            return True
        else:
            print(f'drbd resource {self.res_name} primary failed')
    def drbd_cfg(self):
        if self._drbd_init():
            if self._drbd_up():
                self._drbd_primary()

    def drbd_status_verify(self):
        result = self.ssh.excute_command(f'drbdadm status {self.res_name}')
        result = result.decode('utf-8')
        print(result)
        if result:
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(result)
            if re_result:
                status = re_result[0]
                if status == 'UpToDate':
                    print(f'{self.res_name} DRBD check successful')
                else:
                    print(f'{self.res_name} DRBD verification failed')
                    sys.exit()
            else:
                print(f'{self.res_name} DRBD does not exist')
                sys.exit()


class VplxCrm(VplxDrbd):
    def __init__(self,unique_id, unique_name):
        VplxDrbd.__init__(self,unique_id, unique_name)
        self.lu_name = self.res_name
        self.colocation_name = f'co_{self.lu_name}'
        self.target_iqn = "iqn.2020-06.com.example:test-max-lun"
        self.initiator_iqn = "iqn.1993-08.org.debian:01:885240c2d86c"
        self.target_name = 't_test'
        self.order_name = f'or_{self.lu_name}'

    def iscisi_lun_create(self):
        # command = f'crm conf primitive {self.lu_name} iSCSILogicalUnit params target_iqn=“{self.target_iqn}” implementation=lio-t lun={self.lun_id} path={self.blk_dev_name} allowed_initiators=“{self.initiator_iqn}” op start timeout=40 interval=0 op stop timeout=40 interval=0 op monitor timeout=40 interval=50 meta target-role=Stopped'
        command =u'crm conf primitive %s iSCSILogicalUnit params target_iqn=“%s” \
        implementation=lio-t lun=%s path=%s allowed_initiators=“%s” \
        op start timeout=40 interval=0 op stop timeout=40 interval=0 op monitor \
        timeout=40 interval=50 meta target-role=Stopped'%(self.lu_name,self.target_iqn,self.lun_id,self.blk_dev_name,self.initiator_iqn)
        comm=command.encode('utf-8')
        if self.ssh.excute_command(comm) is True:
            print('iscisi lun_create success')
            return True
        else:
            print('iscisi lun_create failed')
            sys.exit()

    def iscsi_lun_setting(self):
        comm_col = f'crm conf colocation {self.colocation_name} inf: {self.lu_name} {self.target_name}'
        comm_ord = f'crm conf order {self.order_name} {self.target_name} {self.lu_name}'
        set_col=self.ssh.excute_command(comm_col)
        if set_col is True:
            set_ord=self.ssh.excute_command(comm_ord)
            if set_ord is True:
                print('setting order and colocation successful')
                return True
            else:
                print('setting order failed')
                sys.exit()
        else:
            print('setting colocation failed')
            sys.exit()

    def iscsi_lun_start(self):
        comm_start = f'crm res start {self.lu_name}'
        lun_start=self.ssh.excute_command(comm_start)
        if lun_start is True:
            return True
        else:
            print('iscsi lun start failed')

