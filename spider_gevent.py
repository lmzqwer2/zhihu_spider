#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'lmzqwer2'

from gevent import monkey; monkey.patch_all()
import gevent

import spider

def newSearchNextFollow(load_times, params, _xsrf, refurl, listurl, space_name):
    
    glist = [ gevent.spawn(searchUserTable, 2, i+1, load_times, params, _xsrf, refurl, listurl, space_name) for i in range(1, load_times)]
    gevent.joinall(glist)

spider.searchNextFollow = newSearchNextFollow

@classmethod
def newLockCheck(cls):
    while cls.num >= 10:
        gevent.sleep(0)

spider.zhihuRequestLock.check = newLockCheck

from spider import *

if __name__ == '__main__':
    load()
    run()
