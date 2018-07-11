#!/usr/bin/env python
#_*_ coding:utf-8 _*_
# Author:bear

import socket
import os,sys,time
import json,hashlib
import ShowProcess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
print(BASE_DIR)
#声明socket类型，同时生成socket连接对象

class ftp_selectors_client(object):
    def __init__(self):
        self.client = socket.socket() #默认地址簇是AF_INET就是IPV4，type是TCP/IP，proto=0，fileno=None

    def help(self):
        """在用户输入ftp未定义的指令时显示给用户"""
        msg = """
        get filename
        put filename
        """
        print(msg)

    def connect(self,ip_port):
        self.client.connect(ip_port)

    def interactive(self):
        """认证后登录的ftp主程序，根据用户输入的内容反射调用相关的方法"""
        # self.authenticate()#登录认证的方法
        while True:
            cmd = input(">>>:").strip()
            if len(cmd) == 0:continue
            if cmd == "get" or cmd == "put" or cmd == "cd":
                cmd_str = cmd.split()
                if len(cmd_str) == 1:
                    print("少一个参数")
                    continue
            cmd_str = cmd.split()[0]
            if hasattr(self,"cmd_%s" %cmd_str):
                func = getattr(self,"cmd_%s" %cmd_str)
                func(cmd)
            else:
                self.help()

    def cmd_put(self,*args):
        """上传到ftp文件"""
        cmd_split = args[0].split()
        if len(cmd_split) > 1:
            filename = cmd_split[1]
            if os.path.isfile(filename):
                filesize = os.stat(filename).st_size
                msg_dic = {
                    "action":"put",
                    "filename":filename,
                    "size":filesize,
                    "overidden":True  #这个是如果重名覆盖
                }
                self.client.send(json.dumps(msg_dic).encode())
                #为了防止粘包，等服务器确认
                server_response = self.client.recv(1024)
                if server_response.decode() == "True":
                    print("收到了服务端的确认标识")
                    f = open(filename,"rb")
                    process = 0
                    send_size = 0
                    #m = hashlib.md5()
                    for line in f:
                        self.client.send(line)
                        #m.update(line)
                        send_size += len(line)
                        process_bar = ShowProcess.ShowProcess(send_size, filesize, 50, process)
                        res = process_bar.show_process()
                        process = res
                    else:
                        print("文件上传完成！")
                        f.close()
                else:
                    print("上传文件过大，请重新选择文件！")
            else:
                print(filename,"is not exit")

    def cmd_get(self,*args):
        """下载ftp文件"""
        while True:
            cmd_split = args[0].split()
            if len(cmd_split) > 1:
                filename = cmd_split[1]
                msg_dic = {
                    "action": "get",
                    "filename": filename,
                    "overidden": True  # 这个是如果重名覆盖
                }
                self.client.send( json.dumps(msg_dic).encode()) #发送给server端文件name和动作 one
                self.server_response = self.client.recv(1024).strip()  #接收server端的返回文件是否存在及文件信息  two
                file_dic = json.loads(self.server_response.decode())
                print(file_dic)
                if file_dic["flag"] == True:
                    filesize = file_dic["size"]
                    if os.path.isfile(filename):
                        f = open(filename + ".new", "wb")
                    else:
                        f = open(filename, "wb")
                    self.client.send(b"client ok") #three
                    recived_size = 0
                    process = 0
                    while recived_size < filesize:
                        data = self.client.recv(1024) #four
                        f.write(data)
                        recived_size += len(data)
                        process_bar = ShowProcess.ShowProcess(recived_size,filesize,50,process)
                        res = process_bar.show_process()
                        process = res
                    else:
                        print("文件下载完成！%s" % filename)
                        f.close()
                        break
                else:
                    print("您要下载的文件不存在,请重新输入!")
                    break

if __name__ == "__main__":
    ip_port = ("localhost",9999)        #服务端ip、端口
    ftp = ftp_selectors_client()            #创建客户端实例
    ftp.connect(ip_port)
    # ftp.authenticate()
    ftp.interactive()