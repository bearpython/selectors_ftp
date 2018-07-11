#!/usr/bin/env python
#_*_ coding:utf-8 _*_
# Author:bear

import sys,time

class ShowProcess(object):
    def __init__(self,count,total,width,process):
        self.count = count
        self.total = total
        self.width = width
        self.process = process

    def show_process(self):
        percentage = self.count / self.total #计算当前接收数据占总数据比值，count是累计叠加的接收数据大小
        tmp_process = percentage * self.width  #计算本次比值占用多少个#
        cur_process = int(tmp_process - self.process) #当前需要输入多少个#，这里需要计算减去已经输出多少个#，然后当前需要的#减去已经输出的#，就是本次要输出几次#
        if cur_process >= 1:
            self.process += cur_process
            for i in range(int(cur_process)):
                sys.stdout.write("#")
                sys.stdout.flush()
                time.sleep(0.1)
        return self.process

# bar = ShowProcess(148161214,10000000,50)
# bar.show_process()