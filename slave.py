#!/usr/bin python
# -*- coding:utf-8 -*-

"""
echo mode 检查文件夹是否为空并询问是否删除，结束
synchronize mode 检查文件夹是否为空并询问是否删除，开始运行
"""

from SimpleXMLRPCServer import SimpleXMLRPCServer
import os

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


doQuit = False


def close():
    global doQuit
    doQuit = True
    return True


server = SimpleXMLRPCServer(("0.0.0.0", PORT))
print "start service get power on 0.0.0.0 8081..."
server.register_function(checkPath, "check_path")
server.register_function(close, 'close_server')
while not doQuit:
    server.handle_request()

