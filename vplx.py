#  coding: utf-8

import connect
import sundry as s
import time
import sys
import os
import re


host = '10.203.1.199'
port = 22
user = 'root'
password = 'password'
timeout = 3



target_iqn = "iqn.2020-06.com.example:test-max-lun"
initiator_iqn = "iqn.1993-08.org.debian:01:885240c2d86c"
target_name = 't_test'


class VplxDrbd(object):
    '''
    Integrate LUN in DRBD resources
    '''

    def __init__(self, unique_id, unique_name,logger):
        self.logger = logger
        self.ssh = connect.ConnSSH(host, port, user, password, timeout,logger)
        self.id = unique_id
        self.res_name = f'res_{unique_name}_{unique_id}'
        self.blk_dev_name = None
        self.drbd_device_name = f'drbd{unique_id}'

        self.logger.write_to_log('INFO','info','start','',f'config drbd resource {self.res_name}')

    # def _find_blk_dev(self, id, ls_result):
    #     '''
    #     Use re to get the blk_dev_name through id
    #     '''
    #     re_vplx_id_path = re.compile(
    #         r'''\:(\d*)\].*NETAPP[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})''')
    #     stor_result = re_vplx_id_path.findall(ls_result)
    #     if stor_result:
    #         dict_stor = dict(stor_result)
    #         if str(id) in dict_stor.keys():
    #             blk_dev_name = dict_stor[str(id)]
    #             return blk_dev_name

    def discover_new_lun(self):
        '''
        Scan and find the disk from NetApp
        '''
        self.logger.write_to_log('INFO','info','start','',f'discover_new_lun for id {self.id}')
        lsscsi_result = None
        if self.ssh.excute_command('/usr/bin/rescan-scsi-bus.sh'):
            lsscsi_result = self.ssh.excute_command('lsscsi')
        else:
            s.pwe(self.logger,f'Scan new LUN failed on NetApp')
        re_find_id_dev = r'\:(\d*)\].*NETAPP[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
        self.blk_dev_name = s.GetDiskPath(self.id, re_find_id_dev, lsscsi_result, 'NetApp',self.logger).explore_disk()
        print(f'Find device {self.blk_dev_name} for LUN id {self.id}')
        self.logger.write_to_log('INFO', 'info', 'done','' ,f'Find device {self.blk_dev_name} for LUN id {self.id}')
            

    def prepare_config_file(self):
        '''
        Prepare DRDB resource config file
        '''
        self.logger.write_to_log('INFO','info','start','',f'prepare config fiel for resource {self.res_name}')
        context = [rf'resource {self.res_name} {{',
                   rf'\ \ \ \ on maxluntarget {{',
                   rf'\ \ \ \ \ \ \ \ device /dev/{self.drbd_device_name}\;',
                   rf'\ \ \ \ \ \ \ \ disk {self.blk_dev_name}\;',
                   rf'\ \ \ \ \ \ \ \ address 10.203.1.199:7789\;',
                   rf'\ \ \ \ \ \ \ \ node-id 0\;',
                   rf'\ \ \ \ \ \ \ \ meta-disk internal\;',
                   r'\ \ \ \}',
                   r'}']

        self.logger.write_to_log('DATA','input','list','',context)


        # for echo_command in context:
        #     echo_result = self.ssh.excute_command(
        #         f'echo {echo_command} >> /etc/drbd.d/{self.res_name}.res')
        #     if echo_result is True:
        #         continue
        #     else:
        #         s.pe('fail to prepare drbd config file..')
        config_file_name = f'{self.res_name}.res'
        for i in range(len(context)):
            if i == 0:
                echo_result = self.ssh.excute_command(
                    f'echo {context[i]} > /etc/drbd.d/{self.res_name}.res')
            else:
                echo_result = self.ssh.excute_command(
                    f'echo {context[i]} >> /etc/drbd.d/{self.res_name}.res')
            if echo_result is True:
                continue
            else:
                s.pwe(self.logger,'fail to prepare drbd config file..')
        print(f'Create DRBD config file "{self.res_name}.res" done')
        self.logger.write_to_log('INFO','info','done','',f'Create DRBD config file "{self.res_name}.res" done')

    def _drbd_init(self):
        '''
        Initiakize DRBD resource
        '''
        self.logger.write_to_log('INFO','info','start','',f'init drbd for {self.res_name}')
        #
        init_cmd = f'drbdadm create-md {self.res_name}'
        drbd_init = self.ssh.excute_command(init_cmd)

        if drbd_init:
            drbd_init = drbd_init.decode('utf-8')
            re_drbd = re.compile(
                'New drbd meta data block successfully created')
            re_init = re_drbd.findall(drbd_init)
            self.logger.write_to_log('DATA','result','re','',re_init)
            if re_init:
                print(f'{self.res_name} initialize success')
                self.logger.write_to_log('INFO','info','done','',(f'{self.res_name} initialize success'))
                return True
            else:
                s.pwe(self.logger,f'drbd resource {self.res_name} initialize failed')

        else:
            s.pwe(self.logger,f'drbd resource {self.res_name} initialize failed')

    def _drbd_up(self):
        '''
        Start DRBD resource
        '''
        self.logger.write_to_log('INFO','info','start','',f'start up drbd resource {self.res_name}')
        up_cmd = f'drbdadm up {self.res_name}'
        drbd_up = self.ssh.excute_command(up_cmd)
        if drbd_up is True:
            print(f'{self.res_name} up success')
            self.logger.write_to_log('INFO','info','done','',(f'{self.res_name} up success'))
            return True
        else:
            s.pwe(self.logger,f'drbd resource {self.res_name} up failed')

    def _drbd_primary(self):
        '''
        Complete initial synchronization of resources
        '''
        self.logger.write_to_log('INFO','info','start','',f'initial synchronization for {self.res_name}')
        primary_cmd = f'drbdadm primary --force {self.res_name}'
        drbd_primary = self.ssh.excute_command(primary_cmd)
        if drbd_primary is True:
            print(f'{self.res_name} primary success')
            self.logger.write_to_log('INFO','info','done','',(f'{self.res_name} primary success'))
            return True
        else:
            s.pwe(self.logger,f'drbd resource {self.res_name} primary failed')

    def drbd_cfg(self):
        if self._drbd_init():
            if self._drbd_up():
                if self._drbd_primary():
                    return True

    def drbd_status_verify(self):
        '''
        Check DRBD resource status and confirm the status is UpToDate
        '''
        self.logger.write_to_log('INFO','info','start','','check DRBD resource status')
        verify_cmd = f'drbdadm status {self.res_name}'
        result = self.ssh.excute_command(verify_cmd)
        if result:
            result = result.decode('utf-8')
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(result)
            self.logger.write_to_log('DATA','result','re','',re_result)
            if re_result:
                status = re_result[0]
                if status == 'UpToDate':
                    print(f'{self.res_name} DRBD check successful')
                    self.logger.write_to_log('INFO','info','done','',(f'{self.res_name} DRBD check successful'))
                    return True
                else:
                    s.pwe(self.logger,f'{self.res_name} DRBD verification failed')
            else:
                s.pwe(self.logger,f'{self.res_name} DRBD does not exist')


