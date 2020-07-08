#  coding: utf-8

import connect
import sundry as s
import time
import sys
import os
import re
import logdb

# global SSH
SSH = None

global ID
global STRING
global replay
global TID

host = '10.203.1.199'
port = 22
user = 'root'
password = 'password'
timeout = 3

target_iqn = "iqn.2020-06.com.example:test-max-lun"
initiator_iqn = "iqn.1993-08.org.debian:01:885240c2d86c"
target_name = 't_test'

def init_ssh(logger):
    global SSH
    if not SSH:
        SSH = connect.ConnSSH(host, port, user, password, timeout, logger)
    else:
        pass

def discover_new_lun(logger):
    '''
    Scan and find the disk from NetApp
    '''
    logger.write_to_log('T','INFO','info','start','',f'  Discover_new_lun for id {ID}')
    cmd_rescan = '/usr/bin/rescan-scsi-bus.sh'
    result_rescan = SSH.execute_command(cmd_rescan)
    if result_rescan['sts']:
        cmd_lsscsi = 'lsscsi'
        result_lsscsi = SSH.execute_command(cmd_lsscsi)
        if result_lsscsi['sts']:
            result_lsscsi = result_lsscsi['rst'].decode('utf-8')
        else:
            print(f'command {cmd_lsscsi} execute failed')
            logger.write_to_log('T','INFO','warning','start','',f'command {cmd_lsscsi} execute failed')
        #log DAT:output:cmd:lsscsi:result_lsscsi
    # if SSH.execute_command('/usr/bin/rescan-scsi-bus.sh'):#新的返回值有状态和数值,以状态判断,记录数值
    #     result_lsscsi = SSH.execute_command('lsscsi')
    else:
        s.pwe(logger,f'Scan new LUN failed on NetApp')
    re_find_id_dev = r'\:(\d*)\].*NETAPP[ 0-9a-zA-Z._]*(/dev/sd[a-z]{1,3})'
    blk_dev_name = s.get_disk_dev(str(ID), re_find_id_dev, result_lsscsi, 'NetApp',logger)
    
    print(f'Find device {blk_dev_name} for LUN id {ID}')
    logger.write_to_log('T','INFO','info','finish','',f'    Find device {blk_dev_name} for LUN id {ID}')
    return blk_dev_name

