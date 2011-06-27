#  Copyright (c) 2011, Mikheev Rostislav
#
#  This source code is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#  author Mikheev Rostislav <hacenator@gmail.com>
#  date 27.06.2011

# -*- coding: utf-8 -*-
import threading
import urllib2
from BeautifulSoup import BeautifulSoup
import pycurl, StringIO
import time
import threading
import Queue

def getProxyList(verbose = False):
    '''Generate fine HTTP proxy list'''
    class ProxyGrabber(threading.Thread):
        def __init__(self, page, que, verbose=True):
            threading.Thread.__init__(self)
            self.verbose = verbose
            self.list_url = "http://spys.ru/proxylist%d/"
            self.page = page
            self.que = que

        def message(self, message):
            print "(%s): %s" % (self.name, message)

        def run(self):
            if self.verbose:
                self.message("Grab page: %d" % (self.page))

            url = self.list_url % self.page

            list = []

            # grab page
            req = urllib2.Request(url)
            data = urllib2.urlopen(req).read()

            # clear data
            soup = BeautifulSoup(data)

            # And agian fuuuuuuuckin security and antigrab )))
            scripts = soup.findAll("script")
            codes = scripts[3].contents[0]
            codes = codes.split(';')
            codes = codes[10:]

            decode = {}
            i = 0
            for code in codes:
                code = code.split('^')
                if len(code) == 2:
                    decode[code[1]] = i
                    i += 1

            # grab
            rows = soup.findAll("tr",{"class": "spy1xx"})
            for row in rows:
                data = row.find("font", {"class": 'spy14'})
                if data:
                    ip = data.contents[0]
                    code = str(data.contents[1])
                    parts = code[75:len(code)-10].split('+')
                    port = ""
                    for part in parts:
                        part = part.strip('(').strip(')').split('^')[1]
                        port += str(decode[part])

                    list.append("%s:%s" % (ip, port))

            #print proxies
            if self.verbose:
                self.message("Found proxies: %d" % len(list))
                self.message("Checking proxies")

            #TODO(hacenator) I checking proxy with standart google logo. And this not always work fine
            data = StringIO.StringIO()
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, 'http://www.google.com/images/logo_sm.gif')
            curl.setopt(pycurl.TIMEOUT, 2)

            num = 1
            count = len(list)
            for proxy in list:
                data = StringIO.StringIO()
                curl.setopt(pycurl.WRITEFUNCTION, data.write)

                curl.setopt(pycurl.PROXY, str(proxy))

                try:
                    delta = time.time()

                    curl.perform()
                    length = len(data.getvalue())

                    delta = time.time() - delta

                    # ok. i check this with google standart web logo
                    if length == 3972 and delta < 5:
                        if self.verbose:
                            self.message("(%d/%d) GOOD %s (%d sec)" % (num, count, proxy, delta))
                    else:
                        if self.verbose:
                            self.message("(%d/%d) BAD %s (%d sec)" % (num, count, proxy, delta))
                        list.remove(proxy)
                except:
                    if self.verbose:
                        self.message("(%d/%d) BAD %s" % (num, count, proxy))
                    list.remove(proxy)

                num += 1

            curl.close()

            if self.verbose:
                self.message("Good proxies: %d" % len(list))

            # test it
            self.que.put(list)

    pages = 8
    proxies = []
    que = Queue.Queue(0)

    if verbose:
        print "Get proxies"

    # start threads
    for page in range(pages):
        thread = ProxyGrabber(page, que, verbose)
        thread.start()

    # waiting
    for thread in threading.enumerate():
        if thread is not threading.currentThread():
            thread.join()
            proxies.extend(que.get())
    if verbose:
        print "Grabbed!"

    return proxies
