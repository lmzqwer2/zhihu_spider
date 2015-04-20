#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

import tornado.ioloop
import tornado.web
import tornado.options
import time, hashlib, logging, thread
from os import path
try:
    import json
except ImportError:
    import simplejson as json
from lsqlite import db
from models import User, UserList
from tornado.options import define, options

define('workspace', default=path.dirname(path.realpath(__file__)), help='work folder')
define('database', default=path.join(path.dirname(path.realpath(__file__)), 'zdb.db'), help='Database stroage all the infomation')
define('port', default='4323', help="Server listen on")
define('timeout', default=20.0, help='User retry time')
define('flushtime', default=10.0, help='User lock time')

class BaseHandler(tornado.web.RequestHandler):
    pass

class ShowHandler(BaseHandler):
    def get(self):
        u = User.randomGet()
        cnt = 0
        while u.bio=='' and cnt < 5:
            u = User.randomGet()
        self.render('show.html', user=u)

class StatusHandler(BaseHandler):
    def get(self):
        ulc = UserList.count_all()
        uc = User.count_all()
        ubc = User.count_by('where bio!=\'\'')
        self.write('Found %d User(s), including %d have got, %d to search.' % (uc+ulc, uc, ulc))
        self.write('<br/>%d users have its own bio' % ubc)
        self.write('<br/>Tryed: ')
        for i in range(0, 6):
            ultc = UserList.count_by('where tryTime==?', i)
            self.write(' (%d _ %d) ' % (i, ultc))

class NewHandler(BaseHandler):
    def post(self):
        spacename = self.get_argument('spaceName')
        nowspacename = self.get_argument('nowSpaceName')
#password = self.get_argument('password')
        ul = UserList.get(spacename)
        u = User.find_first('where spaceName=?', spacename)
        if u is None and ul is None:
            uln = UserList(spaceName = spacename)
            print 'NUL: SpaceName=%s' % (spacename)
            uln.insert()
            self.write(json.dumps({'code': 0, 'msg':'Succeed'}))
        else:
            print 'EXT: spacename=%s' % (spacename)
            self.write(json.dumps({'code': 1, 'msg':'already exist!'}))
            ul = UserList.get(nowspacename)
            if ul is not None and time.time()-ul.last>options.flushtime:
                if ul is not None:
                    print 'flush the time of %s' % ul.spaceName
                    ul.last = time.time()
                    ul.update()

lock = thread.allocate_lock()

class GetHandler(BaseHandler):
    def get(self):
        if UserList.count_all()==0:
            self.write(json.dumps({'code':-1, 'msg':'No user in list'}))
        else:
            global lock
            lock.acquire()
            nt = time.time()
            ul = UserList.find_first('where last<? and tryTime<5', nt-options.timeout)
            if ul is None:
                ul = UserList.find_first('where last<?', nt-options.timeout)
            if ul is None:
                self.write(json.dumps({'code': 1, 'msg': 'None to pop'}))
            else:
                ul.last = time.time()
                ul.createdAt = ul.last
                ul.tryTime += 1
                ul.update()
                print u'GET: SpaceName=%s, TryTime=%d, last=%f' % (ul.spaceName, ul.tryTime, ul.last)
                output = {'spacename': ul.spaceName, 't': str(ul.createdAt)}
                self.write(json.dumps({'code': 0, 'msg': 'Succeed', 'info': json.dumps(output)}))
            lock.release()

    def post(self):
        t = self.get_argument('t')
        hashId = self.get_argument('hashId')
        name = self.get_argument('name')
        spacename = self.get_argument('spaceName')
        bio = self.get_argument('bio')
        ul = UserList.get(spacename)
        u = User.get(hashId)
        if t is not None and ul is not None and str(ul.createdAt)==t and u is None and len(hashId)==32:
            global lock
            lock.acquire()
            nu = User(hashId=hashId, name=name, spaceName=spacename, bio=bio)
            print u'INS: name=%s, hashId=%s, spaceName=%s, last=%f, tryTime=%d\nBio=%s' % (name, hashId, spacename, ul.last, ul.tryTime, bio)
            ul.delete()
            nu.check_insert()
            self.write(json.dumps({'code': 0, 'msg':'Succeed'}))
            lock.release()
        else:
            self.write(json.dumps({'code': 1, 'msg':'Error'}))

class NotFoundHandler(BaseHandler):
    def get(self):
        raise tornado.web.HTTPError(404)

app = tornado.web.Application([
    (r"/", ShowHandler),
    (r"/status", StatusHandler),
    (r"/get", GetHandler),
    (r"/new", NewHandler),
    (r"/(bgimg.jpg)", tornado.web.StaticFileHandler, {'path':options.workspace}),
    (r"/.*", NotFoundHandler),
])

if __name__ == "__main__":
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    print options.database
    options.logging = 'warning'
    tornado.options.parse_command_line()
    db.create_engine(options.database)
    User.init()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