class VplxDrbd(object):
    '''
    Integrate LUN in DRBD resources
    '''

    def __init__(self, logger):
        print('VplxDrbd __init__')
        self.logger = logger
        self.logger.write_to_log('T', 'INFO', 'info', 'start', '', 'Start to configure DRDB resource and crm resource on VersaPLX')
        init_ssh(self.logger)
        self.blk_dev_name = discover_new_lun(logger)
        self.res_name = f'res_{STRING}_{ID}'
        global DRBD_DEV_NAME
        DRBD_DEV_NAME = f'drbd{ID}'
        self.logger.write_to_log('T','INFO','info','start','',f'    Start to configure DRBD resource {self.res_name}')
    
    def prepare_config_file(self):
        '''
        Prepare DRDB resource config file
        '''
        self.logger.write_to_log('T','INFO','info','start','',f'      Start prepare config fiel for resource {self.res_name}')
        context = [rf'resource {self.res_name} {{',
                   rf'\ \ \ \ on maxluntarget {{',
                   rf'\ \ \ \ \ \ \ \ device /dev/{DRBD_DEV_NAME}\;',
                   rf'\ \ \ \ \ \ \ \ disk {self.blk_dev_name}\;',
                   rf'\ \ \ \ \ \ \ \ address 10.203.1.199:7789\;',
                   rf'\ \ \ \ \ \ \ \ node-id 0\;',
                   rf'\ \ \ \ \ \ \ \ meta-disk internal\;',
                   r'\ \ \ \}',
                   r'}']

        self.logger.write_to_log('F','DATA','value','list','content of drbd config file',context)

        # for echo_command in context:
        #     echo_result = SSH.execute_command(
        #         f'echo {echo_command} >> /etc/drbd.d/{self.res_name}.res')
        #     if echo_result is True:
        #         continue
        #     else:
        #         s.pe('fail to prepare drbd config file..')
        config_file_name = f'{self.res_name}.res'
        for i in range(len(context)):
            if i == 0:
                echo_result = SSH.execute_command(
                    f'echo {context[i]} > /etc/drbd.d/{self.res_name}.res')
            else:
                echo_result = SSH.execute_command(
                    f'echo {context[i]} >> /etc/drbd.d/{self.res_name}.res')
            if echo_result['sts']:
                continue
            else:
                s.pwe(self.logger,'fail to prepare drbd config file..')
        print(f'create DRBD config file "{self.res_name}.res" done')
        self.logger.write_to_log('T','INFO','info','finish','',f'      Create DRBD config file "{self.res_name}.res" done')

    def _drbd_init(self):
        '''
        Initialize DRBD resource
        '''
        info_msg = f'      Initialize drbd for {self.res_name}'
        self.logger.write_to_log('T', 'INFO', 'info', 'start', '', info_msg)
        init_cmd = f'drbdadm create-md {self.res_name}'
        # print(init_cmd)
        drbd_init = SSH.execute_command(init_cmd)
        # log DAT:output:cmd:f'{init_cmd}':start to init drbd for {self.res_name}
        if drbd_init['sts']:
            drbd_init = drbd_init['rst'].decode('utf-8')
            # print(drbd_init)
            re_drbd = re.compile('New drbd meta data block successfully created')
            re_init = re_drbd.findall(drbd_init)
            oprt_id = s.get_oprt_id()
            self.logger.write_to_log('T', 'OPRT', 'regular', 'findall', oprt_id, {'New drbd meta data block successfully created':drbd_init})
            self.logger.write_to_log('F', 'DATA', 'regular', 'findall', oprt_id, re_init)
            if re_init:
                print(f'{self.res_name} initialize success')
                # self.logger.write_to_log('INFO','info','',(f'{self.res_name} initialize success'))
                return True
            else:
                s.pwe(self.logger, f'drbd resource {self.res_name} initialize failed')

        else:
            s.pwe(self.logger, f'drbd resource {self.res_name} initialize failed')

    def _drbd_up(self):
        '''
        Start DRBD resource
        '''
        print('_drbd_up')
        oprt_id_dec = 'Start DRBD resource'
        up_cmd = f'drbdadm up {self.res_name}'
        if replay == 'no':
            oprt_id = s.get_oprt_id()
            self.logger.write_to_log('T','INFO','info','start','',f'      Start to drbd up for {self.res_name}')
            self.logger.write_to_log('F','DATA','oprt_id',oprt_id_dec,'',oprt_id)
            self.logger.write_to_log('T', 'OPRT', 'cmd', 'ssh', oprt_id, up_cmd)
            drbd_up = SSH.execute_command(up_cmd)
            self.logger.write_to_log('F','DATA','cmd','ssh',oprt_id,drbd_up)
            if drbd_up['sts']:
                print(f'{self.res_name} up success')
                self.logger.write_to_log('T','INFO','info','finish','',f'      {self.res_name} started successfully')
                return True
            else:
                s.pwe(self.logger,f'drbd resource {self.res_name} up failed')
        elif replay == 'yes':
            print('-------------------------------------')
            print('_drbd_up replay:')
            db = logdb.LogDB()
            oprt_id_replay = db.get_oprt_id(TID,oprt_id_dec)
            if oprt_id_replay:
                drbd_up = eval(db.get_cmd_result(oprt_id_replay)[0])
            else:
                drbd_up = {}
            if drbd_up['sts']:
                print(f'{self.res_name} up success')
                return True #原来存在
            else:
                print(f'drbd resource {self.res_name} up failed')
                sys.exit()




    def _drbd_primary(self):
        '''
        Complete initial synchronization of resources
        '''
        self.logger.write_to_log('T','INFO','info','start','',f'      Start to initial synchronization for {self.res_name}')
        primary_cmd = f'drbdadm primary --force {self.res_name}'
        drbd_primary = SSH.execute_command(primary_cmd)
        if drbd_primary['sts']:
            print(f'{self.res_name} primary success')
            self.logger.write_to_log('T', 'INFO', 'info', 'finish', '', f'      {self.res_name} synchronize successfully')
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
        self.logger.write_to_log('T','INFO','info','start','','      Start to check DRBD resource status')
        verify_cmd = f'drbdadm status {self.res_name}'
        result = SSH.execute_command(verify_cmd)
        if result['sts']:
            result = result['rst'].decode('utf-8')
            re_display = re.compile(r'''disk:(\w*)''')
            re_result = re_display.findall(result)
            oprt_id = s.get_oprt_id()
            self.logger.write_to_log('T','OPRT','regular','findall',oprt_id,{"disk:(\w*)":result})
            if re_result:
                status = re_result[0]
                self.logger.write_to_log('F', 'DATA', 'regular', 'findall', oprt_id, status)
                if status == 'UpToDate':
                    print(f'      {self.res_name} DRBD check successfully')
                    self.logger.write_to_log('T','INFO','info','finish','',f'      {self.res_name} DRBD check successfully')
                    # self.logger.write_to_log('INFO','info','',(f'{self.res_name} DRBD check successful'))
                    return True
                else:
                    s.pwe(self.logger,f'{self.res_name} DRBD verification failed')
            else:
                s.pwe(self.logger,f'{self.res_name} DRBD does not exist')


