test_server 的片源目录
======================

本目录里放着一个**测试视频 test.mp4**(30 秒 / 640x360 / H.264 + AAC,约 450KB),
所以 /play 给的地址(/media/test.mp4?vg=1)直接指向它:有画面、有声音,能播、能暂停、
能拖进度、能换集 —— 也就是"取流到播放"这条链路用的是真视频。

地址末尾那个 ?vg=1 不是装饰:客户端拿到地址后会拼成 "<地址>&<单集id>=vg" 再交给播放器,
地址里没有 "?" 时这段尾巴会粘在路径上(…/media/test.mp4&tstc0001_v001=vg),
服务端就只能 404,播放器什么也放不出来。带 query 时拼出来的仍是合法 URL,路径保持干净。

它长什么样:一段标准的彩条测试图案(画面上有随时间走的计数),
左上角写着 test_server - TEST VIDEO —— 一眼就能看出这是测试源,不是真片。

想换成别的片源
--------------
把任意一个视频文件丢进本目录即可,app.py 会自动改用它
(多个文件时按文件名排序取第一个;想让它当片源,把 test.mp4 删掉或改名):

    test_server/media/demo.mp4

支持的扩展名:mp4 / m4v / webm / mkv / mov / flv / ts(视频)
                wav / mp3 / m4a / aac(音频)
本文件(.txt)与 README 会被忽略,不会被当片源。

把 test.mp4 删掉会怎样
----------------------
不会报错:此时 /media/stream 会退回去返回一段**现场合成的 WAV 音轨**
(见 tone.py,每秒换音高,能听出进度在走),只是没有画面。
所以"有片源就看画面,没片源就听声音",两种都能验证取流是否通。

怎么重新生成 test.mp4
--------------------
用仓库自带的 ffmpeg(utility/ffmpeg.exe),在项目根目录敲:

    utility\ffmpeg.exe -y -f lavfi -i "testsrc=size=640x360:rate=25:duration=30" ^
      -f lavfi -i "sine=frequency=440:sample_rate=44100:duration=30" ^
      -vf "drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='test_server - TEST VIDEO':fontsize=26:fontcolor=white:x=20:y=20:box=1:boxcolor=black@0.55" ^
      -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 30 -g 50 ^
      -c:a aac -b:a 64k -movflags +faststart -shortest test_server\media\test.mp4

注意:这个目录只影响"放什么",不影响任何接口结构 ——
换成真片源后,/play、/media/stream(Range 拖动)走的还是同一条链路。
