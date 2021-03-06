#!/usr/bin/env python

# Copyright (c) 2012-2013 Lukasz Bolikowski
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cgi
import datetime
import json
import re
import sqlite3
import sys

CUTOFF_DAYS = 1000
LIMIT = 200

def calc_toc(conn):
   fromDate = (datetime.datetime.now() - datetime.timedelta(CUTOFF_DAYS)).strftime('%Y-%m-%d')
   fromYear = fromDate[0:4]
   return [rec for rec in conn.execute('SELECT v.key, v.kind, v.acronym, v.name, COUNT(*) FROM venue AS v JOIN record AS r ON r.venue = v.key WHERE r.date >= ? AND r.year >= ? GROUP BY v.key ORDER BY v.kind, v.name', (fromDate, fromYear))]

def update_feeds(toc, conn, feedsDirName):
   DATETIME_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

   now = datetime.datetime.utcnow().strftime(DATETIME_FORMAT)
   fromDate = (datetime.datetime.now() - datetime.timedelta(CUTOFF_DAYS)).strftime('%Y-%m-%d')
   fromYear = fromDate[0:4]

   for key, kind, acronym, name, _ in toc:
      # print 'Building feed for %s' % key
      sanitizedKey = re.sub('[^a-zA-Z0-9_/-]', '', key)
      fullKind = ['conference', 'journal'][kind == 'journals']
      handle = open(feedsDirName + '/' + sanitizedKey + '.xml', 'w')

      name = cgi.escape(name.encode('utf-8'))

      handle.write('<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n')
      handle.write('  <title>%s</title>\n' % name)
      handle.write('  <description>Feed for DBLP-indexed %s %s</description>\n' % (fullKind, name))
      handle.write('  <link>http://dblp.uni-trier.de/db/%s/index.html</link>\n' % key)
      handle.write('  <lastBuildDate>%s</lastBuildDate>\n\n' % now)

      for title, authors, date, link, _, year \
         in conn.execute('SELECT * FROM record WHERE venue = ? AND year >= ? ORDER BY date DESC LIMIT ?', (key, fromYear, LIMIT)):

         title = cgi.escape(title.encode('utf-8'))
         authors = cgi.escape(authors.encode('utf-8'))
         link = cgi.escape(link.encode('utf-8'))

         formattedDate = datetime.datetime.strptime(date, '%Y-%m-%d').strftime(DATETIME_FORMAT)

         handle.write('  <item>\n    <title>%s</title>\n' % title)
         handle.write('    <description>Published in %d. Authors: %s</description>\n' % (int(year), authors))
         handle.write('    <author>%s</author>\n' % authors)
         handle.write('    <link>%s</link>\n' % link)
         handle.write('    <guid>%s</guid>\n' % link)
         handle.write('    <pubDate>%s</pubDate>\n' % formattedDate)
         handle.write('  </item>\n\n')

      handle.write('</channel>\n</rss>\n')
      handle.close()

def update_index(toc, htmlFileName):
   handle = open(htmlFileName, 'w')
   headings = {'conf': 'Conferences', 'journals': 'Journals'}
   for turn in ['conf', 'journals']:
      handle.write('<div class="%s">\n<h2>%s</h2>\n' % (turn, headings[turn]))
      for key, kind, acronym, name, count in toc:
         if kind <> turn:
            continue
         sanitizedKey = re.sub('[^a-zA-Z0-9_/-]', '', key)
         handle.write('<div class="entry"><a href="%s.xml">%s</a> <span class="count">%d</span></div>\n' % (sanitizedKey, name.encode('utf-8'), min(count, LIMIT)))
      handle.write('</div>\n')
   handle.close()

def update_json(toc, jsonFileName):
   handle = open(jsonFileName, 'w')
   json.dump(toc, handle)
   handle.close()

if __name__ == "__main__":
   def usage():
      print 'Usage: %s <index.sqlite> <feeds_dir> <index.html.part> <index.json>' % sys.argv[0]

   if len(sys.argv) < 5:
      usage()
      sys.exit(1)

   conn = sqlite3.connect(sys.argv[1])
   toc = calc_toc(conn)
   update_feeds(toc, conn, sys.argv[2])
   update_index(toc, sys.argv[3])
   update_json(toc, sys.argv[4])
   conn.close()

# vim:et:sw=3:ts=3
