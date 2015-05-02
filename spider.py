#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

'''
Read the volcabulary from shanbay.com
'''

import cookielib, urllib2, urllib, Cookie, re, time, argparse
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
    'Accept-Encoding': 'deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cookie': 'q_c1=050daf1212554da3bdd5801a41cb907f|1428635070000|1428635070000; z_c0="QUtCQXVFS2J6UWNYQUFBQVlRSlZUYl9LVGxVSVlid0xrWUZySjV6UHl2U3JwQjNQTjhreE9RPT0=|1428635071|9e86871527a7183b7894cec44755fda70aa1250b"; _xsrf=84e730b281ae1b2f00b65b95e7b04ba9'
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
    response = opener.open(request)
    return response

targetServer = 'http://localhost:4323/'
check = 0

def postResult(l, t):
    url = targetServer + 'get'
    l['t'] = t
    print l
    try:
        response = getResponse(url, l, lambda: 'POST')
    except Exception, e:
        print e
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response.read())

def nexSpaceName():
    t = targetServer + 'get'
    print t
    try:
        response = getResponse(t)
    except:
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response.read())
    
def newSpaceName(l):
    url = targetServer + 'new'
    try:
        response = getResponse(url, l, lambda: 'POST')
    except:
        return {'code': 2, 'msg':'Network Error'}
    return json.loads(response.read())

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

def findAllPeople(html, sname):
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
                    print space_name, d
            else:
                if check:
                    print space_name, "exist."
                
 
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

def searchUser(space_name, t):
    L = {}
    for url in ['followees','followers']:
        follow = zhihu_people + space_name + '/' + url
        listurl = 'http://www.zhihu.com/node/Profile'+url.capitalize()+'ListV2'
        try:
            response = getResponse(follow)
        except:
            print 'What\'s wrong with your network?'
            continue
        html = bs(response.read())
        L = merge(L, UserInfo(html))
        findAllPeople(html, space_name)

        listdiv = html.find('div', class_='zh-general-list')
        if listdiv is None:
            continue
        data = json.loads(listdiv['data-init'])
        params = data['params']
        _xsrf = html.find('input', {'name':'_xsrf'})['value']

        items = html.find_all('a', class_='item')
        followee_status = items[6]
        num_followees = followee_status.find('strong').text
        load_times = int(num_followees) / 20 +1

        for i in range(1,load_times):
            params['offset'] = i * 20
            post_data = {
                'method': 'next',
                'params': json.dumps(params),
                '_xsrf': _xsrf,
            }
            post_header = followee_headers
            post_header['Referer'] = follow
            try:
                response = getResponse(listurl, post_data, lambda: 'POST', **post_header)
                data = json.loads(response.read())
                if data.get('r',1)==0:
                    html = bs(''.join(data['msg']))
                    findAllPeople(html, space_name)
                else:
                    break;
            except Exception, e:
                print 'ERR:', e
    L['spaceName'] = space_name
    data = postResult(L, t)
    if data.get('code',1)!=0:
        print space_name, data.get('code', 1), data.get('msg', '')
        pass        
#embed()

def run():
#    import sys
#    reload(sys)
#    sys.setdefaultencoding('utf-8')
#    headers['Cookie'] = ''
#    searchFromFollwee('zhao-yue-qi-88')
#    searchFromZhihu('zenozeng')
#    searchFromFollowee('edward-mj')

    while True:
        data = nexSpaceName()
        if data.get('code',2) != 0:
            print data.get('code'), data.get('msg')
            if data.get('code')==-1:
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
        searchUser(now, t)

#embed()

if (__name__ == '__main__'):
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
    run()
