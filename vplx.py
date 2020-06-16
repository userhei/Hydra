#  coding: utf-8
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
        self.ssh = connect.ConnSSH(host, port, user, password, timeout)
        self.lun_id = unique_id
        self.res_name = f'res_{unique_name}'
        self.blk_dev_name = None
        self.drbd_device_name = f'drbd_dev_{unique_name}'

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
                    # print(self.blk_dev_name)
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
        context = [f'resource {self.res_name} {{',
                    f'\ \ \ \ on maxluntarget {{']
                    #Anders 补齐

        # on maxluntarget {{
        # device /dev/{self.drbd_device_name};
        # disk {self.blk_dev_name};
        # address 10.203.1.199:7789;
        # meta-disk internal;
        # }} }}'''

        # context = '''resource {0} {{
        # on maxluntarget {{
        # device /dev/{1};
        # disk /dev/{2};
        # address 10.203.1.199:7789;
        # meta-disk internal;
        # }} }}'''.format(self.res_name, self.drbd_device_name, self.blk_dev_name)

        # context = f'adasdfsadf\nadfadfasdf'

        for echo_command in context:
            echo_result=self.ssh.excute_command(f'echo {echo_command} >> /etc/drbd.d/{self.res_name}.res')
            if echo_result is True:
                continue
            else:
                break
                print('fail to prepare drbd config file..')
                sys.exit()
                
        # echo_result=self.ssh.excute_command(f'echo {context} > /etc/drbd.d/{self.res_name}.res')
        # print(echo_result)
        # if echo_result is True:
        #     return True
            # print(echo_result)
            # mk_result=self.ssh.excute_command('mkdir -p /etc/drbd.d')
            # if mk_result is True:
            #     print('create folder success')
            #     return self.prepare_config_file()
            # else:
            #     print('create folder fail')
            #     sys.exit()
        # else:
        #     print('fail to prepare drbd config file..')
        #     sys.exit()

    def _drbd_init(self):
        if self.ssh.excute_command(f'drbdadm create-md {self.res_name}') is True:
            return True
        else:
            print(f'drbd resource {self.res_name} initialize failed')
            sys.exit()

    def _drbd_up(self):
        self.ssh.excute_command(f'drdbadm up {self.res_name}')

    def _drbd_primary(self):
        self.ssh.excute_command(f'drbdadm primary --force {self.res_name}')

    def drbd_cfg(self):
        if self._drbd_init():
            if self._drbd_up():
                self._drbd_primary()
    # 三个放在一个函数里里面调用好了，每一个执行完是需要判断是否执行成功。只有成功了才会继续执行下一个。


    def drbd_status_verify(self):
        result = self.ssh.excute_command(f'drbdadm status {self.res_name}')
        result = result.decode('utf-8')
        if result:
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(re_display)
            if re_result:
                status = re_result[0]
                if status == 'UpToDate':
                    print(f'{self.res_name} drbd status Check successful')
                else:
                    print(f'{self.res_name} drbd status Check failure')
                    sys.exit()
            else:
                print(f'{self.res_name} drbd status matching failure')
                sys.exit()


class VplxCrm(VplxDrbd):
    def __init__(self):
        self.lu_name = self.res_name
        self.colocation_name = f'co_{self.lu_name}'
        self.target_iqn = "iqn.2020-06.com.example:test-max-lun"
        self.initiator_iqn = "iqn.1993-08.org.debian:01:885240c2d86c"
        self.target_name = 't_test'
        self.order_name = f'or_{self.lu_name}'

    def iscisi_lun_create(self):
        command = f'crm conf primitive {self.lu_name} \
        iSCSILogicalUnit params target_iqn=“{self.target_iqn}” \
        implementation=lio-t lun={self.lun_id} path={self.blk_dev_name} \
        allowed_initiators=“{self.initiator_iqn}” \
        op start timeout=40 interval=0 op stop timeout=40 interval=0 \
        op monitor timeout=40 interval=50 meta target-role=Stopped'
        self.ssh.excute_command(command)

    def iscsi_lun_setting(self):
        comm_col = f'crm conf colocation {self.colocation_name} inf: {self.lu_name} {self.target_name}'
        self.ssh.excute_command(comm_col)
        comm_ord = f'crm conf order {self.order_name} {self.target_name} {self.lu_name}'
        self.ssh.excute_command(comm_ord)

    def iscsi_lun_start(self):
        comm_start = f'crm res start {self.lu_name}'
        self.ssh.excute_command(comm_start)

if __name__ == "__main__":
    w = VplxDrbd(0,'www')
    w.discover_new_lun()
    print(w.blk_dev_name)
    w.prepare_config_file()
    w.drbd_cfg()
    w.drbd_status_verify()
    pass