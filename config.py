import os


class ConfigData:
    """
    load & store config data
    """

    def __init__(self, _fileName):
        self.fileName = _fileName
        self.docTree = None

        self.ssh_host = None
        self.ssh_port = None
        self.ssh_user = None
        self.ssh_passwd = None
        self.currentDir = None
        self.remoteDir = None

        self.getConfigFromFile()

        self.testConfig()

    def show(self):
        print("-------------------")
        print(''.join([self.ssh_user, "@", str(self.ssh_host), ':', str(self.ssh_port)]))
        # print(self.ssh_passwd)
        print('localDir:', self.currentDir)
        print('remoteDir:', self.remoteDir)
        print("-------------------")

    def getSectionText(self, path):
        retText = ""
        if self.docTree:
            objTmp = self.docTree.find(path)
            if objTmp is not None:
                retText = objTmp.text or ""
        return retText

    def getSectionInt(self, path):
        strTmp = self.getSectionText(path).strip()
        return int(strTmp) if strTmp.isdigit() else 0

    def getConfigFromFile(self):
        try:
            import xml.etree.cElementTree as ET
        except ImportError:
            import xml.etree.ElementTree as ET
        if not os.path.exists(self.fileName):
            print("config file ", self.fileName, " not exists")
            exit(1)
        try:
            self.docTree = ET.ElementTree(file=self.fileName)
        except Exception as e:
            print("%s is NOT well-formed : %s " % (self.fileName, e))
            exit(1)

        self.ssh_host = self.getSectionText("host").strip()
        self.ssh_port = self.getSectionInt("sshPort")
        self.ssh_user = self.getSectionText("user").strip()
        self.ssh_passwd = self.getSectionText("password").strip()
        self.currentDir = self.getSectionText("localDir").strip()
        self.currentDir = os.path.abspath(self.currentDir)
        self.remoteDir = self.getSectionText("remoteDir").strip()
        return None

    def testConfig(self):
        pass  # todo
