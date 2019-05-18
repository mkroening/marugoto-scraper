# Marugoto Scraper

This script scrapes [MARUGOTO-NO-KOTOBA](https://words.marugotoweb.jp). The extracted words are available as [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) and are easy to import in [Anki](https://apps.ankiweb.net/). Audio files are downloaded as well and are referenced in the CSV.

## Requirements

* [Python 3](https://www.python.org/)

## Usage

Run the script with:

```bash
$ python3 marugoto-scraper
```

It will create the following layout:

```bash
marugoto-scraper/
    media/
        MARUGOTO-NO-KOTOBA-${level}/
            ${level}W_${rawAudioIDs}.mp3
    words/
        MARUGOTO-NO-KOTOBA-${lang}-${level}.csv
```

With the CSV being formatted like this:

```csv
rawID|かな|漢字・かな|ローマ字|翻訳|音声|タグ
rawID|kana|kanji kana|romaji|translation|speech|tags
```

You can use existing note types and card types from [MARUGOTO-NO-KOTOBA.apkg](MARUGOTO-NO-KOTOBA.apkg). Just delete the placeholder card.

See [Importing text files](https://apps.ankiweb.net/docs/manual.html#importing-text-files) (use `|` as delimiter) and [Importing Media](https://apps.ankiweb.net/docs/manual.html#importing-media).

## License

[GPL3](LICENSE.md)
