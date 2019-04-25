#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function
from watchdog.events import FileSystemEventHandler

from utils import *

import threading
from time import sleep


# todo 从salve端发送更新请求 & 自身请求

class SyncHandler(FileSystemEventHandler):
    """
    对各种事件的处理：增、改、删、文件移动
    echo模式更新md5，同步。如果是.fileignore文件则更新ignore规则。sync模式则在更新md5前和
    远端确认下版本。
    """

    def __init__(self, fileSync):
        self.conf = fileSync.config
        self.mode = fileSync.mode
        self.timeCycle = fileSync.time_cycle

        self.fileSync = fileSync

        self.__jobs = {}  # {path:(func,args)}

        def thread_cycle():
            while not self.fileSync.quit:
                sleep(self.timeCycle)
                # 询问远端

                # 最好此时可以锁定所有文件
                while self.__jobs:
                    path, (func, args) = self.__jobs.popitem()
                    func(*args)

        self.__exeThread = threading.Thread(target=thread_cycle)
        self.__exeThread.start()

    def doFileSync(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath):
            return

        # 更新ignore规则
        if os.path.basename(srcPath) == self.fileSync.IGNORE_FILE:
            self.fileSync.updateIgnore(os.path.dirname(srcPath))
            return

        if self.fileSync.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed, oldMd5, oldTime = self.fileSync.updateMD5(srcPath)
        if changed:
            # 同步
            if self.mode == self.fileSync.MODE_ECHO:
                doScp(srcPath, self.conf)
            elif self.mode == self.fileSync.MODE_SYNCHRONIZE:
                newMd5, newTime = self.fileSync.file2md5time[srcPath]

                dstPath = getRemotePath(srcPath, self.conf.currentDir, self.conf.remoteDir)
                server = create_server(self.conf.ssh_host, self.fileSync.rpc_port)
                remoteMd5, remoteTime = get_md5_time(
                    dstPath, server)

                if remoteMd5 is None:
                    # the remote file does not exist
                    doScp(srcPath, self.conf)
                elif remoteMd5 == newMd5:
                    # do nothing
                    return
                elif remoteMd5 == oldMd5:
                    # copy to remote
                    doScp(srcPath, self.conf)
                else:
                    # the newer version get copied
                    if remoteTime < newTime:
                        doScp(srcPath, self.conf)
                    else:
                        doScp(dstPath, self.conf, get=True)
            else:
                raise Exception("unsupported mode")

            # 更新md5文件
            self.fileSync.dumpMD5()

        return None

    def doFileDelete(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath):
            return

        # 更新ignore规则
        if os.path.basename(srcPath) == self.fileSync.IGNORE_FILE:
            self.fileSync.updateIgnore(os.path.dirname(srcPath))
            return

        if self.fileSync.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed, oldMd5, oldTime = self.fileSync.updateMD5(srcPath)
        if changed:
            # 同步
            dstPath = getRemotePath(srcPath, self.conf.currentDir, self.conf.remoteDir)

            if self.mode == self.fileSync.MODE_ECHO:
                strcmd = "rm -f {0}".format(dstPath)
                doRemoteCmd(self.conf, strcmd, printOut=True)
            elif self.mode == self.fileSync.MODE_SYNCHRONIZE:
                server = create_server(self.conf.ssh_host, self.fileSync.rpc_port)
                remoteMd5, remoteTime = get_md5_time(
                    dstPath, server)

                if remoteMd5 is None:
                    # the remote file does not exist
                    return
                elif remoteMd5 == oldMd5:
                    # delete remote
                    strcmd = "rm -f {0}".format(dstPath)
                    doRemoteCmd(self.conf, strcmd, printOut=True)
                else:
                    # copy from remote
                    doScp(dstPath, self.conf, get=True)
            else:
                raise Exception("unsupported mode")

            # 更新md5文件
            self.fileSync.dumpMD5()
        return None

    def dispatch(self, event):
        super(SyncHandler, self).dispatch(event)

    def on_any_event(self, event):
        super(SyncHandler, self).on_any_event(event)
        a = list(event.key)
        a[2] = '/' if a[2] else ''
        print('{} : event "{}" in {}{}'.format(datetime.datetime.now(), *tuple(a)))

    def on_created(self, event):
        """
        新建文件
        echo： 直接同步到远端，更新本地md5文件（对文件夹不做反应）
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        self.__jobs[event.src_path] = (self.doFileSync, (event.src_path,))

    def on_modified(self, event):
        """
        修改文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        self.__jobs[event.src_path] = (self.doFileSync, (event.src_path,))

    def on_deleted(self, event):
        """
        删除文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        # self.doFileDelete(event.src_path)
        self.__jobs[event.src_path] = (self.doFileDelete, (event.src_path,))

    def on_moved(self, event):
        """
        移动文件
        echo： 直接同步到远端，更新本地md5文件
        sync： 检查远端同名文件版本是否与原版本相同，相同则同步，不同则取较新的同步
        :param event:
        :return:
        """
        self.__jobs[event.src_path] = (self.doFileDelete, (event.src_path,))
        self.__jobs[event.dest_path] = (self.doFileSync, (event.dest_path,))
