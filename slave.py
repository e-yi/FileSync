#!/usr/bin python
# -*- coding:utf-8 -*-

"""
echo mode 检查文件夹是否为空并询问是否删除，结束
synchronize mode 检查文件夹是否为空并询问是否删除，开始运行
"""

from SimpleXMLRPCServer import SimpleXMLRPCServer
import os

FILE_EXIST = 0
DIR_NOT_EMPTY = 1
DIR_EMPTY = 2


def checkPath(path):
    if os.path.exists(path):
        if not os.path.isdir(path):
            return FILE_EXIST
        if os.listdir(path):
            return DIR_NOT_EMPTY
    os.makedirs(path)
    return DIR_EMPTY


server = SimpleXMLRPCServer(("0.0.0.0", 8081))
print "start service get power on 0.0.0.0 8081..."
server.register_function(checkPath, "check_path")
server.serve_forever()
