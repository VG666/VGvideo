# -*- coding: utf-8 -*-
"""测试数据源的内容目录(test_server.catalog)

这里**没有任何网络请求**:剧集 / 单条视频 / 选集 / 弹幕 / 标题 / 直播频道 / 轮播,
全是写死在下面几张表里的假数据 —— 但**结构与真实数据源完全一致**,
所以界面(model/ + view/)拿到的东西和连 tx_server/ 时长得一模一样。

它的用处就一个:证明这个客户端是个"壳子" ——
把 config/config.json 的 vgapi.PLAY_API_BASE 指到本服务(默认 127.0.0.1:8790),
首页轮播、搜索、选集、播放、弹幕、直播全都能跑起来,而且一个字节都不出网。
反过来说,只要一个数据源照着 tx_server/ 的接口清单把这几份 JSON 喂出来,
不需要改客户端任何一行代码。

要改内容只动本文件:
    加一出戏   → 往 _DRAMAS 里加一行
    加一条视频 → 往 _VIDEOS 里加一行
    加一个直播 → 往 _LIVE 里加一行

图片与播放地址用两个"标记"表示,由 app.py 在发响应前翻成绝对地址
(目录这一层不该知道端口和域名,所以只写标记):
    cover:<种子>   封面图 → <本服务>/cover/<种子>.png
    drama:<剧集id> 详情页 → <本服务>/cover/<剧集id>.html(客户端从末尾抠剧集 id)
    stream         播放地址 → <本服务>/media/test.mp4(就是 media/ 里那份测试视频,真能播)

顺带一提,这份目录是"整份都是测试"的口径:所有片名都带"测试"两个字,
搜索框里敲"测试"(甚至空着直接回车,见 search 的默认关键词)必定搜得出东西,
首页从头到脚(大轮播 / 右侧"大家在看" / 底部一排推荐位)也都是这套测试图/测试名;
点进任意一出戏,选集列表里只有一个选项:"播放测试视频"。
"""
import hashlib

# ---------------------------------------------------------------------------
# 测试口径的两个常量(改这里就能改全站口径)
# ---------------------------------------------------------------------------
TEST_KEYWORD = "测试"            # 默认搜索词:不传关键词时按它搜,必定搜得出东西
TEST_EPISODE = "播放测试视频"     # 选集列表里那唯一一个选项:按钮上写的就是它

# ---------------------------------------------------------------------------
# 表 1:剧集(搜索结果里 kind=cover,点进去进选集页)
#   (剧集id, 剧名, 集数, 补充说明)
#   两点刻意的设计:
#     1) 剧名一律以"测试"开头 —— 界面上任何一处出现的字都自报家门,
#        也保证搜索"测试"能把这批数据全部搜出来(见 search);
#     2) 每部剧只给 1 集(集数写 1)—— 播放页的选集列表里就只有一个按钮,
#        按钮上写"播放测试视频"(见 dramas),专门用来验证"单集"这条路径。
# ---------------------------------------------------------------------------
_DRAMAS = [
    ("tstc0001", "测试剧集 01", 1, "科幻 · 测试数据"),
    ("tstc0002", "测试剧集 02", 1, "美食 · 测试数据"),
    ("tstc0003", "测试剧集 03", 1, "剧情 · 测试数据"),
    ("tstc0004", "测试剧集 04", 1, "动画 · 测试数据"),
    ("tstc0005", "测试剧集 05", 1, "奇幻 · 测试数据"),
    ("tstc0006", "测试剧集 06", 1, "纪录 · 测试数据"),
]

# ---------------------------------------------------------------------------
# 表 2:单条视频(搜索结果里 kind=video,点一下直接播)
#   (视频id, 标题, 补充说明)
# ---------------------------------------------------------------------------
_VIDEOS = [
    ("tstv0001", "测试短片:一分钟看懂数据源", "单条视频 · 测试数据"),
    ("tstv0002", "测试短片:换源只需要改一个地址", "单条视频 · 测试数据"),
    ("tstv0003", "测试短片:选集与弹幕从哪来", "单条视频 · 测试数据"),
    ("tstv0004", "测试短片:直播频道占位", "单条视频 · 测试数据"),
]

