#!/usr/bin/env python3
import csv
import email.utils
import json
import logging
import os
import re
import shutil
import time
from typing import Dict, List
import urllib.request

logging.basicConfig(level=logging.INFO)

delimiter = '|'

baseURL = 'https://words.marugotoweb.jp/'
baseName = 'MARUGOTO-NO-KOTOBA'

levelIDs = [
    'A1',
    'A2-1',
    'A2-2'
]


def levelQuery(levelID: str) -> str:
    return '&lv=' + levelID


topicQuery = '&tp=1,2,3,4,5,6,7,8,9'

lessonQuery = '&ls=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18'

textQuery = '&tx=act,comp,vocab'

languageIDs = [
    'en',
    'es',
    'id',
    'th',
    'zh',
    'vi',
    'fr'
]


def languageQuery(languageID: str) -> str:
    return '&ut=' + languageID


def wordsURL(languageID: str, levelID: str) -> str:
    return baseURL + 'SearchCategoryAPI?' + levelQuery(levelID) + topicQuery + lessonQuery + textQuery + languageQuery(languageID)


audioPathPrefix = '/res/keyword/audio/'
audioPattern = re.compile('^([^_]+)-([0-9]+)$')
audioExtension = '.mp3'


def getAudioFilename(rawID: str) -> str:
    return audioPattern.sub(r'\1W_\2', rawID) + audioExtension


def getAudioPath(rawID: str) -> str:
    return audioPathPrefix + audioPattern.sub(r'\1W/\1W_\2', rawID) + audioExtension


def extractTags(attributes: Dict[str, Dict[str, str]]) -> List[str]:
    mappedAttributes = [[
        attribute['level'],
        attribute['utext'],
        'Topic' + attribute['topic'],
        'Lesson' + attribute['lesson']
    ] for attribute in attributes]
    flatAttributes = [
        attribute for sublist in mappedAttributes for attribute in sublist]
    return sorted(list(set(flatAttributes)))


def extractRows(jsonRep: dict) -> List[List[str]]:
    for word in jsonRep['DATA']:
        yield [
            word['RAWID'],
            word['KANA'],
            word['KANJI'],
            word['ROMAJI'],
            word['UWRD'],
            '[sound:' + getAudioFilename(word['RAWID']) + ']',
            ' '.join(extractTags(word['ATTR']))
        ]


def isDownloaded(onlineFileInfo, path: str) -> bool:
    if not os.path.isfile(path):
        return False
    localFileSize = os.path.getsize(path)
    onlineFileSize = int(onlineFileInfo['Content-Length'])
    if localFileSize != onlineFileSize:
        return False
    localModifiedTime = os.path.getmtime(path)
    onlineModifiedTime = time.mktime(
        email.utils.parsedate(onlineFileInfo['Last-Modified']))
    if localModifiedTime != onlineModifiedTime:
        return False
    return True


def downloadAudio(rawID: str, basePath: str) -> None:
    onlineURL = baseURL + getAudioPath(rawID)
    if not os.path.isdir(basePath):
        os.makedirs(basePath)
    localPath = os.path.join(basePath, getAudioFilename(rawID))
    with urllib.request.urlopen(onlineURL) as onlineAudioFile:
        onlineFileInfo = onlineAudioFile.info()
        if not isDownloaded(onlineFileInfo, localPath):
            logging.info('Downloading ' + localPath)
            onlineModifiedTime = time.mktime(
                email.utils.parsedate(onlineFileInfo['Last-Modified']))
            with open(localPath, 'wb') as localAudioFile:
                shutil.copyfileobj(onlineAudioFile, localAudioFile)
            os.utime(localPath, (onlineModifiedTime, onlineModifiedTime))
        else:
            logging.info('Already downloaded ' + localPath)


def downloadAllAudio(jsonRep, basePath: str) -> None:
    logging.info('Starting audio downloads')
    for word in jsonRep['DATA']:
        downloadAudio(word['RAWID'], basePath)
    logging.info('Audio downloads completed')


basePath = 'words'
for languageID in languageIDs:
    for levelID in levelIDs:
        if not os.path.isdir(basePath):
            os.makedirs(basePath)
        localPath = os.path.join(
            basePath, baseName + '-' + languageID + '-' + levelID + '.csv')
        logging.info('Exporting ' + languageID + '-' + levelID)
        with urllib.request.urlopen(wordsURL(languageID, levelID)) as inputJSONFile:
            jsonRep = json.loads(inputJSONFile.read().decode('utf-8'))
        rows = extractRows(jsonRep)
        with open(localPath, 'w') as outputCSVFile:
            writer = csv.writer(outputCSVFile, delimiter=delimiter)
            writer.writerows(rows)
        logging.info('Exported to ' + localPath)

for levelID in levelIDs:
    with urllib.request.urlopen(wordsURL('en', levelID)) as inputJSONFile:
        jsonRep = json.loads(inputJSONFile.read().decode('utf-8'))
    downloadAllAudio(jsonRep, os.path.join('media', baseName + '-' + levelID))
