#!/usr/bin/env python3
"""
Generate native Japanese pronunciation audio (one MP3 per word) into audio/.

Uses Google Translate's public TTS endpoint with the kana reading of each word
(kana gives an accurate reading; feeding raw romaji can mispronounce). Files are
named audio/<english>.mp3 to match how study.html looks them up
(audio/${item.en.toLowerCase()}.mp3). Requires internet access at generation time
only — the study itself serves the MP3s locally.

Run:  python make_audio.py
"""
import os
import time
import urllib.parse
import urllib.request

# english filename stem -> kana (accurate native reading)
KANA = {
    "jon": "ジョン", "mia": "ミア", "he": "かれ", "she": "かのじょ",
    "apple": "りんご", "egg": "たまご", "rice": "ごはん", "cake": "ケーキ",
    "meat": "にく", "fish": "さかな", "chicken": "とりにく", "strawberry": "いちご",
    "carrot": "にんじん", "book": "ほん", "box": "はこ", "chair": "いす",
    "stone": "いし", "bag": "かばん", "key": "かぎ", "clock": "とけい",
    "shoe": "くつ", "umbrella": "かさ", "see": "みる", "move": "うごかす",
    "drop": "おとす", "draw": "かく",
}

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120 Safari/537.36"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")


def main():
    os.makedirs(OUT, exist_ok=True)
    ok, bad = 0, []
    for en, kana in KANA.items():
        q = urllib.parse.quote(kana)
        url = ("https://translate.google.com/translate_tts"
               f"?ie=UTF-8&client=tw-ob&tl=ja&q={q}")
        try:
            data = urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=20).read()
            if len(data) < 800:
                bad.append((en, f"suspiciously small ({len(data)} bytes)"))
                continue
            with open(os.path.join(OUT, f"{en}.mp3"), "wb") as f:
                f.write(data)
            ok += 1
            time.sleep(0.3)  # be polite to the endpoint
        except Exception as e:  # noqa: BLE001
            bad.append((en, str(e)))
    print(f"generated {ok} / {len(KANA)} into {OUT}")
    if bad:
        print("FAILED:", bad)


if __name__ == "__main__":
    main()
