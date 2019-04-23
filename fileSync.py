#!/usr/bin python
# -*- coding:utf-8 -*-
"""
watchdog 使用了 inotify

"""

from __future__ import print_function

import argparse
import re
import traceback
from collections import defaultdict
from time import sleep

from watchdog.observers import Observer

import slave
from config import ConfigData
from syncHandler import SyncHandler
from utils import *


class FileSync:
    INFO_DIR = '.filesync/'
    MD5_FILE = 'md5'
    IGNORE_FILE = '.fileignore'

    MODE_ECHO = 'echo'
    MODE_SYNCHRONIZE = 'synchronize'

    def __init__(self, configFileName, mode, time_cycle, d):
        # 同步模式
        self.mode = mode

        # 自动同步时间
        self.time_cycle = time_cycle

        # 自动在同步前清空远端文件夹
        self.autoDelete = d

        # RPC 端口
        self.rpc_port = slave.PORT

        # 符合条件的路径会被排除   {dir:[re]}
        self.ignoreExp = defaultdict(list)

        # 文件对应的修改时间和md5   {file:(md5,time)}
        self.file2md5time = {}

        # 读取配置文件
        self.config = ConfigData(configFileName)
        self.config.show()

        # 建立存放同步用数据的文件夹
        self.infoDir = os.path.join(self.config.currentDir, self.INFO_DIR)
        if not os.path.exists(self.infoDir):
            os.makedirs(self.infoDir)

        self.remoteInfoDir = os.path.join(self.config.remoteDir, self.INFO_DIR)

        # 读取本地同步文件夹信息
        self._loadDir()

    def _loadDir(self):
        """
        读取.fileignore文件
        读取文件目录结构
        导出.filesync文件
        :return:
        """
        self.__updateDirIgnore(self.config.currentDir)
        self.__updateDirMD5(self.config.currentDir)
        self.dumpMD5(self.infoDir)

    def updateIgnore(self, curDir):
        """
        读取`curDir`路径下的.fileignore文件
        当文件不存在时，删除`self.ignoreExp`中对应键值对
        :param curDir:
        :return:
        """
        changed = False

        ignoreFile = os.path.join(curDir, self.IGNORE_FILE)

        if not os.path.exists(ignoreFile):
            if not self.ignoreExp[curDir]:
                return False
            else:
                del self.ignoreExp[curDir]
                return True

        with open(ignoreFile, 'r') as f:
            exps = f.read().split('\n')

        exps.sort()  # 保证用户以不同顺序写的两组相同表达式不会影响`changed`变量

        oldExps = self.ignoreExp.get(curDir, [])

        newExps = []
        for exp in map(str.strip, exps):
            try:
                re.compile(exp)  # 测试表达式
                newExps.append(exp)  # 无法处理 修改.fileignore事件 故取消预编译设计
            except:
                print(traceback.format_exc())

        if newExps != oldExps:  # 这里的比较是逐元素比较
            self.ignoreExp[curDir] = newExps
            changed = True

        return changed

    def __updateDirIgnore(self, curDir):
        """
        DFS文件路径，读取所有的.fileignore文件
        :param curDir:
        :return:
        """
        if curDir[-1] != '/':
            curDir += '/'

        fileNames = os.listdir(curDir)

        if self.IGNORE_FILE in fileNames:
            self.updateIgnore(curDir)

        for filename in os.listdir(curDir):
            fullPath = os.path.join(curDir, filename)
            if os.path.isdir(fullPath):
                self.__updateDirIgnore(fullPath)

    def __DFSIncludedFile(self, curDir, fun):
        """
        辅助函数DFS遍历未被忽略的函数
        :param curDir:
        :param fun: function(fullPath):void
        :return:
        """
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

    def updateMD5(self, fullPath):
        """
        当md5变化时，文件粒度更新`self.file2md5time`
        当文件不存在时，删除`self.file2md5time`中对应键值对
        :param fullPath:
        :return: bool 是否更新了self.file2md5time
        """

        oldMd5, oldTime = self.file2md5time.get(fullPath, (None, None))

        if not os.path.exists(fullPath):
            if oldMd5 is None:
                return False, oldMd5, oldTime
            else:
                del self.file2md5time[fullPath]
                return True, oldMd5, oldTime

        newMd5 = file2md5(fullPath)
        if oldMd5 != newMd5:
            time = os.stat(fullPath).st_mtime  # 文件修改时间 时间戳
            self.file2md5time[fullPath] = (newMd5, time)
            return True, oldMd5, oldTime

        return False, oldMd5, oldTime

    def __updateDirMD5(self, curDir):
        """
        文件夹粒度更新md5
        :param curDir:
        :return:
        """
        self.__DFSIncludedFile(curDir, self.updateMD5)

    def __isIgnore(self, fileName, parentDir):
        """
        检查一个文件是否符合忽略规则
        !!!无法检测祖先文件夹是否被忽略，在此情况下失效
        :param fileName:
        :param parentDir:
        :return:
        """
        if fileName == self.INFO_DIR[:-1] or fileName == self.IGNORE_FILE:
            return True
        assert parentDir[-1] == '/'

        ignore = False
        # if not self.ignoreExp[parentDir] : skip for loop
        for exp in self.ignoreExp[parentDir]:
            if re.match(exp, fileName):
                ignore = True
                break
        return ignore

    def isIgnorePlus(self, fullPath):
        """
        检查一个文件是否符合忽略规则
        :param fullPath:
        :return:
        """
        curFile = os.path.basename(fullPath)
        curDir = os.path.dirname(fullPath) + '/'

        while True:
            ignore = self.__isIgnore(curFile, curDir)
            if ignore:
                return True

            if curDir == self.config.currentDir:
                break

            curFile = os.path.basename(curDir[:-1])
            curDir = os.path.dirname(curDir[:-1]) + '/'

        return False

    def dumpMD5(self, path=None):
        """
        将self.file2md5time中的数据导出到文件
        :param path:
        :return:
        """
        if not path:
            path = self.infoDir

        if path[-1] != '/':
            path += '/'

        md5FilePath = os.path.join(path, self.MD5_FILE)
        data = [(fileName, md5, time) for fileName, (md5, time) in self.file2md5time.iteritems()]
        content = '\n'.join(['|'.join(map(str, i)) for i in sorted(data, key=lambda x: x[0])])
        with open(md5FilePath, 'w') as f:
            f.write(content)

    def _init(self):
        """
        初始化
        将slave发送到对应目录下并运行
        echo mode        检查文件夹是否为空并询问是否删除，结束
        synchronize mode 检查文件夹是否为空并询问是否删除，开始运行
        :return:
        """

        # 暂时存放slave.py的位置
        TEMP_DIR = '/tmp/filesync/'

        # create remore TEMP_DIR
        cmd = "mkdir -p %s" % TEMP_DIR
        doRemoteCmd(self.config, cmd, printOut=True)

        # 传输slave脚本并运行
        # slaveDest = os.path.join(self.remoteInfoDir, 'slave.py')
        slaveDest = os.path.join(TEMP_DIR, 'slave.py')
        sftp_put('./slave.py', slaveDest, self.config)  # 需要添加故障检测？
        # slaveLog = os.path.join(self.remoteInfoDir, 'slave.log')
        slaveLog = os.path.join(TEMP_DIR, 'slave.log')
        cmd = 'nohup python %s 1>%s 2>&1 &'  # no mode flag
        doRemoteCmd(self.config, cmd % (slaveDest, slaveLog))

        # check if the remote directory exists
        server = create_server(self.config.ssh_host, self.rpc_port)
        code = check_path(self.config.remoteDir, server)
        close_server(server)
        if code == slave.CODE_DIR_EMPTY:
            print('remote directory is empty')
        elif code == slave.CODE_DIR_NOT_EMPTY:
            print('remote directory %s is NOT empty!' % self.config.remoteDir)
            if self.autoDelete:
                agree = True
            else:
                agree = getAnswer('delete all before sync? y/n\n')
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

        print('\nstart sync now...\n')

        # create remore infoDir
        cmd = "mkdir -p %s" % self.remoteInfoDir
        doRemoteCmd(self.config, cmd, printOut=True)

        # scp all included file
        self.__DFSIncludedFile(self.config.currentDir,
                               lambda path: doScp(path, self.config))

        if self.mode == self.MODE_ECHO:
            pass
        elif self.mode == self.MODE_SYNCHRONIZE:
            self.__initSynchronize()

    def __initSynchronize(self):
        """
        将slave传到remoteInfoDir
        启动slave，建立远端md5文件，开始远端的本地监听，在本地要求同步时，提供对应文件的md5和时间标记
        todo 通信安全
        :return:
        """
        # 传输slave脚本并运行
        slaveDest = os.path.join(self.remoteInfoDir, 'slave.py')
        sftp_put('./slave.py', slaveDest, self.config)  # 需要添加故障检测？
        slaveLog = os.path.join(self.remoteInfoDir, 'slave.log')
        cmd = 'nohup python %s --mode %s --time_cycle %s --working_dir %s 1>%s 2>&1 &'
        doRemoteCmd(self.config, cmd % (slaveDest, self.mode, self.time_cycle,
                                        self.config.remoteDir, slaveLog))

    def _run(self):
        """
        开始监听本地动作
        :return:
        """
        # do sync on modify
        event_handler = SyncHandler(self.config, self.mode, self)
        observer = Observer()
        observer.schedule(event_handler, path=self.config.currentDir, recursive=True)
        observer.start()

        print("\n----watchdog start working----\n")

        try:
            while True:
                sleep(self.time_cycle)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        server = create_server(self.config.ssh_host,self.rpc_port)
        close_server(server)

    def run(self):
        self._init()
        self._run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_file', help='path/to/config/file', default='./conf.xml')
    parser.add_argument('--time_cycle', help='time interval between two synchronizations',
                        default=10, type=int)
    parser.add_argument('--mode',
                        choices=[FileSync.MODE_SYNCHRONIZE, FileSync.MODE_ECHO],
                        help='choose filesync mode',
                        default=FileSync.MODE_ECHO)
    parser.add_argument('-d', action='store_true',
                        help="auto delete existing files in remote directory")

    args = parser.parse_args()

    fileSync = FileSync(args.config_file, args.mode, args.time_cycle, args.d)
    fileSync.run()
