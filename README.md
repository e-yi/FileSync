# autoSync

auto sync directury to linux server

to remove CryptographyDeprecationWarning
use `pip install cryptography==2.4.2`


1.	模式
参考Microsoft SyncToy，提供echo和synchronize两种模式。
echo：主从模式，在主文件夹中新增加的和被改变的内容会被备份到远端文件夹中。在主端被重命名的文件以及被删除了的文件，将也会在远端的文件夹中删除。
synchronize：对等模式，在任意一端的任意变动都会更新到另一端*。

*：目前远端修改自动同步没有完成。

2.	冲突
当使用synchronize模式时，如果两边都在同步前修改了同一个文件，可能导致冲突，此时将保留修改时间较晚的文件。

3.	时间
使用Unix时间戳进行同步。

4.	ignore
类似git的.gitignore文件，可以在某目录下建立.fileignore文件存放同步中忽略的文件名的正则表达式。

5.	初始化
读取xml格式的配置文件进行初始化。在初始化时，使用ssh连接远端机器，检查并配置环境*，之后将传输一个python脚本slave.py到远端机器。slave.py将被运行并提供RPC服务。

*：自动化配置环境未完成。

6.	文件传输
使用sftp进行文件的传输。

7.	本地文件监控
使用inotify监控文件的变化，使用md5和Unix时间戳记录文件状态。

8.	安全性
ssh通信较安全。sftp文件传输较安全。RPC通信通过锁定IP以及利用事先使用ssh传输的密码进行加密*以保证安全性。

*：目前未实现。


