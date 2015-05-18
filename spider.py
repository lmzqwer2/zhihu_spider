#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

'''
Read the volcabulary from shanbay.com
'''

import cookielib, urllib2, urllib, Cookie, re, time, argparse, gzip, StringIO
from os import path
from lsqlite import db, orm
from models import User, UserList
from bs4 import BeautifulSoup as bs
from IPython import embed
try:
    import json
except ImportError:
    import simplejson as json

cookieJar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
headers = {
    'Host': 'www.zhihu.com',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36',
    'Referer': 'http://www.zhihu.com/',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cookie': ' _za=66e5f568-83fc-4cee-99a5-6f125f1477e5; q_c1=3280938f2b694f7ea333bba230caa553|1430745348000|1430745348000; z_c0="QUtCQXVFS2J6UWNYQUFBQVlRSlZUUVQtYmxYcXFvOElTM0tzWmhfME42ZVpPVGszZTVEbXpBPT0=|1430745348|a4e4b5d3aae27b201a1d02a27f1915faaf3215b5"; _xsrf=e4556d2cfc929adb16a3742cba31c6b2'
}
#opener.handle_open["http"][0].set_http_debuglevel(1)

zhihu_people = 'http://www.zhihu.com/people/'

def getResponse(url, data={}, method=lambda: 'GET', **kw):
    jsdata = json.dumps(data)
    encodejsdata = urllib.urlencode(data)
    request = urllib2.Request(url, encodejsdata)
    request.get_method = method
    for name, values in headers.items():
        if name not in kw:
            request.add_header(name, values)
    for name, values in kw.items():
        request.add_header(name, values)
    response = opener.open(request, timeout = 60)
    if response.info().get('Content-Encoding') == 'gzip': # gzip
        content = response.read()
        data    = StringIO.StringIO(content)
        gzipper = gzip.GzipFile(fileobj=data)
        html    = gzipper.read()
    else: # normal page
        html = response.read()
    return html

targetServer = 'http://localhost:4323/'
check = 0

def postResult(l, t):
    url = targetServer + 'get'
    l['t'] = t
    print l
    try:
        response = getResponse(url, l, lambda: 'POST')
    except Exception, e:
        print 'ERR: nexSpacename', e, url
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response)

def nexSpaceName():
    url = targetServer + 'get'
    print url
    try:
        response = getResponse(url)
    except Exception, e:
        print 'ERR: nexSpacename', e, url
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response)
    
def newSpaceName(l):
    url = targetServer + 'new'
    try:
        response = getResponse(url, l, lambda: 'POST')
    except Exception, e:
        zhihuRequestLock.fail()
        print 'ERR: newSpacename', e, url
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response)

uid_pattern = re.compile('^/inbox/(.*)$')

def UserInfo(html):
    L = {}
    userProfile = html.find('div', class_='zm-profile-header')
    if userProfile is None:
        return L
    user = userProfile.find('div', class_='title-section')
    userName = user.find('span', class_='name')
    if userName is None:
        userName = user.find('a', class_='name')
    L['name'] = userName.text.encode('utf8')
    userBio = user.find('span', class_='bio' )
    if userBio is None:
        userBio = ''
    else:
        userBio = ' '.join(userBio.text.split('\r\n'))
    L['bio'] = userBio.encode('utf8')
    follow = html.find('button', {'data-follow':'m:button'})
    hashId = follow['data-id'] if follow is not None else ''
    L['hashId'] = hashId
    return L

space_pattern = re.compile('^/people/(.*)$')

def findAllPeople(types, i, times, html, sname):
    followees = html.find_all('div', class_='zm-profile-section-item')
    l = {'nowSpaceName': sname, 'spaceName':''}
    for people in followees:
        linker = people.find('a', class_='zm-item-link-avatar')
        space_match = space_pattern.match(linker['href'])
        if space_match:
            space_name = space_match.group(1)
            ul = UserList.get(space_name)
            u = User.find_first('where spaceName=?', space_name)
            if u is None and ul is None:
                l['spaceName'] = space_name
                d = newSpaceName(l)
                if check:
                    print types, i, times, space_name, d
            else:
                if check:
                    print types, i, times, space_name, "exist."
 
followee_headers = {
    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1581.2 Safari/537.36',
    'Host':'www.zhihu.com',
    'Origin':'http://www.zhihu.com',
    'Connection':'keep-alive',
    'Content-Type':'application/x-www-form-urlencoded',
}

def merge(pre, now):
    tmp = pre
    for key,val in pre.iteritems():
        if key in now:
            if isinstance(val, dict):
                tmp[key] = merge(val, now[key])
            else:
                tmp[key] = now[key]
        else:
             tmp[key] = val
    for key,val in now.iteritems():
        if key not in tmp:
            tmp[key] = val
    return tmp

