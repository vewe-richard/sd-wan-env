import subprocess
import vdevs.basevdev


class vSwitch(vdevs.basevdev.BasevDev):
    def __init__(self, name):
        self._name = name
        self._ifs = set()

    def start(self):
        try:
            self.access(self._name)
        except vdevs.basevdev.ExceptionNotExist:
            self.create(self._name)

        #patch, iptable forward rule will affect bridge performs
        exist = False
        sp = subprocess.run(["iptables", "-L", "FORWARD", "-v", "--line-numbers"], stdout=subprocess.PIPE)
        lines = sp.stdout.splitlines()
        for line in reversed(lines):
            lstr = line.decode()
            if self._name in lstr and "ACCEPT" in lstr:
                exist = True
        if not exist:
            subprocess.run(["iptables", "-A", "FORWARD", "-i", self._name, "-j", "ACCEPT"])
            subprocess.run(["iptables", "-A", "FORWARD", "-o", self._name, "-j", "ACCEPT"])
        #patch, the bridge interface should be up
        subprocess.run(["ip", "link", "set", self._name, "up"])
        pass

    def remove(self):
        sp = subprocess.run(["ip", "link", "show", self._name, "type", "bridge"])
        if sp.returncode == 0:
            sp = subprocess.run(["ip", "link", "delete", self._name, "type", "bridge"])

        sp = subprocess.run(["iptables", "-L", "FORWARD", "--line-numbers", "-v"], stdout = subprocess.PIPE)
        lines = reversed(sp.stdout.splitlines())
        for line in lines:
            if self._name in line.decode():
                id = (line.decode().split()[0])
                subprocess.run(["iptables", "-D", "FORWARD", id])
        pass

    def addintf(self, intf):
        if len(self._ifs) == 0:
            self.access(self._name)
        if intf in self._ifs:
            return
        sp = subprocess.run(["brctl", "addif", self._name, intf])
        if sp.returncode != 0:
            raise Exception("can not add interface to bridge")
        subprocess.run(["ifconfig", intf, "up"])
        self._ifs.add(intf)
        pass

    def getintfs(self):
        return self._ifs

# inner
    def create(self, name):
        sp = subprocess.run(["ip", "link", "add", name, "type", "bridge"])
        pass

    def access(self, name):
        sp = subprocess.run(["ip", "link", "show", name, "type", "bridge"])
        if sp.returncode != 0:
            raise vdevs.basevdev.ExceptionNotExist
        sp = subprocess.run(["brctl", "show", name], stdout=subprocess.PIPE)
        lines = sp.stdout.splitlines()
        self._ifs = set()
        for line in lines[1:]:
            items = line.split()
            if len(items) == 4:
                self._ifs.add(items[3].decode())
            elif len(items) == 1:
                self._ifs.add(items[0].decode())
        pass