# ---------------------------------------------------------------------------
# 表 3:直播频道(按分类分组,每条 = 播放地址 / 名称 / 备注 / 封面)
#   地址写成 "stream" 标记,由 app.py 翻成本服务的 /media/stream
# ---------------------------------------------------------------------------
_LIVE = {
    "测试频道": [
        ("stream", "测试频道 A", "本地测试片源 · 可播", "cover:live-a"),
        ("stream", "测试频道 B", "本地测试片源 · 可播", "cover:live-b"),
        ("stream", "测试频道 C", "本地测试片源 · 可播", "cover:live-c"),
    ],
    "备用频道": [
        ("stream", "备用频道 X", "同一个地址,用来验证分组", "cover:live-x"),
        ("stream", "备用频道 Y", "同一个地址,用来验证分组", "cover:live-y"),
    ],
}

# ---------------------------------------------------------------------------
# 表 4:弹幕 / 评论(按 vid 的哈希从池子里稳定地挑几条)
# ---------------------------------------------------------------------------
_DANMU_POOL = [
    "这段是假的,别当真", "占位弹幕来一条", "测试数据源,正常现象",
    "画质取决于你丢进去的片源", "换源只要改 PLAY_API_BASE",
    "进度条能拖说明取流链路是通的", "声音每 5 秒会变一次,用来确认进度在走",
    "选集列表是本地生成的", "这条数据来自 test_server", "客户端一行代码都不用改",
    "结构跟真实数据源完全一致", "能播就说明壳子是好的",
]

# ---------------------------------------------------------------------------
# 轮播(首页"重磅推荐"):八条,刚好铺满客户端的一轮
#   客户端首页那三块内容全吃这一张表 —— 所以这里统一填"测试"片名:
#     左上大轮播图      ← rotation() 的 pics
#     右侧"大家在看"列表 ← rotation() 的 names
#     底下一排推荐位     ← rotation() 的 thumbs(与大轮播同图,见 rotation)
# ---------------------------------------------------------------------------
_ROTATION = [
    ("tstc0001", "测试剧集 01"), ("tstc0002", "测试剧集 02"),
    ("tstc0003", "测试剧集 03"), ("tstc0004", "测试剧集 04"),
    ("tstc0005", "测试剧集 05"), ("tstc0006", "测试剧集 06"),
    ("tstv0001", "测试短片:一分钟看懂数据源"),
    ("tstv0002", "测试短片:换源只需要改一个地址"),
]

# 搜索联想词的补充词(除了上面那些片名,再多给几个"像是能搜出东西"的词):
# 一律用能搜出结果的词 —— 本服务里片名都带"测试",所以"测试"及其变体必命中
_EXTRA_WORDS = ["测试", "测试剧集", "测试短片", "测试频道"]


def _n(seed):
    """种子 → 稳定整数(同一串每次都是同一个数,弹幕才不会每次刷新都换一批)"""
    return int(hashlib.md5(str(seed).encode("utf-8")).hexdigest()[:8], 16)


def _ep_id(cid, i):
    """单集 vid:剧集 id + 集号(6~32 位、只含字母数字下划线,和真实 vid 的约束一致)"""
    return "%s_v%03d" % (cid, i)


# ---------------------------------------------------------------- 剧集 / 视频
def dramas():
    """全部剧集(含各自的选集列表)

    测试模式下每部剧只有一个选项:选集列表里就一个按钮,写的是"播放测试视频",
    点它播的就是 media/ 里那份测试视频(见 app.py 的 /play)。
    """
    _out = []
    for _cid, _title, _eps, _desc in _DRAMAS:
        _list = [{
            "id": _ep_id(_cid, 1),
            "episode_number": TEST_EPISODE,   # 选集按钮上的字(客户端直接拿它当文本)
            "title": TEST_EPISODE,            # 播放页标题(客户端拿不到 episode_number 时退到它)
            "markLabelList": [],
            "playUrl": "",
        }]
        _out.append({"id": _cid, "title": _title, "desc": _desc, "episodes": _list})
    return _out


