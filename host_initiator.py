# coding:utf-8

import connect as c

class HostTest():
    def __init__(self, unique_id):
        self.ssh = _ssh_instance()
        self.id = unique_id
        


    def _ssh_instance(self):
        return c.ConnSSH(host,port,user,password,timeout)

    def _list_to_dict(self, arg_list):
        '''
        convert :
        [('0', '/dev/sdb'), ('1', '/dev/sdc')]
        to :
        {'0':'/dev/sdb', '1':'/dev/sdc')}
        '''
        dic = {}
        for i in arg_list:
            dic[i[0]] = i[i]
        return dic

    def _find_device(self, command_result):
        re_find_id_dev = re.compile(r'\:(\d*)\].*LIO-ORG[ 0-9a-zA-Z.]*(/dev/sd[a-z]{1,3})')
        re_result = re_find_id_dev.findall(command_result)
        # [('0', '/dev/sdb'), ('1', '/dev/sdc')]
        if re_result:
            dic_result = self._list_to_dict(re_result)
            if str(self.id) in dic_result.keys():
                dev_path = dic_result[str(self.id)]
                return dev_path

    def explore_disk(self):
        if self.ssh.excute_command('/usr/bin/rescan-scsi-bus.sh'):
            lsscsi_result = self.ssh.excute_command('lsscsi')
            if lsscsi_result and lsscsi_result not True:
                dev_path = self._find_device(lsscsi_result)
                if dev_path:
                    return dev_path
                else:
                    print("don't find the new LUN from VersaPLX")
                    sys.exit()
            else:
                print("command 'lsscsi' failed")
                sys.exit()
        else:
            print('scan failed')
            sys.exit()

    def format_mount(self):
        dev_name = self.explore_disk()
        mount_point = '/mnt'
        format_cmd = f'mkfs.ext4 {dev_name} -F'
        cmd_result = self.ssh.excute_command(format_cmd)
        # 'information: done' means that format completly
        if 'information: done' in cmd_result.decode():
            mount_cmd = f'mount {dev_name} {mount_point}'
            if self.ssh.excute_command(mount_cmd) == True:
                return True
            else:
                print(f"mount {dev_name} to {mount_point} failed")
                sys.exit()
        else:
            print("format disk %s failed" % dev_name)
            sys.exit()

    def _get_dd_perf(self, arg_str):
        re_performance = re.compile(r'*, ([1-9.]*) MB/s')
        re_result = re_performance.match(arg_str)
        perf = re_result.group()
        return perf

    def write_test(self):
        test_cmd = f'dd if=/dev/zero of={mount_point}/t.dat bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        if test_result:
            return self._get_dd_perf(test_result)
        
    def read_test(self):
        test_cmd = f'dd if={mount_point}/t.dat of=/dev/zero bs=512k count=16'
        test_result = self.ssh.excute_command(test_cmd)
        if test_result:
            return self._get_dd_perf(test_result)
