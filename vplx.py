#  coding: utf-8

import connect
import time
import sys
import os
import re

host = '10.203.1.199'
port = 22
user = 'root'
password = 'password'
timeout = 3


class VplxDrbd(object):
    def __init__(self, unique_id, unique_name):
        self.ssh = connect.ConnSSH(host, port, user, password, timeout)
        self.lun_id = unique_id
        self.res_name = f'res_{unique_name}_{unique_id}'
        self.blk_dev_name = None
        self.drbd_device_name = f'drbd{unique_id}'

    def discover_new_lun(self):
        self.ssh.excute_command('rescan-scsi-bus.sh')
        time.sleep(1)
        str_out = self.ssh.excute_command('lsscsi')
        if str_out:
            str_out = str_out.decode('utf-8')
            re_vplx_id_path = re.compile(
                r'''\:(\d*)\].*NETAPP[ 0-9a-zA-Z.]*(/dev/sd[a-z]{1,3})''')
            stor_result = re_vplx_id_path.findall(str_out)
            # print(stor_result)
            if stor_result:
                result_dict = dict(stor_result)
                if str(self.lun_id) in result_dict.keys():
                    self.blk_dev_name = result_dict[str(self.lun_id)]
                    print('Query to map new LUN succeeded')
                    return True
                else:
                    print('LUN does not exist')
                    sys.exit()
            else:
                print('check NETAPP failed')
                sys.exit()
        else:
            print('lsscsi check failed')
            sys.exit()

    def prepare_config_file(self):
        context = [rf'resource {self.res_name} {{',
                   rf'\ \ \ \ on maxluntarget {{',
                   rf'\ \ \ \ \ \ \ \ device /dev/{self.drbd_device_name}\;',
                   rf'\ \ \ \ \ \ \ \ disk {self.blk_dev_name}\;',
                   rf'\ \ \ \ \ \ \ \ address 10.203.1.199:7789\;',
                   rf'\ \ \ \ \ \ \ \ node-id 0\;',
                   rf'\ \ \ \ \ \ \ \ meta-disk internal\;',
                   r'\ \ \ \}',
                   r'}']

        for echo_command in context:
            echo_result = self.ssh.excute_command(
                f'echo {echo_command} >> /etc/drbd.d/{self.res_name}.res')
            if echo_result is True:
                continue
            else:
                print('fail to prepare drbd config file..')
                sys.exit()

    def _drbd_init(self):
        drbd_init = self.ssh.excute_command(
            f'drbdadm create-md {self.res_name}')
        # print(drbd_init)
        if drbd_init:
            drbd_init = drbd_init.decode('utf-8')
            re_drbd = re.compile(
                'New drbd meta data block successfully created')
            re_init = re_drbd.findall(drbd_init)
            if re_init:
                print('initialize success')
                return True
            else:
                print(f'drbd resource {self.res_name} initialize failed')
                sys.exit()
        else:
            print(f'drbd resource {self.res_name} initialize failed')
            sys.exit()

    def _drbd_up(self):
        drbd_up = self.ssh.excute_command(f'drbdadm up {self.res_name}')
        if drbd_up is True:
            print(f'drbd resource {self.res_name} up success')
            return True
        else:
            print(f'drbd resource {self.res_name} up failed')
            sys.exit()

    def _drbd_primary(self):
        drbd_primary = self.ssh.excute_command(
            f'drbdadm primary --force {self.res_name}')
        if drbd_primary is True:
            print(f'{self.res_name} primary success')
            return True
        else:
            print(f'drbd resource {self.res_name} primary failed')
            sys.exit()

    def drbd_cfg(self):
        if self._drbd_init():
            if self._drbd_up():
                if self._drbd_primary():
                    return True

    def drbd_status_verify(self):
        result = self.ssh.excute_command(f'drbdadm status {self.res_name}')
        result = result.decode('utf-8')
        # print(result)
        if result:
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(result)
            if re_result:
                status = re_result[0]
                if status == 'UpToDate':
                    print(f'{self.res_name} DRBD check successful')
                    return True
                else:
                    print(f'{self.res_name} DRBD verification failed')
                    sys.exit()
            else:
                print(f'{self.res_name} DRBD does not exist')
                sys.exit()


class VplxCrm(VplxDrbd):
    def __init__(self, unique_id, unique_name):
        VplxDrbd.__init__(self, unique_id, unique_name)
        self.lu_name = self.res_name
        self.colocation_name = f'co_{self.lu_name}'
        self.target_iqn = "iqn.2020-06.com.example:test-max-lun"
        self.initiator_iqn = "iqn.1993-08.org.debian:01:885240c2d86c"
        self.target_name = 't_test'
        self.order_name = f'or_{self.lu_name}'

    def _crm_create(self):
        command = f'crm conf primitive {self.lu_name} \
            iSCSILogicalUnit params target_iqn="{self.target_iqn}" \
            implementation=lio-t lun={self.lun_id} path={self.blk_dev_name} \
            allowed_initiators="{self.initiator_iqn}" op start timeout=40 interval=0 op stop timeout=40 interval=0 op monitor timeout=40 interval=50 meta target-role=Stopped'
        crm_create = command.encode('utf-8')
        if self.ssh.excute_command(crm_create) is True:
            print('iscisi lun_create success')
            return True
        else:
            print('iscisi lun_create failed')
            sys.exit()

    def _setting_col(self):
        comm_col = f'crm conf colocation {self.colocation_name} inf: {self.lu_name} {self.target_name}'
        set_col = self.ssh.excute_command(comm_col)
        if set_col is True:
            print('setting colocation successful')
            return True
        else:
            print('setting colocation failed')
            sys.exit()

    def _setting_ord(self):
        comm_ord = f'crm conf order {self.order_name} {self.target_name} {self.lu_name}'
        set_ord = self.ssh.excute_command(comm_ord)
        if set_ord is True:
            print('setting order succeed')
            return True
        else:
            print('setting order failed')
            sys.exit()

    def _crm_setting(self):
        if self._setting_col():
            if self._setting_ord():
                return True

    def _crm_start(self):
        comm_start = f'crm res start {self.lu_name}'
        crm_start = self.ssh.excute_command(comm_start)
        if crm_start is True:
            print('iscsi lun start successful')
            return True
        else:
            print('iscsi lun start failed')
            sys.exit()

    def crm_cfg(self):
        if self._crm_create():
            if self._crm_setting():
                if self._crm_start():
                    return True

    def crm_verify(self):
        pass


if __name__ == '__main__':
    pass
    # test_crm = VplxCrm('13', 'test')
    # if test_crm.discover_new_lun():
    #     test_crm.prepare_config_file()
    #     if test_crm.drbd_cfg():
    #         if test_crm.drbd_status_verify():
    #             if test_crm.crm_cfg():
    #                 print('Execute succeed')
    # test_crm.ssh.close()