def videos():
    """全部单条视频"""
    return [{"id": _v, "title": _t, "desc": _d} for _v, _t, _d in _VIDEOS]


def find_cover(cid):
    """按剧集 id 找剧集;没有返回 None"""
    _c = str(cid or "").strip()
    for _it in dramas():
        if _it["id"] == _c:
            return _it
    return None


def find_video(vid):
    """按 vid 找单条视频;没有返回 None"""
    _v = str(vid or "").strip()
    for _it in videos():
        if _it["id"] == _v:
            return _it
    return None


def find_episode(vid):
    """按单集 vid 找它属于哪一出戏的哪一集;没有返回 (None, None)"""
    _v = str(vid or "").strip()
    for _it in dramas():
        for _ep in _it["episodes"]:
            if _ep["id"] == _v:
                return _it, _ep
    return None, None


def is_known(vid):
    """这个 id 认不认识(能播的 id 就这几类:单集 vid / 单条视频 id / 剧集 id)"""
    if find_episode(vid)[0] or find_video(vid):
        return True
    return bool(find_cover(vid))


# ---------------------------------------------------------------- 搜索结果
def _items():
    """搜索结果的全部条目(剧集在前、单条视频在后),img 用 cover: 标记"""
    _out = [{"kind": "cover", "id": _c, "title": _t, "img": "cover:" + _c, "desc": _d,
             "eps": int(_e)} for _c, _t, _e, _d in _DRAMAS]
    _out += [{"kind": "video", "id": _v, "title": _t, "img": "cover:" + _v, "desc": _d}
             for _v, _t, _d in _VIDEOS]
    return _out


