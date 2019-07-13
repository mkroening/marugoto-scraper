#!/usr/bin/env python3
import email.utils
import json
import logging
import os
import re
import time
from typing import Dict, Iterable, Iterator, List, Sequence, Union

import requests
from requests.exceptions import HTTPError
from requests_futures.sessions import FuturesSession

import genanki
from genanki import Deck, Model, Note, Package

Words = Iterable[Dict[str, Union[str, None, List[Dict[str, str]]]]]

logging.basicConfig(level=logging.INFO)

delimiter = '|'

base_url = 'https://words.marugotoweb.jp'
base_name = 'MARUGOTO-NO-KOTOBA'

words_api_url = base_url + '/SearchCategoryAPI'


def words_api_params(language_id: str = 'en',
                     level_ids: Sequence[str] = None,
                     topics: Sequence[int] = None,
                     lessons: Sequence[int] = None,
                     texts: Sequence[str] = None) -> Dict[str, str]:
    if level_ids is None:
        level_ids = ['A1', 'A2-1', 'A2-2']
    if topics is None:
        topics = range(1, 10)
    if lessons is None:
        lessons = range(1, 19)
    if texts is None:
        texts = ['act', 'comp', 'vocab']
    return {
        'lv': ','.join(level_ids),
        'tp': ','.join(str(topic) for topic in topics),
        'ls': ','.join(str(lesson) for lesson in lessons),
        'tx': ','.join(texts),
        'ut': language_id
    }


audio_base_url = base_url + '/res/keyword/audio'
audio_pattern = re.compile('^([^_]+)-([0-9]+)$')
audio_extension = '.mp3'


def audio_filename(raw_id: str) -> str:
    return audio_pattern.sub(r'\1W_\2', raw_id) + audio_extension


def audio_url(raw_id: str) -> str:
    return audio_base_url + '/' + audio_pattern.sub(r'\1W/\1W_\2',
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


def download_audio(raw_ids: Iterable[str], prefix: str = 'media') -> None:
    """Download audio files corresponding to raw_ids to prefix.
    """
    if not os.path.isdir(prefix):
        os.makedirs(prefix)
    session = FuturesSession()
    futures = {
        raw_id: session.get(audio_url(raw_id), stream=True)
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


available_language_ids = ['en', 'es', 'id', 'th', 'zh', 'vi', 'fr']

fields = """
- name: RawId
- name: 漢字・かな
- name: かな
- name: ローマ字
- name: 翻訳
- name: 音声
"""

templates = """
-
  name: Card1
  qfmt: >
    {{音声}}
    {{hint:漢字・かな}}<br/>
    {{hint:かな}}<br/>
    {{hint:ローマ字}}
  afmt: >
    {{FrontSide}}
    <hr id=answer>
      {{翻訳}}
    </hr>
-
  name: Card2
  qfmt: >
    {{漢字・かな}}<br/><br/>
    {{hint:かな}}<br/>
    {{hint:ローマ字}}
  afmt: >
    {{FrontSide}}
    <hr id=answer>
      {{音声}}
      {{翻訳}}
    </hr>
-
  name: Card3
  qfmt: >
    {{翻訳}}
  afmt: >
    {{FrontSide}}
    <hr id=answer>
      {{音声}}
      {{漢字・かな}}<br/><br/>
      {{hint:かな}}<br/>
      {{hint:ローマ字}}
    </hr>
"""

style = """
.card {
  font-size: 20px;
  text-align: center;
}
"""

model = Model(model_id=1237599646,
              name=base_name,
              fields=fields,
              templates=templates,
              css=style)


class MarugotoNote(Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


def export_words(words: Words, file: str, media_prefix: str = 'media') -> None:
    deck = Deck(deck_id=1336548074,
                name=base_name,
                description='This deck was created using Marugoto Scraper.')
    for word in words:
        deck.add_note(
            MarugotoNote(model=model,
                         fields=[
                             word['RAWID'], word['KANJI'], word['KANA'],
                             word['ROMAJI'], word['UWRD'],
                             '[sound:' + audio_filename(word['RAWID']) + ']'
                         ],
                         tags=extract_tags(word['ATTR'])))

    package = Package(deck)
    package.media_files = [
        media_prefix + '/' + audio_filename(word['RAWID']) for word in words
    ]
    package.write_to_file(file)


if __name__ == '__main__':
    language_id = 'en'
    r = requests.get(words_api_url,
                     params=words_api_params(language_id=language_id)).json()
    download_audio(word['RAWID'] for word in r['DATA'])
    export_words(r['DATA'], base_name + '-' + language_id + '.apkg')
