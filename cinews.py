#!/usr/bin/env python3

from bs4 import BeautifulSoup as Soup
from multiprocessing import Pool
from operator import itemgetter
import requests
import datetime
import time
import sys
import io
import argparse


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

        return [item['data-context-item-id'] for item in Soup(page.text, 'html5lib').findAll(attrs={'data-context-item-id': True})]

    def handle(self, video):
        url = f'https://www.youtube.com/watch?v={video}'
        page = requests.get(url, headers=headers)

        try:
            upload_date = Soup(page.text, 'html5lib').select('.watch-time-text')[0].contents[0]
        except IndexError:
            return

        upload_date = upload_date.lstrip('Published on ')
        upload_date = upload_date.lstrip('Streamed live on ')

        try:
            upload_date = str(datetime.datetime.strptime(upload_date, '%b %d, %Y').date())
        except ValueError:
            return

        content_title = Soup(page.text, 'html5lib').findAll(attrs={'property': 'og:title'})[0]['content']

        return (video, upload_date, content_title)

    def fetch(self):
        videos = self.get_source_videos()
        pool = Pool(processes=10)
        promises = []

        for video in videos:
            promises.append(pool.apply_async(func=self.handle, args=(video,)))

        pool.close()
        pool.join()

        result = [i for i in [i.get() for i in promises] if i]
        sorted_list = sorted(result, reverse=True, key=itemgetter(1))

        for x in sorted_list:
            print(*x)

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
        # print(text_containers[0].select('.channel-videos-title .spa')[0]['href'])
        # debug_output(text_containers[0])
        for container in text_containers:
            a = container.select('.channel-videos-title .spa')

            video = a[0]['href'].split('/')[2]

            upload_date = container.select('.channel-videos-details.text-right.hidden-xs span')[0].contents[0]
            upload_date = str(datetime.datetime.strptime(upload_date, '%b %d, %Y').date())

            content_title = a[0].contents[0]

            entity = (video, upload_date, content_title)
            aggregate.append(entity)
            print(f'{video:12} {upload_date} {content_title}')
        return len(aggregate)


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
        print(f'Fetched {videos_fetched} valid videos in {time.time() - start:.1f}s.')
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
