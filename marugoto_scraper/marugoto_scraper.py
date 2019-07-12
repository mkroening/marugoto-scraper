#!/usr/bin/env python3
import csv
import email.utils
import json
import logging
import os
import re
import shutil
import time
from typing import Dict, Iterable, Iterator, List, Sequence

from requests import Session
from requests.exceptions import HTTPError
from requests_futures.sessions import FuturesSession

logging.basicConfig(level=logging.INFO)

delimiter = '|'

base_url = 'https://words.marugotoweb.jp'
base_name = 'MARUGOTO-NO-KOTOBA'

words_api_url = base_url + '/SearchCategoryAPI'


def words_api_params(language_id: str,
                     level_id: str,
                     topics: Sequence[int] = None,
                     lessons: Sequence[int] = None,
                     texts: Sequence[str] = None) -> Dict[str, str]:
    if topics is None:
        topics = range(1, 10)
    if lessons is None:
        lessons = range(1, 19)
    if texts is None:
        texts = ['act', 'comp', 'vocab']
    return {
        'lv': level_id,
        'tp': ','.join(str(topic) for topic in topics),
        'ls': ','.join(str(lesson) for lesson in lessons),
        'tx': ','.join(texts),
        'ut': language_id
    }


audio_path_prefix = '/res/keyword/audio/'
audio_pattern = re.compile('^([^_]+)-([0-9]+)$')
audio_extension = '.mp3'


def audio_filename(raw_id: str) -> str:
    return audio_pattern.sub(r'\1W_\2', raw_id) + audio_extension


def get_audio_path(raw_id: str) -> str:
    return audio_path_prefix + audio_pattern.sub(r'\1W/\1W_\2',
                                                 raw_id) + audio_extension


def extract_tags(attributes: Dict[str, Dict[str, str]]) -> List[str]:
    mapped_attributes = [[
        attribute['level'], attribute['utext'], 'Topic' + attribute['topic'],
        'Lesson' + attribute['lesson']
    ] for attribute in attributes]
    flat_attributes = [
        attribute for sublist in mapped_attributes for attribute in sublist
    ]
    return sorted(list(set(flat_attributes)))


def extract_rows(json_rep: dict) -> Iterator[List[str]]:
    for word in json_rep['DATA']:
        yield [
            word['RAWID'], word['KANA'], word['KANJI'], word['ROMAJI'],
            word['UWRD'], '[sound:' + audio_filename(word['RAWID']) + ']',
            ' '.join(extract_tags(word['ATTR']))
        ]


def is_downloaded(http_headers: Dict[str, str], path: str) -> bool:
    if not os.path.isfile(path):
        return False
    local_file_size = os.path.getsize(path)
    online_file_size = int(http_headers['Content-Length'])
    if local_file_size != online_file_size:
        return False
    local_modified_time = os.path.getmtime(path)
    online_modified_time = time.mktime(
        email.utils.parsedate(http_headers['Last-Modified']))
    if local_modified_time != online_modified_time:
        return False
    return True


def download_audio(raw_ids: Iterable[str], prefix: str) -> None:
    """Download audio files corresponding to raw_ids to prefix.
    """
    if not os.path.isdir(prefix):
        os.makedirs(prefix)
    session = FuturesSession()
    futures = {
        raw_id: session.get(base_url + get_audio_path(raw_id), stream=True)
        for raw_id in raw_ids
    }
    for raw_id, future in futures.items():
        local_path = os.path.join(prefix, audio_filename(raw_id))
        response = future.result()
        try:
            response.raise_for_status()
            if not is_downloaded(response.headers, local_path):
                logging.info('Downloading ' + local_path)
                with open(local_path, 'wb') as local_audio_file:
                    for chunk in response.iter_content(chunk_size=128):
                        local_audio_file.write(chunk)
                online_modified_time = time.mktime(
                    email.utils.parsedate(response.headers['Last-Modified']))
                os.utime(local_path,
                         (online_modified_time, online_modified_time))
            else:
                logging.debug('Already downloaded ' + local_path)
        except HTTPError:
            logging.warning('Could not download ' + audio_filename(raw_id))


available_level_ids = ['A1', 'A2-1', 'A2-2']

available_language_ids = ['en', 'es', 'id', 'th', 'zh', 'vi', 'fr']


def download_words(language_id: str,
                   level_ids: Sequence[str] = available_level_ids) -> None:
    base_path = 'words'
    session = FuturesSession()
    futures = {
        level_id: session.get(words_api_url,
                              params=words_api_params(language_id, level_id))
        for level_id in level_ids
    }
    for level_id, future in futures.items():
        if not os.path.isdir(base_path):
            os.makedirs(base_path)
        local_path = os.path.join(
            base_path, base_name + '-' + language_id + '-' + level_id + '.csv')
        logging.info('Exporting ' + language_id + '-' + level_id)
        json_rep = future.result().json()
        rows = extract_rows(json_rep)
        with open(local_path, 'w') as output_csv_file:
            writer = csv.writer(output_csv_file, delimiter=delimiter)
            writer.writerows(rows)
        logging.info('Exported to ' + local_path)


def download_audios(level_ids: Sequence[str] = available_level_ids) -> None:
    session = Session()
    for level_id in level_ids:
        json_rep = session.get(words_api_url,
                               params=words_api_params('en', level_id)).json()
        prefix = os.path.join('media', base_name + '-' + level_id)
        raw_ids = [word['RAWID'] for word in json_rep['DATA']]
        logging.info('Starting audio downloads for level ' + level_id)
        download_audio(raw_ids, prefix)
        logging.info('_audio downloads completed for level ' + level_id)


if __name__ == '__main__':
    download_words('en')
    download_audios()
