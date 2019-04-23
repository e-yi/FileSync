#!/usr/bin python
# -*- coding:utf-8 -*-

"""
echo mode 检查文件夹是否为空并询问是否删除，结束
synchronize mode 检查文件夹是否为空并询问是否删除，开始运行
"""
from __future__ import print_function

import argparse
import os
import re
import hashlib
import traceback
from SimpleXMLRPCServer import SimpleXMLRPCServer
from collections import defaultdict
from time import sleep
from time import time as timestamp

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

PORT = 8081
CODE_FILE_EXIST = 0
CODE_DIR_NOT_EMPTY = 1
CODE_DIR_EMPTY = 2


def checkPath(path):
    if os.path.exists(path):
        if not os.path.isdir(path):
            return CODE_FILE_EXIST
        if os.listdir(path):
            return CODE_DIR_NOT_EMPTY
        else:
            return CODE_DIR_EMPTY
    os.makedirs(path)
    return CODE_DIR_EMPTY


__doQuit = False


def close():
    global __doQuit
    __doQuit = True
    return True


def file2md5(filename):
    md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(128), ""):
            md5.update(block)
    return md5.hexdigest()


class SyncHandlerSlave(FileSystemEventHandler):
    """
    对各种事件的处理：增、改、删、文件移动
    echo模式更新md5，同步。如果是.fileignore文件则更新ignore规则。sync模式则在更新md5前和
    远端确认下版本。
    """

    def __init__(self, mode, fileSyncSlave):
        self.mode = mode
        self.fileSyncSlave = fileSyncSlave

    def doFileSync(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath):
            return

        # 更新ignore规则
        if os.path.basename(srcPath) == self.fileSyncSlave.IGNORE_FILE:
            self.fileSyncSlave.updateIgnore(os.path.dirname(srcPath))
            return

        if self.fileSyncSlave.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed = self.fileSyncSlave.updateMD5(srcPath)
        if changed:
            # 更新md5文件
            self.fileSyncSlave.dumpMD5()

        return None

    def doFileDelete(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath):
            return

        # 更新ignore规则
        if os.path.basename(srcPath) == self.fileSyncSlave.IGNORE_FILE:
            self.fileSyncSlave.updateIgnore(os.path.dirname(srcPath))
            return

        if self.fileSyncSlave.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed = self.fileSyncSlave.updateMD5(srcPath)
        if changed:
            # 更新md5文件
            self.fileSyncSlave.dumpMD5()

        return None

    def dispatch(self, event):
        super(SyncHandlerSlave, self).dispatch(event)

    def on_any_event(self, event):
        super(SyncHandlerSlave, self).on_any_event(event)

    def on_created(self, event):
        """
        新建文件
        echo： 直接同步到远端，更新本地md5文件（对文件夹不做反应）
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        print(event.key)
        self.doFileSync(event.src_path)

    def on_modified(self, event):
        """
        修改文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        print(event.key)
        self.doFileSync(event.src_path)

    def on_deleted(self, event):
        """
        删除文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        print(event.key)
        self.doFileDelete(event.src_path)

    def on_moved(self, event):
        """
        移动文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        print(event.key)
        self.doFileDelete(event.src_path)
        self.doFileSync(event.dest_path)


class FileSyncSlave:
    IGNORE_FILE = '.fileignore'
    INFO_DIR = '.filesync/'
    MD5_FILE = 'md5'

    MODE_ECHO = 'echo'
    MODE_SYNCHRONIZE = 'synchronize'

    def __init__(self, mode, time_cycle, working_dir):
        print('init slave...')

        # 修改工作目录到上一级
        self.currentDir = os.path.abspath(working_dir)
        print('curDir = %s' % self.currentDir)
        os.chdir(working_dir)

        # 同步模式
        self.mode = mode
        print('mode = %s' % self.mode)

        # 同步时间
        self.time_cycle = time_cycle
        print('time_cycle = %s' % time_cycle)

        # 符合条件的路径会被排除   {dir:[re]}
        self.ignoreExp = defaultdict(list)

        # 文件对应的修改时间和md5   {file:(md5,time)}
        self.file2md5time = {}

        # 建立存放同步用数据的文件夹
        self.infoDir = os.path.join(self.currentDir, self.INFO_DIR)

        # 读取本地同步文件夹信息
        self._loadDir()

    def _loadDir(self):
        """
        读取.fileignore文件
        读取文件目录结构
        导出.filesync文件
        :return:
        """
        self.__updateDirIgnore(self.currentDir)
        self.__updateDirMD5(self.currentDir)
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

        oldMd5 = self.file2md5time.get(fullPath, None)

        if not os.path.exists(fullPath):
            if oldMd5 is None:
                return False
            else:
                del self.file2md5time[fullPath]
                return True

        newMd5 = file2md5(fullPath)
        if oldMd5 != newMd5:
            time = timestamp()
            self.file2md5time[fullPath] = (newMd5, time)
            return True

        return False

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

            if curDir == self.currentDir:
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

    def _run(self):
        """
        开始监听本地动作
        :return:
        """
        import threading

        # do sync on modify
        event_handler = SyncHandlerSlave(self.mode, self)
        observer = Observer()
        observer.schedule(event_handler, path=self.currentDir, recursive=True)
        observer.start()

        print("\n----watchdog start working----\n")

        def work():
            try:
                while True:
                    sleep(self.time_cycle)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        t = threading.Thread(target=work)
        t.start()

    def run(self):
        return self._run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--working_dir',
                        help='remote directory ,only working in synchronize mode',
                        default='../')
    parser.add_argument('--time_cycle', help='time interval between two synchronizations',
                        default=10, type=int)
    parser.add_argument('--mode',
                        choices=[FileSyncSlave.MODE_SYNCHRONIZE, FileSyncSlave.MODE_ECHO],
                        help='choose filesyncSlave mode',
                        default=FileSyncSlave.MODE_ECHO)

    args = parser.parse_args()
    server = SimpleXMLRPCServer(("0.0.0.0", PORT), allow_none=True)
    print("start remote service on 0.0.0.0 8081...")

    if args.mode == FileSyncSlave.MODE_ECHO:
        pass
    elif args.mode == FileSyncSlave.MODE_SYNCHRONIZE:
        fileSyncSlave = FileSyncSlave(args.mode, args.time_cycle, args.working_dir)
        fileSyncSlave.run()
        server.register_function(
            lambda fullPath: fileSyncSlave.file2md5time.get(fullPath, (None, None)),
            'get_md5_time')
        server.register_function(lambda: fileSyncSlave.file2md5time, 'get_md5_time_all')

    server.register_function(checkPath, "check_path")
    server.register_function(close, 'close_server')
    while not __doQuit:
        server.handle_request()
    print("end remote service on 0.0.0.0 8081...")
