#!/usr/bin/env python
# encoding: utf-8

import optparse
import logging
import urllib2
import urllib
import sys
import os
import re
from HTMLParser import HTMLParser

logging.basicConfig()
LOG = logging.getLogger("youtube.downloader")
LOG.setLevel(logging.DEBUG)

FMT_MAP = {
 '5': '320x240 H.263/MP3 mono FLV',
 '6': '320x240 H.263/MP3 mono FLV',
'13': '176x144 3GP/AMR mono 3GP',
'17': '176x144 3GP/AAC mono 3GP',

'18': '480x360 480x270 H.264/AAC stereo MP4',
'22': '1280x720 H.264/AAC stereo MP4',

'34': '320x240 H.264/AAC stereo FLV',
'35': '640x480 640x360 H.264/AAC stereo FLV',

'37': '1920x1080 H.264/AAC stereo MP4',
}

def _reporthook(numblocks, blocksize, filesize, url=None):
    #print "reporthook(%s, %s, %s)" % (numblocks, blocksize, filesize)
    base = os.path.basename(url)
    #XXX Should handle possible filesize=-1.
    try:
        percent = min((numblocks*blocksize*100)/filesize, 100)
    except:
        percent = 100
    if numblocks != 0:
        print "\r%66s %3d%%" % (base, percent) ,

def geturl(url, dst):
    LOG.debug("Video URL is '%s'" % (url) )
    LOG.info("Saving video to '%s'" % (dst) )
    if sys.stdout.isatty():
        return urllib.urlretrieve(url, dst, lambda nb, bs, fs, url=url: _reporthook(nb,bs,fs,dst))
        #sys.stdout.write('\n')
    else:
        return urllib.urlretrieve(url, dst)

def downloadFileByUrl(url, filename=None):
   data = None
   try:
       f = urllib2.urlopen(url)
       if filename:
           geturl(url, filename)
           return True
       else:
           data = f.read()
           f.close()
   except IOError, e:
       LOG.critical("Can't process with download: %s" % e)
       return None
   except urllib2.HTTPError, e:
       LOG.critical("Can't process with download: %s" % e)
       return None


class YoutubePlaylistHTMLParser(HTMLParser):
    """HTMLParser class which extract youtube video IDs
       from HTML page
    """
    PLAYLIST_ITEMS = list()

    def __extract_video_id_from_uri(self, uri):
        """
        GET uri like '/watch?v=AsXf9v&param=1&p=3#junk'
        RETURNS value for 'v' parameter --> 'AsXf9v'
        """
        uri = uri.replace('&', ';')
        uri = uri.replace('?', ';')
        req, params = urllib.splitattr(uri)
        for item in params:
            k, v = urllib.splitvalue(params[0])
            if k == 'v':
                return v
        raise ValueError("Can't find parameter 'v' from '%s'" % uri)

    def handle_starttag(self, tag, attrs):
        if not tag == 'a':
            return 1

        # Building dict() from attrs list(). It's easy to dealing with dict() later...
        _attrs_dict = {}
        for attr in attrs:
            key, value = attr
            _attrs_dict[key] = value

        if _attrs_dict.get('id') and _attrs_dict.get('id').find('video-long-title') > -1:
            # We need only HREFs with 'id' == 'video-long-title.*'
            vid = self.__extract_video_id_from_uri(_attrs_dict['href'])
            self.PLAYLIST_ITEMS.append(vid)
            LOG.info("Found video id %s for %s" % (vid, _attrs_dict.get('title')) )


