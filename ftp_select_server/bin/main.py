#!/usr/bin/env python
#_*_ coding:utf-8 _*_
# Author:bear

import os,sys,socketserver,socket

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core import ftp_select_server


if __name__ == "__main__":
    sock = socket.socket()
    sock.bind(("localhost",9999))
    ftp_server = ftp_select_server.ftp_selectors_server(sock)
    ftp_server.register()