class VplxCrm(object):
    def __init__(self, logger):
        init_ssh(logger)
        self.logger = logger
        self.lu_name = f'res_{STRING}_{ID}' # same as drbd resource name
        self.colocation_name = f'co_{self.lu_name}'
        self.order_name = f'or_{self.lu_name}'
        self.logger.write_to_log('T','INFO','info','start','',f'  Start to configure crm resource {self.lu_name}')

    def _crm_create(self):
        '''
        Create iSCSILogicalUnit resource
        '''
        self.logger.write_to_log('T','INFO','info','start','',f'    Start to create iSCSILogicalUnit resource {self.lu_name}')
        cmd_crm_create = f'crm conf primitive {self.lu_name} \
            iSCSILogicalUnit params target_iqn="{target_iqn}" \
            implementation=lio-t lun={ID} path="/dev/{DRBD_DEV_NAME}"\
            allowed_initiators="{initiator_iqn}" op start timeout=40 interval=0 op stop timeout=40 interval=0 op monitor timeout=40 interval=50 meta target-role=Stopped'
        result_crm_create = SSH.execute_command(cmd_crm_create)
        if result_crm_create['sts']:
            print('create iSCSILogicalUnit successfully')
            self.logger.write_to_log('T','INFO','info','finish','','      Create iSCSILogicalUnit successfully')
            return True
        else:
            s.pwe(self.logger,'iscisi lun_create failed')

    def _setting_col(self):
        '''
        Setting up iSCSILogicalUnit resources of colocation
        '''
        self.logger.write_to_log('T','INFO','info','start','','      start to setting up iSCSILogicalUnit resources of colocation')
        cmd_crm_col = f'crm conf colocation {self.colocation_name} inf: {self.lu_name} {target_name}'
        result_crm_col = SSH.execute_command(cmd_crm_col)
        if result_crm_col['sts']:
            print('  setting colocation successful')
            self.logger.write_to_log('T','INFO','info','finish','','      Setting colocation successful')
            return True
        else:
            s.pwe(self.logger,'setting colocation failed')

    def _setting_order(self):
        '''
        Setting up iSCSILogicalUnit resources of order
        '''
        self.logger.write_to_log('T','INFO','info','start','','      Start to setting up iSCSILogicalUnit resources of order')
        cmd_crm_order = f'crm conf order {self.order_name} {target_name} {self.lu_name}'
        result_crm_order = SSH.execute_command(cmd_crm_order)
        if result_crm_order['sts']:
            print('setting order succeed')
            self.logger.write_to_log('T','INFO','info','finish','','      Setting order succeed')
            return True
        else:
            s.pwe(self.logger,'setting order failed')

    def _crm_setting(self):
        if self._setting_col():
            if self._setting_order():
                return True

    def _crm_start(self):
        '''
        start the iSCSILogicalUnit resource
        '''
        self.logger.write_to_log('T','INFO','info','start','',f'      Start the iSCSILogicalUnit resource {self.lu_name}')
        cmd_lu_start = f'crm res start {self.lu_name}'
        result_lu_start = SSH.execute_command(cmd_lu_start)
        if result_lu_start['sts']:
            print('  iSCSI LUN start successful')
            self.logger.write_to_log('T','INFO','info','finish','','      ISCSI LUN start successful')
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