class Youtube(object):
    '''Youtube class is created to download video from youtube.com.
    '''
    @staticmethod
    def retriveYoutubePageToken(ID, htmlpage=None):
        """
        Magick method witch extract session token from 'htmlpage'.
        Session token needed for video download URL
        """
        if not htmlpage:
            url = "http://www.youtube.com/watch?v=%s" % ID
            #htmlpage="var fullscreenUrl = '/watch_fullscreen?fs=1&fexp=900142%2C900030%2C900162&iv_storage_server=http%3A%2F%2Fwww.google.com%2Freviews%2Fy%2F&creator=amiablewalker&sourceid=r&video_id=VJyTA4VlZus&l=353&sk=QtBR18Y95jsDyLXHgv9jbMu0ghb3MxoSU&fmt_map=34%2F0%2F9%2F0%2F115%2C5%2F0%2F7%2F0%2F0&t=vjVQa1PpcFPt0HhU0HkTG6A75-QxhAiV6WuMqB2a4r4%3D&hl=en&plid=AARnlkLz-d6cbsVe&vq=None&iv_module=http%3A%2F%2Fs.ytimg.com%2Fyt%2Fswf%2Fiv_module-vfl89178.swf&cr=US&sdetail=p%253Afriendfeed.com%2Feril&title=How To Learn Any Accent Part 1';"
            htmlpage = urllib2.urlopen(url).read()
        match = re.search(r', "t": "([^&"]+)"', htmlpage)
        if match:
            token = match.group(1)
        else:
            raise ValueError("Can't extract token from HTML page. Youtube changed layout. Please, contact to the author of this script")
        return token

    @staticmethod
    def retriveYoutubePageTitle(ID, htmlpage=None, clean=False):
        title = ID
        if not htmlpage:
            url = "http://www.youtube.com/watch?v=%s" % ID
            htmlpage = urllib2.urlopen(url).read()
        match = re.search(r"<title>(.+)</title>", htmlpage)
        if match:
            title = match.group(1)
            title = title.decode('utf-8')
            if clean:
                title = re.sub(ur"[^a-zA-Z0-9\W]+", "_", title, re.UNICODE)
                title = re.sub(ur"[\s\/]", "_", title, re.UNICODE)
        return title

    @staticmethod
    def getVideourlByFormatcodeForID(youtube_id, formatcode):
        if str(formatcode) not in FMT_MAP.keys():
            log.critical("Unknown code format %s. Please, check known videoformats table" % str(formatcode) )
            return None
        videourl = None
        token = Youtube.retriveYoutubePageToken(youtube_id)
        if token:
            videourl = "http://www.youtube.com/get_video.php?video_id=%s&fmt=%s&t=%s" % (youtube_id, formatcode, token)
        return videourl

    @staticmethod
    def downloadYoutubeVideo(youtube_id, formatcode, outFilePath=None):
        LOG.debug("Getting video URL for video (%s)" % FMT_MAP.get(str(formatcode)) )
        url = Youtube.getVideourlByFormatcodeForID(youtube_id, formatcode)
        if not url:
            LOG.debug("Can't get video url for %s format" % formatcode)
        else:
            return downloadFileByUrl(url, outFilePath)

    @staticmethod
    def run(youtube_id, outFilePath=None, formatcode=None):
        """
        GET youtube video ID 'youtube_id'
        RETURNS True is file properly downloaded and saved to local disk
                False in case of error
        """
        url = "http://www.youtube.com/watch?v=%s" % youtube_id
        htmlpage = None
        if not outFilePath:
            htmlpage = urllib2.urlopen(url).read()
            title = Youtube.retriveYoutubePageTitle(youtube_id, htmlpage, clean=True)
            outFolder = os.getcwd()
            outFilePath = os.path.join(os.getcwd(), title + '.mp4')

        outFilePath_tmp = outFilePath + ".part"
        data = None
        finished = False

        if formatcode not in FMT_MAP.keys():
            finished = Youtube.downloadYoutubeVideo(youtube_id, '22', outFilePath_tmp)
            if not finished:
                finished = Youtube.downloadYoutubeVideo(youtube_id, '18', outFilePath_tmp)
        else:
            finished = Youtube.downloadYoutubeVideo(youtube_id, formatcode, outFilePath_tmp)

        # if file exist on local node, do not download FLV one more.
        if os.path.isfile(outFilePath):
            LOG.warning("We already have %s. Not retrieving" % (outFilePath))
            finished = True
            return finished

        if finished:
            os.rename(outFilePath_tmp, outFilePath)
        else:
            try:
                os.remove(outFilePath_tmp)
            except OSError:
                pass
        return finished


    @staticmethod
    def get_playlist_video_ids(playlist_id, html=None):
        """
        GET playlist_id
        RETURNS list() of all video ids from that playlist

        Explanation:
          for the URL http://www.youtube.com/view_play_list?p=8EE54070B382E73A
          'playlist_id' shold be '8EE54070B382E73A'
        """
        playlist_url = "http://www.youtube.com/view_play_list?p=%s" % playlist_id

        if not html:
            LOG.info('Downloading playlist %s from "%s"' % (playlist_id, playlist_url))
            html = urllib2.urlopen(playlist_url).read()
            #html = open('youtube.playlist.example.html').read()
        ypp = YoutubePlaylistHTMLParser()
        ypp.feed(html)
        return ypp.PLAYLIST_ITEMS



if __name__ == "__main__":
    LOG.setLevel(logging.DEBUG)
    usage = "usage: %prog <youtube-video-id> [youtube-video-id,..]\n       %prog -p <playlist id>\n\nKnown video format codes:\n" + str(FMT_MAP.items())
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--playlist", dest="playlist",
            help="Download all playlist videos to the current directory", default=None)
    parser.add_option("-f", "--formatcode", dest="formatcode",
            help="Download video of the specific format", default=None)

    (options, args) = parser.parse_args()
    try:
        if options.playlist:
            for vID in Youtube.get_playlist_video_ids(options.playlist):
                Youtube.run(vID, formatcode=options.formatcode)
        elif len(args) > 0:
            for vID in args:
                Youtube.run(vID, formatcode=options.formatcode)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print "\nThank you for flying with youtube.py. Bye-bye."
        sys.exit(1)

