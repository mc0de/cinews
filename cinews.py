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


def get_source_videos(id=None, user=True):
    if user is True:
        url = f'https://www.youtube.com/user/{id}/videos'
    else:
        url = f'https://www.youtube.com/channel/{id}/videos'

    print(f'Fetching {url} ...')
    page = requests.get(url, headers=headers)

    return [item['data-context-item-id'] for item in Soup(page.text, 'html5lib').findAll(attrs={'data-context-item-id': True})]


def handle(video):
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


def main(args):
    start = time.time()

    if args.user_id:
        videos = get_source_videos(id=args.user_id, user=True)
    else:
        videos = get_source_videos(id=args.channel_id, user=False)

    pool = Pool(processes=10)
    promises = []

    for video in videos:
        promises.append(pool.apply_async(func=handle, args=(video,)))

    pool.close()
    pool.join()

    result = [i for i in [i.get() for i in promises] if i]
    sorted_list = sorted(result, reverse=True, key=itemgetter(1))

    for x in sorted_list:
        print(*x)

    print(f'Fetched {len(sorted_list)} valid videos in {time.time() - start:.1f}s.')
    exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        prog='cinews',
        description='Fetch youtube videos by user or channel id.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-u', '--user-id', type=str, help='Youtube user id')
    group.add_argument('-c', '--channel-id', type=str, help='Youtube channel id')
    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.print_help()
        parser.exit()
    return args


if __name__ == '__main__':
    args = parse_args()
    main(args)
