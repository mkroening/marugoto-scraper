#!/usr/bin/env python3
import csv
import email.utils
import json
import logging
import os
import re
import shutil
import time
from typing import Dict, List, Sequence

from requests import Session
from requests.exceptions import HTTPError

logging.basicConfig(level=logging.INFO)

delimiter = '|'

base_url = 'https://words.marugotoweb.jp/'
base_name = 'MARUGOTO-NO-KOTOBA'


def level_query(level_id: str) -> str:
    return '&lv=' + level_id


def topic_query(topics: Sequence[int] = None) -> str:
    if topics is None:
        topics = range(1, 10)
    return '&tp=' + ','.join(str(i) for i in topics)


def lesson_query(lessons: Sequence[int] = None) -> str:
    if lessons is None:
        lessons = range(1, 19)
    return '&ls=' + ','.join(str(i) for i in lessons)


def text_query(texts: Sequence[str] = None) -> str:
    if texts is None:
        texts = ['act', 'comp', 'vocab']
    return '&tx=' + ','.join(texts)


def language_query(language_id: str) -> str:
    return '&ut=' + language_id


def words_url(language_id: str,
              level_id: str,
              topics: Sequence[int] = None,
              lessons: Sequence[int] = None,
              texts: Sequence[str] = None) -> str:
    return base_url + 'SearchCategoryAPI?' + level_query(
        level_id) + topic_query(topics) + lesson_query(lessons) + text_query(
            texts) + language_query(language_id)


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


def extract_rows(json_rep: dict) -> List[List[str]]:
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


def download_all_audio(json_rep, base_path: str) -> None:
    logging.info('Starting audio downloads for level ' + json_rep['LV'])
    if not os.path.isdir(base_path):
        os.makedirs(base_path)
    session = Session()
    for word in json_rep['DATA']:
        online_url = base_url + get_audio_path(word['RAWID'])
        local_path = os.path.join(base_path, audio_filename(word['RAWID']))
        response = session.get(online_url, stream=True)
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
            logging.warning('Could not download ' +
                            audio_filename(word['RAWID']))
    logging.info('_audio downloads completed for level ' + json_rep['LV'])


available_level_ids = ['A1', 'A2-1', 'A2-2']

available_language_ids = ['en', 'es', 'id', 'th', 'zh', 'vi', 'fr']


def download_words(level_ids: Sequence[str] = available_level_ids,
                   language_ids: Sequence[str] = available_language_ids
                   ) -> None:
    base_path = 'words'
    session = Session()
    for language_id in language_ids:
        for level_id in level_ids:
            if not os.path.isdir(base_path):
                os.makedirs(base_path)
            local_path = os.path.join(
                base_path,
                base_name + '-' + language_id + '-' + level_id + '.csv')
            logging.info('Exporting ' + language_id + '-' + level_id)
            json_rep = session.get(words_url(language_id, level_id)).json()
            rows = extract_rows(json_rep)
            with open(local_path, 'w') as output_csv_file:
                writer = csv.writer(output_csv_file, delimiter=delimiter)
                writer.writerows(rows)
            logging.info('Exported to ' + local_path)


def download_audios(level_ids: Sequence[str] = available_level_ids) -> None:
    session = Session()
    for level_id in level_ids:
        json_rep = session.get(words_url('en', level_id)).json()
        download_all_audio(json_rep,
                           os.path.join('media', base_name + '-' + level_id))


if __name__ == '__main__':
    download_words()
    download_audios()
