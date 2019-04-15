#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function

import argparse
import os
import re
from time import time as timestamp
from collections import defaultdict

from config import ConfigData
from utils import *

MD5_FILE = '.filesync'
IGNORE_FILE = '.fileignore'


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

        # 读取本地同步文件夹信息
        self._loadDir()

    def _loadDir(self):
        """
        读取.fileignore文件
        读取文件目录结构
        导出.filesync文件
        :return:
        """
        self.__loadIgnoreDFS(self.config.currentDir)
        self.__loadMD5DFS(self.config.currentDir)
        self._dumpMD5(self.config.currentDir)

    def __loadIgnoreDFS(self, curDir):
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
                self.__loadIgnoreDFS(fullPath)

    def __loadMD5DFS(self, curDir):
        if curDir[-1] != '/':
            curDir += '/'

        for filename in os.listdir(curDir):
            # 检查是否忽略
            if self.__isIgnore(filename, curDir):
                continue

            fullPath = os.path.join(curDir, filename)
            if os.path.isdir(fullPath):
                self.__loadMD5DFS(fullPath)
            else:
                newMd5 = file2md5(fullPath)
                time = timestamp()
                self.file2md5time[fullPath] = (newMd5, time)

    def __isIgnore(self, i, dir):
        ignore = False
        for exp in self.ignoreExp[dir]:
            if re.match(exp, i):
                ignore = True
                break
        return ignore

    def _dumpMD5(self, path):
        if path[-1] != '/':
            path += '/'

        md5FilePath = os.path.join(path, MD5_FILE)
        data = [(fileName, md5, time) for fileName, (md5, time) in self.file2md5time.iteritems()]
        content = '\n'.join(['|'.join(map(str, i)) for i in sorted(data, key=lambda x:x[0])])
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
        pass

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
                            choices=['synchronize', 'echo'],
                            help='synchronize mode',
                            default='echo')

        args = parser.parse_args()

        confFile = args.config_file
        mode = args.mode

        fileSync = FileSync(confFile, mode)
        fileSync.run()
