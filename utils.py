#!/usr/bin python
# -*- coding:utf-8 -*-
from __future__ import print_function

import datetime
import hashlib
import os
import xmlrpclib

import paramiko


# -------- ssh -----------

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
    print("{0} : {1}".format(datetime.datetime.now(), strcmd))
    stdin, stdout, stderr = ssh.exec_command(strcmd)
    if printOut:
        print(stdout.read(), end='')
        print(stderr.read(), end='')
        return None
    return stdin, stdout, stderr


def doScp(srcPath, cnf, get=False):
    srcPath = os.path.abspath(srcPath)
    # print("srcPath : {0}".format(srcPath))
    srcFile = os.path.relpath(srcPath, cnf.currentDir)
    dstPath = os.path.join(cnf.remoteDir, srcFile)

    if get:
        srcPath, dstPath = dstPath, srcPath

    print("{0} : {1}  -->  {2}".format(datetime.datetime.now(), srcPath, dstPath))

    ssh = getSSHInstance(cnf)
    strcmd = "mkdir -p {0}".format(os.path.split(dstPath)[0])
    # print strcmd
    stdin, stdout, stderr = ssh.exec_command(strcmd)
    print(stdout.read(), end='')
    print(stderr.read(), end='')
    sftp = ssh.open_sftp()
    if get:
        sftp.get(srcPath, dstPath)
    else:
        sftp.put(srcPath, dstPath)
    ssh.close()

    return None


def sftp_put(srcPath, dstPath, cnf):
    ssh = getSSHInstance(cnf)
    sftp = ssh.open_sftp()
    sftp.put(srcPath, dstPath)
    ssh.close()


# -------- RPC ----------

def check_path(path, host, port):
    server = xmlrpclib.ServerProxy(
        "http://%s:%s/" % (host, str(port)))
    code = server.check_path(path)
    server.close_server()
    return code


def get_md5_time(path, host, port):
    server = xmlrpclib.ServerProxy(
        "http://%s:%s/" % (host, str(port)))
    md5, time = server.get_md5_time(path)
    server.close_server()
    return md5, time


# -------- others --------

def file2md5(filename):
    md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(128), ""):
            md5.update(block)
    return md5.hexdigest()


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


def getRemotePath(srcPath, currentDir, remoteDir):
    srcFile = os.path.relpath(srcPath, currentDir)
    dstFile = os.path.join(remoteDir, srcFile)
    return dstFile
