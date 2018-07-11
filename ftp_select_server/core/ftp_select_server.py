#!/usr/bin/env python
#_*_ coding:utf-8 _*_
# Author:bear

import socketserver
import socket,time
import os,sys,hashlib
import json,errno
import selectors

"""
注意，在写selectors的ftpserver时候需要用到modify这个方法，要不然执行不了
大致的步骤是：
server启动等待连接，并监听自己的socket
client启动连接server
server建立连接，把连接添加到监听的列表里
client：发送一个字典过来带着文件名、大小等信息
server:坚挺到有数据返回了，就调用read方法进行处理，第一次接收到的数据是用户端发来的字典，返回给用户信号准备接受文件数据
client：接受到server端的标识，然后发送文件数据
server：这个在处理完上一步接受的字典后，用modify这个方法把sel实例进行改变，不走read方法了，直接调用put方法，直到数据接收完，put方法在回调回read方法
我理解就是一个连接当做一个实例来处理，在接收文件数据前都是进行raad调用，真正开始接收文件数据后就改变回调函数，要不然在接收第二次文件数据时候又回到了read函数，这样肯定报错了
"""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from conf import setting



class ftp_selectors_server(object):
    """
    ftp服务端
    """
    def __init__(self,sock):
        self.sock = sock
        self.sel = selectors.DefaultSelector()
        self.put_dic = {}
        self.get_dic = {}

    def put(self,conn,mask):
        """接收客户端文件"""
        try:
            filesize = self.put_dic[conn]["size"]
            recived_size = self.put_dic[conn]["recv_size"]
            f = self.put_dic[conn]["openfile"]
            while recived_size < filesize:
                try:
                    data = conn.recv(1024)
                    #m.update(data)
                    f.write(data)
                    recived_size += len(data)
                    self.put_dic[conn]["recv_size"] = recived_size
                    # raise BlockingIOError
                    # 异常处理，这个连接第一次建立然后第一次接收数据是一个字典，第二次开始就是数据文件里，在第一次接收完后发给客户端，然后等待客户端返回时候这个必然会报错
                    # 这样处理一下就是抓到这个异常后raise后边的代码不会执行了，但是except里边的还会执行
                    if recived_size >= filesize:
                        print("文件接收完成！%s" % self.put_dic[conn]["filename"])
                        f.close()
                        del self.put_dic[conn]
                        self.sel.modify(conn, selectors.EVENT_READ, self.read)
                except BlockingIOError:
                    break

        except ConnectionResetError as e:
            print("客户端断开连接",e)

    def get(self,conn,mask):
        """发送给客户端需要下载的文件"""
        print("进入get方法")
        try:
            client_response = conn.recv(1024).strip()  # three
            print("客户端接状态：", client_response.decode())
            f = self.get_dic[conn]["openfile"]
            f.seek(self.get_dic[conn]["send_size"])
            while self.get_dic[conn]["send_size"] < self.get_dic[conn]["size"]:
                #print("进入while循环")
                for line in f:
                    #print("进入for循环")
                    sendsize = conn.send(line)  # four
                    self.get_dic[conn]["send_size"] += sendsize
                    # print("发送文件的大小：",self.get_dic[conn]["send_size"])
                if self.get_dic[conn]["send_size"] == self.get_dic[conn]["size"]:
                    print("文件发送完成！")
                    f.close()
                    del self.get_dic[conn]
                    self.sel.modify(conn, selectors.EVENT_READ, self.read)
                    break
        except BlockingIOError:
            return

    def accept(self,sock, mask):
        """监听函数，所有进来的连接包括新连接和数据连接以及server端自己的连接"""
        conn,addr = sock.accept()  # Should be ready
        print('accepted', conn, 'from',addr)
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)  # 新连接注册read回调函数

    def read(self,conn,mask):
        """建立连接后接收用户数据的回调函数"""
        self.data = conn.recv(1024)  # Should be ready
        cmd_dic = json.loads(self.data.decode())
        action = cmd_dic["action"]
        if self.data:
            print('echoing', repr(self.data), 'to', conn)
            if action == "put":
                cmd_dic["recv_size"] = 0
                filename = "%s\%s" % (setting.DATA_PATH, cmd_dic["filename"])
                if os.path.isfile(filename):
                    f = open(filename + ".new", "wb")
                else:
                    f = open(filename, "wb")
                cmd_dic["openfile"] = f
                self.put_dic[conn] = cmd_dic
                conn.send(b"True")
                print("conn :",conn)
                self.sel.modify(conn, selectors.EVENT_READ, self.put)
                #self.put(conn,mask)  #如果这样调用，就只执行一次put后又回到了read方法，没法接收了
            elif action == "get":
                filename = "%s\%s" % (setting.DATA_PATH, cmd_dic["filename"])
                if os.path.isfile(filename):
                    filesize = os.stat(filename).st_size
                    msg_dic = {
                        "filename": filename,
                        "size": filesize,
                        "flag": True,
                    }
                    print("下载文件server端大小：", filesize)
                    conn.send(json.dumps(msg_dic).encode())  # two
                    f = open(filename, "rb")
                    msg_dic["openfile"] = f
                    msg_dic["send_size"] = 0
                    self.get_dic[conn] = msg_dic
                    print(self.get_dic)
                    self.sel.modify(conn,selectors.EVENT_READ,self.get)
                else:
                    msg_dic = {
                        "flag": False
                    }
                    conn.send(json.dumps(msg_dic).encode())
                    print("server端，文件不存在")
        else:
            print('closing', conn)
            self.sel.unregister(conn)
            conn.close()

    def register(self):
        """把sock的实例server传给此方法注册到sel这个对象里边，然后去进行监听，第一次就是传server自己"""
        self.sock.listen(100)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept) #这里是只要来新的连接就调用accept函数(调用实在for循环里边的回掉函数)
        while True:
            events = self.sel.select()  # 默认是阻塞的，有活动连接就返回活动的连接列表
            for key, mask in events:
                callback = key.data  # 回调函数，等于是调用accept函数了
                callback(key.fileobj, mask)  # key,fileobj =  文件句柄

