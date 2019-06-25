import requests

from flask import Flask
from flask import render_template
from flask import Response, request
from flask import abort, jsonify
from subprocess import Popen, PIPE, DEVNULL
from threading import Thread
from you_get.extractors.bilibili import Bilibili

app = Flask(__name__)
debug = app.logger.debug

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/resolve/<path:bpath>')
def resolve(bpath):
    video = Bilibili('https://www.bilibili.com/{}'.format(bpath))
    video.prepare()
    video.extract()
    '''
    # select best quality
    qualitys = [st['id'] for st in Bilibili.stream_types]                                                                                                 
    quality = video.streams.keys()
    for q in qualitys: 
        if q in quality: 
            quality = q
            break
    srcs = video.streams[quality]['src']
    '''
    return jsonify(video.streams)


@app.route('/video/mkv/<protocol>/<path:vpath>')
def proxy_video(protocol, vpath, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
                'Referer': 'https://www.bilibili.com/'
            }):
    url_rebuilt = '{}://{}?{}'.format(protocol, vpath, request.query_string.decode())
    debug('rebuild url: {}'.format(url_rebuilt))

    resp = requests.get(url_rebuilt, headers=headers, stream=True)

    ffmpeg = Popen(['ffmpeg', '-i', '-', '-vcodec', 'copy', '-acodec', 'aac', '-f', 'matroska', 'pipe:1'], \
         stdin=PIPE, stdout=PIPE, stderr=DEVNULL)
    def ffmpeg_input():
        for chunk in resp.iter_content(chunk_size=4096):
            ffmpeg.stdin.write(chunk)
    def generator():
        while True:
            data = ffmpeg.stdout.read(4096)
            yield data
    if resp.status_code == 200:
        Thread(target=ffmpeg_input).start()
        return Response(generator(), mimetype='video/x-matroska')
    else:
        abort(resp.status_code)

if __name__ == '__main__':
    app.run('0.0.0.0', 8787, debug=True)
