# Marugoto Scraper

This script scrapes [MARUGOTO-NO-KOTOBA](https://words.marugotoweb.jp). The
extracted words and their audio files are being converted into
[Anki](https://apps.ankiweb.net/) Notes and being saved as
`Pacakged Anki Deck/Collection` (`.apkg`).

## Usage

Run the script with:

```bash
$ pipenv install
$ pipenv run python marugoto_scraper/marugoto_scraper.py
```

It will create the following files:

```bash
MARUGOTO-NO-KOTOBA-${lang}.apkg
media/
    ${level}W_${rawAudioIDs}.mp3
```

Import `MARUGOTO-NO-KOTOBA-${lang}.apkg` in anki.

## License

[GPL3](LICENSE.md)
