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
import urllib.request

logging.basicConfig(level=logging.INFO)

delimiter = '|'

base_url = 'https://words.marugotoweb.jp/'
base_name = 'MARUGOTO-NO-KOTOBA'


def level_query(level_id: str) -> str:
    return '&lv=' + level_id


topic_query = '&tp=1,2,3,4,5,6,7,8,9'

lesson_query = '&ls=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18'

text_query = '&tx=act,comp,vocab'


def language_query(language_id: str) -> str:
    return '&ut=' + language_id


def words_url(language_id: str, level_id: str) -> str:
    return base_url + 'SearchCategoryAPI?' + level_query(
        level_id) + topic_query + lesson_query + text_query + language_query(
            language_id)


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


def is_downloaded(online_file_info, path: str) -> bool:
    if not os.path.isfile(path):
        return False
    local_file_size = os.path.getsize(path)
    online_file_size = int(online_file_info['Content-Length'])
    if local_file_size != online_file_size:
        return False
    local_modified_time = os.path.getmtime(path)
    online_modified_time = time.mktime(
        email.utils.parsedate(online_file_info['Last-Modified']))
    if local_modified_time != online_modified_time:
        return False
    return True


def download_audio(raw_id: str, base_path: str) -> None:
    online_url = base_url + get_audio_path(raw_id)
    if not os.path.isdir(base_path):
        os.makedirs(base_path)
    local_path = os.path.join(base_path, audio_filename(raw_id))
    with urllib.request.urlopen(online_url) as online_audio_file:
        online_file_info = online_audio_file.info()
        if not is_downloaded(online_file_info, local_path):
            logging.info('Downloading ' + local_path)
            online_modified_time = time.mktime(
                email.utils.parsedate(online_file_info['Last-Modified']))
            with open(local_path, 'wb') as local_audio_file:
                shutil.copyfileobj(online_audio_file, local_audio_file)
            os.utime(local_path, (online_modified_time, online_modified_time))
        else:
            logging.debug('Already downloaded ' + local_path)


def download_all_audio(json_rep, base_path: str) -> None:
    logging.info('Starting audio downloads for level ' + json_rep['LV'])
    for word in json_rep['DATA']:
        try:
            download_audio(word['RAWID'], base_path)
        except urllib.error.HTTPError:
            logging.warning('Could not download ' +
                            audio_filename(word['RAWID']))
    logging.info('_audio downloads completed for level ' + json_rep['LV'])


available_level_ids = ['A1', 'A2-1', 'A2-2']

available_language_ids = ['en', 'es', 'id', 'th', 'zh', 'vi', 'fr']


def download_words(level_ids: Sequence[str] = available_level_ids,
                   language_ids: Sequence[str] = available_language_ids
                   ) -> None:
    base_path = 'words'
    for language_id in language_ids:
        for level_id in level_ids:
            if not os.path.isdir(base_path):
                os.makedirs(base_path)
            local_path = os.path.join(
                base_path,
                base_name + '-' + language_id + '-' + level_id + '.csv')
            logging.info('Exporting ' + language_id + '-' + level_id)
            with urllib.request.urlopen(words_url(
                    language_id, level_id)) as input_json_file:
                json_rep = json.loads(input_json_file.read().decode('utf-8'))
            rows = extract_rows(json_rep)
            with open(local_path, 'w') as output_csv_file:
                writer = csv.writer(output_csv_file, delimiter=delimiter)
                writer.writerows(rows)
            logging.info('Exported to ' + local_path)


def download_audios(level_ids: Sequence[str] = available_level_ids) -> None:
    for level_id in level_ids:
        with urllib.request.urlopen(words_url('en',
                                              level_id)) as input_json_file:
            json_rep = json.loads(input_json_file.read().decode('utf-8'))
        download_all_audio(json_rep,
                           os.path.join('media', base_name + '-' + level_id))


if __name__ == '__main__':
    download_words()
    download_audios()
