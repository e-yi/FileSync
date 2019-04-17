# autoSync

auto sync directury to linux server

usage :

$ python autoSync.py default.xml

depends :

    pip install paramiko
    pip install watchdog

compile to stand alone binary file :

    python pyinstaller.py -F autoSync.py

bin file is in  autoSync/dist 

pyinstaller ：https://github.com/pyinstaller/pyinstaller

to remove CryptographyDeprecationWarning
use `pip install cryptography==2.4.2`

