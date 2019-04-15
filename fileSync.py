#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function

import argparse
import os
import re
import xmlrpclib
from time import time as timestamp
from collections import defaultdict

import slave
from config import ConfigData
from utils import *

INFO_DIR = '.filesync/'
MD5_FILE = 'md5'
IGNORE_FILE = '.fileignore'

MODE_ECHO = 'echo'
MODE_SYNCHRONIZE = 'synchronize'


class FileSync:

    def __init__(self, configFileName, mode):
        # 同步模式
        self.mode = mode

        # 符合条件的路径会被排除   {dir:[re]}
        self.ignoreExp = defaultdict(list)

        # 文件对应的修改时间和md5   {file:(md5,time)}
        self.file2md5time = {}

        # 读取配置文件
        self.config = ConfigData(configFileName)

        # 建立存放同步用数据的文件夹
        self.infoDir = os.path.join(self.config.currentDir, INFO_DIR)
        if not os.path.exists(self.infoDir):
            os.makedirs(self.infoDir)

        self.remoteInfoDir = os.path.join(self.config.remoteDir, INFO_DIR)

        # 读取本地同步文件夹信息
        self._loadDir()

    def _loadDir(self):
        """
        读取.fileignore文件
        读取文件目录结构
        导出.filesync文件
        :return:
        """
        self.__loadIgnore(self.config.currentDir)
        self.__loadMD5(self.config.currentDir)
        self._dumpMD5(self.infoDir)

    def __loadIgnore(self, curDir):
        if curDir[-1] != '/':
            curDir += '/'

        fileNames = os.listdir(curDir)

        if IGNORE_FILE in fileNames:
            ignoreFile = os.path.join(curDir, IGNORE_FILE)
            with open(ignoreFile, 'r') as f:
                exps = f.read().split('\n')

            for exp in map(str.strip, exps):
                try:
                    re.compile(exp)  # 测试表达式
                    self.ignoreExp[curDir].append(exp)
                    # 无法处理 修改.fileignore事件 故取消预编译设计
                    # self.exceptRegularExp.append(exp_compiled)
                except:
                    print(traceback.format_exc())

        for filename in os.listdir(curDir):
            fullPath = os.path.join(curDir, filename)
            if os.path.isdir(fullPath):
                self.__loadIgnore(fullPath)

    def __DFSIncludedFile(self, curDir, fun):
        if curDir[-1] != '/':
            curDir += '/'

        for filename in os.listdir(curDir):
            # 检查是否忽略
            if self.__isIgnore(filename, curDir):
                continue

            fullPath = os.path.join(curDir, filename)
            if os.path.isdir(fullPath):
                self.__DFSIncludedFile(fullPath, fun)
            else:
                fun(fullPath)

    def __loadMD5(self, curDir):
        def fun(fullPath):
            newMd5 = file2md5(fullPath)
            time = timestamp()
            self.file2md5time[fullPath] = (newMd5, time)

        self.__DFSIncludedFile(curDir, fun)

    def __isIgnore(self, i, path):
        if i == INFO_DIR[:-1]:
            return False

        ignore = False
        for exp in self.ignoreExp[path]:
            if re.match(exp, i):
                ignore = True
                break
        return ignore

    def _dumpMD5(self, path):
        if path[-1] != '/':
            path += '/'

        md5FilePath = os.path.join(path, MD5_FILE)
        data = [(fileName, md5, time) for fileName, (md5, time) in self.file2md5time.iteritems()]
        content = '\n'.join(['|'.join(map(str, i)) for i in sorted(data, key=lambda x: x[0])])
        with open(md5FilePath, 'w') as f:
            f.write(content)

    def _init(self):
        """
        初始化
        将slave发送到对应目录下并运行
        echo mode 检查文件夹是否为空并询问是否删除，结束
        synchronize mode 检查文件夹是否为空并询问是否删除，开始运行
        :return:
        """

        TEMP_DIR = '/tmp/filesync/'

        # 传输slave脚本并运行
        # slaveDest = os.path.join(self.remoteInfoDir, 'slave.py')
        slaveDest = os.path.join(TEMP_DIR, 'slave.py')
        scp('./slave.py', slaveDest, self.config)  # 需要添加故障检测？
        # slaveLog = os.path.join(self.remoteInfoDir, 'slave.log')
        slaveLog = os.path.join(TEMP_DIR, 'slave.log')
        cmd = 'nohup python %s --mode %s 1>%s 2>&1 &'
        doRemoteCmd(self.config, cmd % (slaveDest, self.mode, slaveLog))

        # check if the remote directory exists
        server = xmlrpclib.ServerProxy(
            "http://%s:%d/" % (self.config.ssh_host, slave.PORT))
        code = server.check_path(self.config.remoteDir)
        if code == slave.CODE_DIR_EMPTY:
            print('remote directory is empty\nstart sync now...')
        elif code == slave.CODE_DIR_NOT_EMPTY:
            print('remote directory %s is NOT empty!' % self.config.remoteDir)
            agree = getAnswer('delete all before sync? y/n')
            if agree:
                doRemoteCmd(self.config, 'rm %s -rf' % self.config.remoteDir)
            else:
                exit(0)
        elif code == slave.CODE_FILE_EXIST:
            print('remote directory name conflicts with an existing file!')
            exit(1)
        else:
            print('can not understand return code')
            exit(1)
        server.close_server()

        # create remore infoDir
        cmd = "mkdir -p %s" % self.remoteInfoDir
        doRemoteCmd(self.config, cmd, printOut=True)

        # scp all included file
        self.__DFSIncludedFile(self.config.currentDir,
                               lambda path: doScp(path, self.config))

        if mode == MODE_ECHO:
            pass
        elif mode == MODE_SYNCHRONIZE:
            # todo
            print('unsupported')
            exit(1)

    def _run(self):
        """
        开始监听本地动作
        :return:
        """
        pass

    def run(self):
        self._init()
        self._run()


if __name__ == '__main__':
    if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument('--config_file', help='path/to/config/file', default='./conf.xml')
        parser.add_argument('--mode',
                            choices=[MODE_SYNCHRONIZE, MODE_ECHO],
                            help='synchronize mode',  # todo
                            default=MODE_ECHO)

        args = parser.parse_args()

        confFile = args.config_file
        mode = args.mode

        fileSync = FileSync(confFile, mode)
        fileSync.run()
