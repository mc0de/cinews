#!/usr/bin/env python3

from bs4 import BeautifulSoup as Soup
from multiprocessing import Pool
from operator import itemgetter
from datetime import datetime
from slugify import slugify
import requests
import time
import sys
import io
import argparse
import sqlite3
import os


sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', line_buffering=True)
headers = {'Accept-Language': 'en-US'}


class YouTube(object):
    def __init__(self, id, is_user):
        super(YouTube, self).__init__()
        self.id = id
        self.is_user = is_user
        self.url = None

    def get_source_videos(self):
        if self.is_user is True:
            self.url = f'https://www.youtube.com/user/{self.id}/videos'
        else:
            self.url = f'https://www.youtube.com/channel/{self.id}/videos'

        if args.no_headings is not True:
            print(f'{args.module}> Fetching {self.url} ...')
        page = requests.get(self.url, headers=headers)
        channel_title = Soup(page.text, 'html5lib').findAll(attrs={'property': 'og:title'})[0]['content']
        print(channel_title)

        videos = [item['data-context-item-id'] for item in Soup(page.text, 'html5lib').findAll(attrs={'data-context-item-id': True})]

        return (channel_title, videos)

    def handle(self, video, channel_title):
        lite = SQL(channel_title, 'youtube')

        if lite.exists(video):
            return

        url = f'https://www.youtube.com/watch?v={video}'
        page = requests.get(url, headers=headers)

        try:
            upload_date = Soup(page.text, 'html5lib').select('.watch-time-text')[0].contents[0]
        except IndexError:
            return

        upload_date = upload_date.lstrip('Published on ')
        upload_date = upload_date.lstrip('Streamed live on ')

        try:
            upload_date = str(datetime.strptime(upload_date, '%b %d, %Y').date())
        except ValueError:
            return

        content_title = Soup(page.text, 'html5lib').findAll(attrs={'property': 'og:title'})[0]['content']
        entity = (video, upload_date, content_title)
        lite.create(*entity)

        return entity

    def fetch(self):
        channel_title, videos = self.get_source_videos()
        pool = Pool(processes=10)
        promises = []

        for video in videos:
            promises.append(pool.apply_async(func=self.handle, args=(video, channel_title)))

        pool.close()
        pool.join()

        result = [i for i in [i.get() for i in promises] if i]
        sorted_list = sorted(result, reverse=True, key=itemgetter(1))

        for x in sorted_list:
            video, upload_date, content_title = x
            print(f'{video:14} {upload_date} {content_title}')

        return len(sorted_list)


class Bitchute(object):
    def __init__(self, id):
        super(Bitchute, self).__init__()
        self.id = id
        self.url = f'https://www.bitchute.com/channel/{self.id}/'

    def fetch(self):
        aggregate = []
        if args.no_headings is not True:
            print(f'{args.module}> Fetching {self.url} ...')
        page = requests.get(self.url, headers=headers)
        channel_title = Soup(page.text, 'html5lib').findAll(attrs={'property': 'og:title'})[0]['content']
        print(channel_title)
        text_containers = Soup(page.text, 'html5lib').select('.channel-videos-text-container')

        lite = SQL(channel_title, 'bitchute')
        for container in text_containers:
            a = container.select('.channel-videos-title .spa')

            video = a[0]['href'].split('/')[2]

            upload_date = container.select('.channel-videos-details.text-right.hidden-xs span')[0].contents[0]
            upload_date = str(datetime.strptime(upload_date, '%b %d, %Y').date())

            content_title = a[0].contents[0]

            entity = (video, upload_date, content_title)

            if lite.exists(video):
                continue

            lite.create(*entity)
            aggregate.append(entity)
            print(f'{video:14} {upload_date} {content_title}')
        return len(aggregate)


class SQL(object):
    def __init__(self, channel, module):
        super(SQL, self).__init__()
        self.channel = channel
        self.module = module
        self.path = os.path.join(os.path.expanduser("~"), '.cinews', 'index')
        self.filename = f'{slugify(channel, separator="_")}.{self.module}.sqlite'
        self.dest = os.path.join(self.path, self.filename)
        self.__connection = None
        self.__cursor = None
        self.__table = 'data'

        if not os.path.isdir(self.path):
            os.makedirs(self.path, mode=0o644)
        if not os.path.exists(self.dest):
            self.connect()
            self.create_table()
        else:
            self.connect()

    def connect(self):
        try:
            self.__connection = sqlite3.connect(self.dest)
            self.__cursor = self.__connection.cursor()
        except Exception:
            raise

    def execute(self, query, param=None):
        try:
            if param is not None:
                self.__cursor.execute(query, param)
            else:
                self.__cursor.execute(query)
        except Exception:
            raise

    def close(self):
        try:
            self.__cursor.close()
        except Exception:
            raise

    def create_table(self):
        try:
            query = f"""CREATE TABLE {self.__table} (
                video_id TEXT PRIMARY KEY,
                date TEXT,
                title TEXT,
                created_at TEXT
            );"""
            self.execute(query)
        except Exception:
            raise

    def create(self, video_id, date, title):
        try:
            query = f'INSERT INTO {self.__table}(video_id, date, title, created_at) VALUES (?, ?, ?, ?);'
            self.execute(query, (video_id, date, title, datetime.now().strftime('%Y-%m-%d')))
            self.__connection.commit()
        except sqlite3.OperationalError:
            pass

    def find(self, video_id):
        return self.where('video_id', video_id)

    def where(self, column, value, operator='='):
        query = f'SELECT * FROM {self.__table} WHERE {column} {operator} ?;'
        self.execute(query, (value,))
        return self.__cursor.fetchall()

    def exists(self, video_id):
        return len(self.find(video_id)) > 0

    def update(self, video_id, date, title):
        query = F"""UPDATE {self.__table}
            SET date = ?,
                title = ?
            WHERE video_id = ?;"""
        self.execute(query, (date, title, video_id))
        self.__connection.commit()


def run_youtube_module():
    if args.user_id:
        module = YouTube(id=args.user_id, is_user=True)
    else:
        module = YouTube(id=args.channel_id, is_user=False)

    return module.fetch()


def run_bitchute_module():
    module = Bitchute(args.channel_id)

    return module.fetch()


def main(args):
    start = time.time()

    videos_fetched = args.func()
    if args.no_headings is not True:
        print(f'Fetched {videos_fetched} new videos in {time.time() - start:.1f}s.')
    exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        prog='cinews',
        description='Fetch newest videos from web.')
    parser.add_argument('-s', '--no-headings', action='store_true', help="Removes fetching header and fetched footer.")

    subparsers = parser.add_subparsers(title='modules', dest='module', help='Run video module', required=True)

    # YouTube section
    parser_yt = subparsers.add_parser('youtube', help='Fetches from youtube.')
    group_yt = parser_yt.add_mutually_exclusive_group(required=True)
    group_yt.add_argument('-u', '--user-id', type=str, help='Youtube user id')
    group_yt.add_argument('-c', '--channel-id', type=str, help='Youtube channel id')
    parser_yt.set_defaults(func=run_youtube_module)

    # Bitchute section
    parser_bc = subparsers.add_parser('bitchute', help='Fetches from bitchute.')
    parser_bc.add_argument('-c', '--channel-id', type=str, help='Bitchute channel id', required=True)
    parser_bc.set_defaults(func=run_bitchute_module)

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        parser.exit()
    return args


if __name__ == '__main__':
    args = parse_args()
    main(args)