def search(keyword, page=1, page_size=8):
    """搜一页,返回客户端约定的"标准 JSON"

    结构完全照 tx_server/sources/search.py 那份来(source/keyword/page/pages/total/items),
    客户端(model/api/search.py)与搜索页因此一行都不用改。

    默认关键词:没传 q / 传了空串时按 TEST_KEYWORD("测试") 搜 ——
    本服务所有片名都带"测试",所以空搜索框回车必定出结果,结果里用
    default_keyword=true 说明"这是替你填的关键词",方便排查。

    一点小体贴:本服务里没有"搜不到"这件事 —— 关键词没命中任何片名时,
    就把全部条目当作兜底结果返回,并在结果里带一个 fallback=true 说明这是兜底,
    免得拿它测界面的人以为是自己配错了。
    """
    _kw = str(keyword or "").strip()
    _defaulted = False
    if not _kw:
        _kw, _defaulted = TEST_KEYWORD, True
    _pg = max(1, int(page or 1))
    _size = max(1, int(page_size or 8))
    _all = _items()
    _low = _kw.lower()
    _hit = [_x for _x in _all
            if not _low or _low in _x["title"].lower() or _low in str(_x["desc"]).lower() or _low == _x["id"].lower()]
    _fallback = not _hit
    if _fallback:
        _hit = list(_all)
    _pages = max(1, (len(_hit) + _size - 1) // _size)
    _begin = (_pg - 1) * _size
    return {
        "source": "test-source",
        "keyword": _kw,
        "default_keyword": _defaulted,              # true = 关键词是服务端替你填的("测试")
        "page": _pg,
        "pages": _pages,
        "total": len(_hit),
        "fallback": _fallback,
        "items": [dict(_x) for _x in _hit[_begin:_begin + _size]],
    }


# ---------------------------------------------------------------- 选集 / 弹幕 / 标题
def episodes(cid):
    """选集:返回与腾讯同构的 JSON 文本(PlaylistItem / videoPlayList),认不出来就给空串

    测试模式下只有一项:按钮上写"播放测试视频"(TEST_EPISODE),
    点它取到的就是 media/ 里那份测试视频 —— 单集路径一条就够验。
    """
    _it = find_cover(cid)
    if not _it:
        return ""
    from json import dumps
    return dumps({"PlaylistItem": {"title": _it["title"], "videoPlayList": _it["episodes"]}},
                 ensure_ascii=False)     # 中文直接出,和真实数据源一样好读(客户端 loads 后再渲染)


def danmu(vid):
    """弹幕 / 评论:按 vid 稳定地挑 6 条(结构 {content, up, time} 与真实数据源一致)"""
    _v = str(vid or "").strip()
    if not _v:
        return []
    _seed = _n(_v)
    _out = []
    for _i in range(6):
        _out.append({"content": _DANMU_POOL[(_seed + _i * 7) % len(_DANMU_POOL)],
                     "up": 10 + (_seed + _i * 1337) % 9989,          # 点赞数:用来验证"按热度排序"
                     "time": (_seed + _i * 29) % 900})                # 时间点(秒)
    return sorted(_out, key=lambda _x: _x["up"], reverse=True)


def title(vid):
    """片名:单集 vid 给"剧名 第N集",单条视频给它的标题,认不出来给空串"""
    _drama, _ep = find_episode(vid)
    if _drama:
        return _ep["title"]
    _it = find_video(vid)
    if _it:
        return _it["title"]
    _it = find_cover(vid)                       # 兜底:直接拿剧集 id 问也算认得
    return _it["title"] if _it else ""


def vip_probe():
    """会员探测:给一个一定有得播的 vid(客户端拿它验证"探测→播放"这条链路)"""
    return _ep_id(_DRAMAS[0][0], 1)


# ---------------------------------------------------------------- 轮播 / 热词 / 联想 / 直播
def rotation():
    """首页轮播:返回 (海报, 标题, 详情页链接, 缩略图) 四元组,图片用 cover: 标记、链接用 drama: 标记

    thumbs 故意和 pics 取同一批"测试轮播图":客户端把 thumbs 用在首页底下一排推荐位上,
    于是首页从上到下(大轮播 / 右侧"大家在看" / 底下一排)看到的全是同一套测试图。
    """
    _pics = ["cover:rot-%d" % (_i + 1) for _i in range(len(_ROTATION))]
    _names = [_t for _c, _t in _ROTATION]
    _covers = ["drama:" + _c for _c, _t in _ROTATION]
    _thumbs = list(_pics)
    return _pics, _names, _covers, _thumbs


def bottoms():
    """首页底部那一排推荐位(与 rotation 同一批测试图 / 测试名)

    底部四个位置和大轮播共用同一张表,所以从上到下看到的都是"测试"内容;
    每一项给 (标题, 封面, 详情页链接),由 app.py 翻成绝对地址后挂在 /rotation 的 bottoms 上。
    """
    return [{"title": _t, "img": "cover:rot-%d" % (_i + 1), "link": "drama:" + _c}
            for _i, (_c, _t) in enumerate(_ROTATION)]


def default_keyword():
    """默认搜索词:界面(热词 / 空搜索)与 search / suggest 都按这一个口径"""
    return TEST_KEYWORD


def hot_words():
    """搜索热词:全用能搜出东西的词;默认词(TEST_KEYWORD)放第一个(点它必定搜得出结果,见 search)"""
    return [TEST_KEYWORD] + [_t for _c, _t, _e, _d in _DRAMAS]


def suggest(keyword):
    """搜索联想词:优先返回包含关键词的片名,不足再补几个通用词

    关键词留空时同样按 TEST_KEYWORD("测试") 匹配,和 search 一个口径:
    搜索框刚聚焦、还没打字时给的就是能搜出东西的那批词。
    """
    _kw = str(keyword or "").strip().lower() or TEST_KEYWORD.lower()
    _words = [str(_x["title"]) for _x in _items()] + _EXTRA_WORDS
    _hit = [_w for _w in _words if _kw and _kw in _w.lower()]
    for _w in _words:
        if len(_hit) >= 8:
            break
        if _w not in _hit:
            _hit.append(_w)
    return _hit[:8]


def live():
    """直播频道表:{分类: [[地址, 名称, 备注, 封面], …]};地址/封面用标记,由 app.py 翻成绝对地址"""
    return {_group: [list(_row) for _row in _rows] for _group, _rows in _LIVE.items()}
