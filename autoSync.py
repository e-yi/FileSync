#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function
import time
import datetime
import hashlib
import os
import posixpath
import re
import time

import argparse


from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


from config import ConfigData

MD5FILE = '.fileSync'













# todo 改成支持re的
class SyncHandler(FileSystemEventHandler):
    def __init__(self, conf):
        self.conf = conf

    def doFileSync(self, event):
        if not event.is_directory:
            srcFile = event.src_path
            srcFile = os.path.abspath(srcFile)
            doScp(srcFile, self.conf)
        return None

    def doFileDelete(self, event):
        try:
            if not event.is_directory:
                srcPath = os.path.abspath(event.src_path)
                srcFile = os.path.relpath(srcPath, self.conf.currentDir)
                dstFile = posixpath.join(self.conf.remoteDir, srcFile.replace(os.path.sep, posixpath.sep))
                print(dstFile)
                if dstFile:
                    strcmd = "rm -f {0}".format(dstFile)
                    doRemoteCmd(self.conf, strcmd)
        except:
            print("doFileDelete fail")
        return None

    def on_modified(self, event):
        print(event.key)
        self.doFileSync(event)

    def on_deleted(self, event):
        print(event.key)
        self.doFileDelete(event)

    def on_moved(self, event):
        print(event.key, "moved")
        self.doFileDelete(event)
        self.doFileSync(event)


parser = argparse.ArgumentParser()
parser.add_argument('--config_file', help='path/to/config/file', default='./conf.xml')
parser.add_argument('--mode',
                    choices=['synchronize', 'echo'],
                    help='synchronize mode',
                    default='echo')

args = parser.parse_args()

confFile = args.config_file
mode = args.mode

conf = ConfigData(confFile)
conf.show()

md5FilePath = os.path.join(conf.currentDir, MD5FILE)
conf.hashDict = {}

# 初始化
if os.path.exists(md5FilePath):
    with open(md5FilePath) as f:
        for _line in f:
            _path, _md5 = _line.split()
            conf.hashDict[_path] = _md5

# 初始化更新文件md5
for root, dirs, files in os.walk(conf.currentDir):
    for name in files:
        t_path = os.path.join(root, name)
        t_path = os.path.abspath(t_path)
        if t_path in conf.hashDict:
            t_md5 = conf.hashDict[t_path]
            n_md5 = file2md5(t_path)
            if t_md5 != n_md5:
                doScp(t_path, conf)
                conf.hashDict[t_path] = n_md5
            else:
                pass
        else:
            n_md5 = file2md5(t_path)
            doScp(t_path, conf)
            conf.hashDict[t_path] = n_md5

        conf.hashDict[t_path] = file2md5(t_path)
with open(md5FilePath, 'w') as f:
    for _path, _md5 in conf.hashDict.iteritems():
        f.write("%s %s\n" % (_path, _md5))

# do sync in start todo 支持断点重连
for root, dirs, files in os.walk(conf.currentDir):
    for name in files:
        t_path = os.path.join(root, name)
        t_path = os.path.abspath(t_path)
        print(t_path, name)
        # doScp(t_path, conf)

# do sync on modify
# event_handler = SyncHandler(conf)
# observer = Observer()
# observer.schedule(event_handler, path=conf.currentDir, recursive=True)
# observer.start()
#
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     observer.stop()
# observer.join()
