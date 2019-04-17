#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function

import datetime
import hashlib
import os

import paramiko
import traceback


def getSSHInstance(cnf):
    ssh = paramiko.SSHClient()
    # ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=cnf.ssh_host,
                port=cnf.ssh_port,
                username=cnf.ssh_user,
                password=cnf.ssh_passwd,
                timeout=5)
    return ssh


def doRemoteCmd(cnf, strcmd, printOut=False):
    ssh = getSSHInstance(cnf)
    print(strcmd)
    stdin, stdout, stderr = ssh.exec_command(strcmd)
    if printOut:
        print(stdout.read(), end='')
        print(stderr.read(), end='')
        return None
    return stdin, stdout, stderr


def file2md5(filename):
    md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(128), ""):
            md5.update(block)
    return md5.hexdigest()


def doScp(srcPath, cnf):
    srcPath = os.path.abspath(srcPath)
    # print("srcPath : {0}".format(srcPath))
    srcFile = os.path.relpath(srcPath, cnf.currentDir)
    dstFile = os.path.join(cnf.remoteDir, srcFile)
    # print dstFile
    print("{0},doScp : {1}->{2}".format(datetime.datetime.now(), srcPath, dstFile))

    ssh = getSSHInstance(cnf)
    strcmd = "mkdir -p {0}".format(os.path.split(dstFile)[0])
    # print strcmd
    stdin, stdout, stderr = ssh.exec_command(strcmd)
    print(stdout.read(), end='')
    print(stderr.read(), end='')
    sftp = ssh.open_sftp()
    sftp.put(srcPath, dstFile)
    ssh.close()

    return None


def scp(srcPath, dstPath, cnf):
    ssh = getSSHInstance(cnf)
    sftp = ssh.open_sftp()
    sftp.put(srcPath, dstPath)
    ssh.close()


def getAnswer(question):
    """
    要求用户用 y 或 n 回答问题
    :param question:
    :return:
    """
    while True:
        ans = raw_input(question)
        if ans == 'y':
            return True
        elif ans == 'n':
            return False
        else:
            continue