class VplxCrm(VplxDrbd):
    def __init__(self, unique_id, unique_name,logger):
        VplxDrbd.__init__(self, unique_id, unique_name,logger)
        self.lu_name = self.res_name
        self.colocation_name = f'co_{self.lu_name}'
        self.target_iqn = target_iqn
        self.initiator_iqn = initiator_iqn
        self.target_name = target_name
        self.order_name = f'or_{self.lu_name}'
        self.logger.write_to_log('INFO','info','start','',f'config crm resource {self.lu_name}') #
    def _crm_create(self):
        '''
        Create iSCSILogicalUnit resource
        '''
        self.logger.write_to_log('INFO','info','start','',f'create iSCSILogicalUnit resource {self.lu_name}')
        crm_create_cmd = f'crm conf primitive {self.lu_name} \
            iSCSILogicalUnit params target_iqn="{self.target_iqn}" \
            implementation=lio-t lun={self.id} path="/dev/{self.drbd_device_name}"\
            allowed_initiators="{self.initiator_iqn}" op start timeout=40 interval=0 op stop timeout=40 interval=0 op monitor timeout=40 interval=50 meta target-role=Stopped'

        if self.ssh.excute_command(crm_create_cmd) is True:
            print('iscisi lun_create success')
            self.logger.write_to_log('INFO','info','done','',('iscisi lun_create success'))
            return True
        else:
            s.pwe(self.logger,'iscisi lun_create failed')

    def _setting_col(self):
        '''
        Setting up iSCSILogicalUnit resources of colocation
        '''
        self.logger.write_to_log('INFO','info','start','','setting up iSCSILogicalUnit resources of colocation')
        col_cmd = f'crm conf colocation {self.colocation_name} inf: {self.lu_name} {self.target_name}'
        set_col = self.ssh.excute_command(col_cmd)
        if set_col is True:
            print('setting colocation successful')
            self.logger.write_to_log('INFO','info','done','',('setting colocation successful'))
            return True
        else:
            s.pwe(self.logger,'setting colocation failed')

    def _setting_order(self):
        '''
        Setting up iSCSILogicalUnit resources of order
        '''
        self.logger.write_to_log('INFO','info','start','','start to setting up iSCSILogicalUnit resources of order')
        order_cmd = f'crm conf order {self.order_name} {self.target_name} {self.lu_name}'
        set_order = self.ssh.excute_command(order_cmd)
        if set_order is True:
            print('setting order succeed')
            self.logger.write_to_log('INFO','info','done','',('setting order succeed'))
            return True
        else:
            s.pwe(self.logger,'setting order failed')

    def _crm_setting(self):
        if self._setting_col():
            if self._setting_order():
                # self.logger.write_to_log('VplxCrm', 'return', '_setting_col', True)
                return True

    def _crm_start(self):
        '''
        start the iSCSILogicalUnit resource
        '''
        self.logger.write_to_log('INFO','info','start','',f'start the iSCSILogicalUnit resource {self.lu_name}')
        crm_start_cmd = f'crm res start {self.lu_name}'
        crm_start = self.ssh.excute_command(crm_start_cmd)
        if crm_start is True:
            print('iscsi lun start successful')
            self.logger.write_to_log('INFO','info','done','',('iscsi lun start successful'))
            return True
        else:
            s.pwe(self.logger,'iscsi lun start failed')

    def crm_cfg(self):
        if self._crm_create():
            if self._crm_setting():
                if self._crm_start():
                    return True

    def crm_verify(self):
        pass


# if __name__ == '__main__':
#     test_crm = VplxCrm('72', 'luntest')
#     test_crm.discover_new_lun()
