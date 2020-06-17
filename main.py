
#  coding: utf-8
import storage
import vplx
import host_initiator as host
import argparse
import sys


class HydraArgParse():
    '''
    Hydra project
    parse argument for auto max lun test program
    '''
    def __init__(self):
        self.argparse_init()

    def argparse_init(self):
        self.parser = argparse.ArgumentParser(prog='max_lun',
                                              description='test max lun number of VersaRAID-SDS')
        self.parser.add_argument(
            '-r',
            '--run',
            action="store_true",
            dest="run_test",
            help="run auto max lun test")
        self.parser.add_argument(
            '-s',
            '--string',
            action="store",
            dest="unique_str",
            help="the unique string for this test, affects related naming")

    def _storage(self, unique_id, unique_str):
        netapp = storage.Storage(unique_id, unique_str)
        netapp.lun_create()
        netapp.lun_map()

    def _vplx_drbd(self, unique_id, unique_str):
        drbd = vplx.VplxDrbd(unique_id, unique_str)
        drbd.prepare_config_file()
        drbd.drbd_cfg()
        

    def _vplx_crm(self, unique_id, unique_str):
        crm = vplx.VplxCrm(unique_id, unique_str)
        crm.iscisi_lun_create()
        crm.iscisi_lun_setting()
        crm.iscisi_lun_start()

    def _host_test(self, unique_id):
        host = host.HostTest(unique_id)
        ssh.excute_command('umount /mnt')
        mount_status = w.format_mount()
        if mount_status:
            write_perf = w.write_test()
            print(f'write speed: {write_perf}')
            time.sleep(1)
            read_perf = w.read_test()
            print(f'read speed: {read_perf}')
        else:
            print('mount failed')
            sys.exit()

    def run(self):
        args = self.parser.parse_args()
        if args.run_test:
            if args.unique_str:
                for i in range(255):
                    self._storage(i, args.unique_str)
                    self._vplx_drbd(i, args.unique_str)
                    self._vplx_crm(i, args.unique_str)
                    self._host_test(i)
            else:
                self.parser.print_help()
        else:
            self.parser.print_help()


if __name__ == '__main__':
    w = HydraArgParse()
    w.run()