class zhihuRequestLock(object):
    '''
    calc the number of request to zhihu
    '''
    num = 0
    fail = 0
    @classmethod
    def check(cls):
        return cls.fail>=10
    
    @classmethod
    def checkgevent(cls):
        '''
        Do something in gevent mode but no use in normal mode.
        '''
        pass

    @classmethod
    def inc(cls):
        cls.num += 1

    @classmethod
    def dec(cls):
        cls.num -= 1

    @classmethod
    def failed(cls):
        cls.fail += 1

    @classmethod
    def clear(cls):
        cls.fail = 0

def searchUserTable(types, i, load_times, params, _xsrf, refurl, listurl, space_name):
    params['offset'] = i * 20
    post_data = {
        'method': 'next',
        'params': json.dumps(params),
        '_xsrf': _xsrf,
    }
    post_header = followee_headers
    post_header['Referer'] = refurl
    response = None
    if zhihuRequestLock.check()!=0:
        return 
    try:
        zhihuRequestLock.checkgevent()
        zhihuRequestLock.inc()
        if check:
            print 'Search: table', i, 'Co-search:', zhihuRequestLock.num
        response = getResponse(listurl, post_data, lambda: 'POST', **post_header)
    except Exception, e:
        zhihuRequestLock.failed()
        print 'ERR: UserTable', e, listurl
    finally:
        zhihuRequestLock.dec()
    if response is not None and zhihuRequestLock.check()==0:
        data = json.loads(response)
        if data.get('r',1)==0:
            html = bs(''.join(data['msg']))
            findAllPeople(types, i, load_times, html, space_name)

def searchNextFollow(times, params, _xsrf, refurl, listurl, space_name):
    for i in range(1,times):
        searchUserTable(1, i+1, times, params, _xsrf, refurl, listurl, space_name)

def searchUser(space_name, t):
    L = {}
    for url, code in zip(['followees','followers'], [6, 7]):
        follow = zhihu_people + space_name + '/' + url
        listurl = 'http://www.zhihu.com/node/Profile'+url.capitalize()+'ListV2'
        try:
            response = getResponse(follow)
        except Exception, e:
            print 'ERR: searchUser', e, follow
            continue
        html = bs(response, from_encoding="UTF-8")
        L = merge(L, UserInfo(html))

        listdiv = html.find('div', class_='zh-general-list')
        if listdiv is None:
            continue
        data = json.loads(listdiv['data-init'])
        params = data['params']
        _xsrf = html.find('input', {'name':'_xsrf'})['value']

        items = html.find_all('a', class_='item')
        followee_status = items[code]
        num_followees = followee_status.find('strong').text
        load_times = int(num_followees) / 20 +1

        findAllPeople(0, 1, load_times, html, space_name)
        
        if load_times>1:
            searchNextFollow(load_times, params, _xsrf, follow, listurl, space_name)

    L['spaceName'] = space_name
    if zhihuRequestLock.check()==0:
        data = postResult(L, t)
        if data.get('code',1)!=0:
            print space_name, data.get('code', 1), data.get('msg', '')
    else:
        print "Error exit of: %s" % space_name
#embed()

def run():
    nowdir = path.abspath(__file__).strip(__file__)
    stopfile = path.join(nowdir, 'spiderstop')
    while not path.exists(stopfile):
        data = nexSpaceName()
        if data.get('code',2) != 0:
            print data.get('code'), data.get('msg')
            if data.get('code')==-1:
                print 'Server stop.'
                break
            time.sleep(1)
            continue
        data = json.loads(data.get('info', '{}'))
        now = data.get('spacename', None)
        t = data.get('t', None)
        print now, t
        if now is None or t is None:
            time.sleep(1)
            continue
        print 'SEARCH: %s' % now
        zhihuRequestLock.clear()
        searchUser(now, t)
    if path.exists(stopfile):
        print 'File stop.'

#embed()

def load():
    global targetServer
    global check
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', default='http://localhost:4323', help='The address of the server')
    parser.add_argument('-d', '--database', default='zdb.db', help='to use local database to check the data conflict')
    parser.add_argument('-c', '--check', default=0, help='to use local database to check the data conflict')
    args = parser.parse_args()
    targetServer = args.address
    dbname = args.database
    check = args.check
    print dbname
    db.create_engine(dbname);
    if not targetServer.endswith('/'):
        targetServer += '/'
    if not targetServer.startswith('http://'):
        targetServer = 'http://' + targetServer
    print targetServer

if (__name__ == '__main__'):
    load()
    run()
