from collections import namedtuple
import re

import requests
from lxml.etree import fromstring

from htmlutils import parse_document_from_requests

SongInfo = namedtuple('SongInfo', 'sid name href artist album info')
DEFAULT_BETTER_LRC_RE = re.compile(r'\[\d+:\d+[:.](?!00)\d+\]')

class Xiami:
  _session = None
  better_lrc_re = DEFAULT_BETTER_LRC_RE

  def __init__(self, session=None):
    self._session = session

  @property
  def session(self):
    if not self._session:
      s = requests.Session()
      s.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:20.0) ' \
          'Gecko/20100101 Firefox/20.0'
      self._session = s
    return self._session

  def search(self, q):
    url = 'http://www.xiami.com/search?key=' + q
    doc = parse_document_from_requests(url, self.session)
    rows = doc.xpath('//table[@class="track_list"]//tr')[1:]
    ret = []
    for tr in rows:
      # 没有 target 属性的是用于展开的按钮
      names = tr.xpath('td[@class="song_name"]/a[@target]')
      if len(names) == 2:
        info = names[1].text_content()
      else:
        info = None
      name = names[0].text_content()
      href = names[0].get('href')

      # '/text()' in XPath get '.text', not '.text_content()'
      artist = tr.xpath('td[@class="song_artist"]/a')[0].text_content().strip()
      album = tr.xpath('td[@class="song_album"]/a')[0].text_content().strip()
      album = album.lstrip('《').rstrip('》')

      sid = href.rsplit('/', 1)[-1]
      song = SongInfo(sid, name, href, artist, album, info)
      ret.append(song)

    return ret

  def getLyricFor(self, sid):
    url = 'http://www.xiami.com/song/playlist/id/%s/object_name/default/object_id/0' % sid
    r = self.session.get(url)
    doc = fromstring(r.content)
    try:
      lyric_url = doc.xpath('//xspf:lyric/text()',
                            namespaces={'xspf': 'http://xspf.org/ns/0/'})[0]
    except IndexError:
      return
    # pic_url = doc.xpath('//xspf:pic/text()', namespaces={'xspf': 'http://xspf.org/ns/0/'})[0]

    r = self.session.get(lyric_url)
    return r.text

  def findBestLrc(self, q):
    results = self.search(q)
    candidate = None
    r = self.better_lrc_re

    for song in results:
      lyric = self.getLyricFor(song.sid)
      if lyric and lyric.count('[') > 5:
        if r.search(lyric):
          return lyric
        elif not candidate:
          candidate = lyric

    return candidate
