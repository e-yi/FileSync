#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function

import os

from watchdog.events import FileSystemEventHandler


# todo 改成支持re的
from utils import *


class SyncHandler(FileSystemEventHandler):
    """
    对各种事件的处理：增、改、删、文件移动
    echo模式更新md5，同步。如果是.fileignore文件则更新ignore规则。sync模式则在更新md5前和
    远端确认下版本。
    """
    def __init__(self, conf, mode, fileSync):
        self.conf = conf
        self.mode = mode
        self.fileSync = fileSync  # todo 检查是否真的需要传一整个FileSync进来

    def doFileSync(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath) or \
                self.fileSync.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed = self.fileSync.updateMD5(srcPath)
        if changed:

            # 同步
            doScp(srcPath, self.conf)

            # 更新md5文件
            self.fileSync.dumpMD5()

            # 更新ignore规则
            if os.path.basename(srcPath) == self.fileSync.IGNORE_FILE:
                self.fileSync.updateIgnore(os.path.dirname(srcPath))

        return None

    def doFileDelete(self, src_path):
        srcPath = os.path.abspath(src_path)

        if os.path.isdir(srcPath) or \
                self.fileSync.isIgnorePlus(srcPath):
            return

        # 尝试更新md5规则
        changed = self.fileSync.updateMD5(srcPath)
        if changed:

            # 同步
            srcFile = os.path.relpath(srcPath, self.conf.currentDir)
            dstFile = os.path.join(self.conf.remoteDir, srcFile)
            if dstFile:
                strcmd = "rm -f {0}".format(dstFile)
                doRemoteCmd(self.conf, strcmd, printOut=True)

            # 更新md5文件
            self.fileSync.dumpMD5()

            # 更新ignore规则
            if os.path.basename(srcPath) == self.fileSync.IGNORE_FILE:
                self.fileSync.updateIgnore(os.path.dirname(srcPath))

        return None

    def dispatch(self, event):
        super(SyncHandler, self).dispatch(event)

    def on_any_event(self, event):
        super(SyncHandler, self).on_any_event(event)

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
