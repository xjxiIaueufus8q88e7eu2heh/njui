import requests
import json
import os
import click

cookies = {
  "__Secure-3PSID": "g.a000xAi68EEwiHpVgKOgb_0IkaVhqnDZ5lzCwhQRp8c82UzZZch8f2AzQqaJKg-B05iZm6D-ygACgYKARESARASFQHGX2Mit6lAJidyakf-DSQQ3RLMZRoVAUF8yKr7g1ZnIDE3zqNE1r1J8ZOo0076",
  "__Secure-1PSIDTS": "sidts-CjIB5H03P-AdzJTCxSMrqV3MrvhaLXDlh54-abS10xB-lGChJP5JVUEZ-kj7dhf4uOxWLhAA",
  "SAPISID": "vV-FkowIK7ScWwJW/Azy3I1xFL4tE9pMHs",
  "__Secure-1PSIDCC": "AKEyXzVyk5AFJUmI0NuS3ekkFwQcPZIbC09vPY3UXHvWEGPQ_HJy3_2os9M_bTxAI20uIleCTB15",
  "SSID": "A5QQ8kH3RspqENXL5",
  "__Secure-1PAPISID": "vV-FkowIK7ScWwJW/Azy3I1xFL4tE9pMHs",
  "__Secure-1PSID": "g.a000xAi68EEwiHpVgKOgb_0IkaVhqnDZ5lzCwhQRp8c82UzZZch8TqRoD9Yv9BQP11E6lRuz6gACgYKASMSARASFQHGX2MibIOMeMIAHC47JIC3nWJAZRoVAUF8yKqHSBH9KXhliZmpeGlJWSR60076",
  "__Secure-3PAPISID": "vV-FkowIK7ScWwJW/Azy3I1xFL4tE9pMHs",
  "__Secure-3PSIDCC": "AKEyXzVSUZYWOFjQBwQTEpoRjaOdLyLsw6gZB0e4oDh_XsoQBI-8ZLZaBjqkb1Yc-kChYMVrIA",
  "__Secure-3PSIDTS": "sidts-CjIB5H03P-AdzJTCxSMrqV3MrvhaLXDlh54-abS10xB-lGChJP5JVUEZ-kj7dhf4uOxWLhAA",
  "LOGIN_INFO": "AFmmF2swRAIgSL9JJ01yt_mRAxDNK51IBdT_pHp1CXE-Jc4EZ4m6CuACIBSzAE0jJLqohH230mwp6EBAW802qnUUI2odCV0JT3yh:QUQ3MjNmeVJKVEFoVVdlbXVpRHFNTnJ1aW5DNDNqWUxwNXFSQXdRbEpRaURydVNYMW43MGxoWkdVZmozb3M2UnR6SUR3S0QtamJSZGFJQzJBOW5IMmNSb0htc3ZRdkZDdmdpZmJObTVjcFh0R2tqb1ZLUnEtRjRUcFdrUzAwSDc3Vjg3WERudnJlakViUTZ1Z29BeHIyWUtIOENBTFZJbXNR",
  "PREF": "f6=40000400&f7=4100&tz=Asia.Calcutta&f5=20000&f4=4000000"
}

headers = {
    'Connection': 'keep-alive',
    'User-Agent': 'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
    'X-Youtube-Client-Name': '5',
    'X-Youtube-Client-Version': '20.10.4',
    'Origin': 'https://www.youtube.com',
    'X-Goog-Visitor-Id': 'CgtneWx0QzE2MmpKWSjpibnCBjIKCgJJThIEGgAgZw%3D%3D'
}

params = {
    'prettyPrint': 'false'
}

def streams(streams):
    best_video = best_audio = None
    max_video = (0, 0)
    max_audio = 0    
    for s in streams:
        mime = s.get('mimeType', '')
        if 'video/' in mime:
            res = s.get('width', 0) * s.get('height', 0)
            br = s.get('bitrate', 0)
            if res > max_video[0] or (res == max_video[0] and br > max_video[1]):
                best_video = s
                max_video = (res, br)
        elif 'audio/' in mime and "mp4a" in mime:
            br = s.get('bitrate', 0)
            if br > max_audio:
                best_audio = s
                max_audio = br                
    return best_video, best_audio
    
@click.group()
def Video():
    pass

@Video.command()
@click.option("--link", "-L", type=str, required=True, help="Enter your Youtube Link")
@click.option("-ss", type=str, required=True, help="Enter input time")
@click.option("-to", type=str, required=True, help="Enter output time")
@click.option("--output", "-O", type=str, required=True, help="Enter Output filename")
def yt(link, output, ss, to):
    """Download youtube videos"""
    if "?" in link:
        video_id = link.split("?")[0].split("/")[-1]
    else:
        video_id = link.split("/")[-1]
    json_data = {
        'context': {
            'client': {
                'clientName': 'IOS',
                'clientVersion': '20.10.4',
                'deviceMake': 'Apple',
                'deviceModel': 'iPhone16,2',
                'userAgent': 'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)',
                'osName': 'iPhone',
                'osVersion': '18.3.2.22D82',
                'hl': 'en',
                'timeZone': 'UTC',
                'utcOffsetMinutes': 0,
            },
        },
        'videoId': f"{video_id}",
        'playbackContext': {
            'contentPlaybackContext': {
                'html5Preference': 'HTML5_PREF_WANTS',
                'signatureTimestamp': 20249,
            },
        },
        'contentCheckOk': True,
        'racyCheckOk': True,
    }
    response = requests.post(
            'https://www.youtube.com/youtubei/v1/player',
            params=params,
            cookies=cookies,
            headers=headers,
            json=json_data,
    )
   
    video, audio = streams(json.loads(response.text)["streamingData"]["adaptiveFormats"])
    print("VIDEO   : ", video)
    os.system(f"ffmpeg -ss {ss} -to {to} -i \"{video['url']}\" -ss {ss} -to {to} -i \"{audio['url']}\" -c copy -preset ultrafast {output}")
if __name__ == '__main__':
    try:
        yt()
    except (KeyError, NameError):
        os.system("Quality Not Available")
