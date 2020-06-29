
#  coding: utf-8
import argparse
import sys
import time

import storage
import vplx
import host_initiator
import sundry
import log

class HydraArgParse():
    '''
    Hydra project
    parse argument for auto max lun test program
    '''

    def __init__(self):
        self.transaction_id = sundry.get_transaction_id()
        self.logger = log.Log(self.transaction_id)
        self.argparse_init()

    def argparse_init(self):
        self.parser = argparse.ArgumentParser(prog='max_lun',
                                              description='Test max lun number of VersaRAID-SDS')
        # self.parser.add_argument(
        #     '-r',
        #     '--run',
        #     action="store_true",
        #     dest="run_test",
        #     help="run auto max lun test")
        self.parser.add_argument(
            '-s',
            action="store",
            dest="uniq_str",
            help="The unique string for this test, affects related naming")
        self.parser.add_argument(
            '-id',
            action="store",
            dest="id_range",
            help='The ID range of test, split with ","')

    def _storage(self, unique_id, unique_str):
        '''
        Connect to NetApp Storage
        Create LUN and Map to VersaPLX
        '''
        netapp = storage.Storage(unique_id, unique_str,self.logger)
        netapp.lun_create()
        netapp.lun_map()

    def _vplx_drbd(self, unique_id, unique_str):
        '''
        Connect to VersaPLX
        Go on DRDB resource configuration
        '''
        drbd = vplx.VplxDrbd(unique_id, unique_str,self.logger)
        drbd.discover_new_lun() # 查询新的lun有没有map过来，返回path
        drbd.prepare_config_file() # 创建配置文件
        drbd.drbd_cfg() # run
        drbd.drbd_status_verify() # 验证有没有启动（UptoDate）

    def _vplx_crm(self, unique_id, unique_str):
        '''
        Connect to VersaPLX
        Go on crm configuration
        '''
        crm = vplx.VplxCrm(unique_id, unique_str,self.logger)
        crm.crm_cfg()

    def _host_test(self, unique_id):
        '''
        Connect to host
        Umount and start to format, write, and read iSCSI LUN
        '''
        host = host_initiator.HostTest(unique_id,self.logger)
        host.ssh.excute_command('umount /mnt')
        host.start_test()

    @sundry.record_exception
    def run(self):
        if sys.argv:
            path = sundry.get_path()
            cmd = ' '.join(sys.argv)
            self.logger.write_to_log('DATA', 'input', 'user_input', cmd)

        args = self.parser.parse_args()
        '''
        uniq_str: The unique string for this test, affects related naming
        '''
        if args.uniq_str:
            if args.id_range:
                id_range = args.id_range.split(',')
                if len(id_range) == 2:
                    id_start, id_end = int(id_range[0]), int(id_range[1])
                else:
                    self.logger.write_to_log('INFO','info','','print_help')
                    self.parser.print_help()
                    sys.exit()
            else:
                self.logger.write_to_log('INFO','info','','print_help')
                self.parser.print_help()
                sys.exit()

            for i in range(id_start, id_end):
                # 新的logger对象（新的事务id）
                self.transaction_id = sundry.get_transaction_id()
                self.logger = log.Log(self.transaction_id)
                print(f'\n======*** Start working for ID {i} ***======')
                self._storage(i, args.uniq_str)
                self._vplx_drbd(i, args.uniq_str)
                self._vplx_crm(i, args.uniq_str)
                time.sleep(1.5)
                self._host_test(i)
        else:
            self.logger.write_to_log('INFO','info','','print_help')
            self.parser.print_help()


if __name__ == '__main__':
    w = HydraArgParse()
    w.run()
