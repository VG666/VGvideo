# -*- coding: utf-8 -*-
"""搜索数据源(测试用薄封装)—— 转发给数据服务,本脚本不再自己抓取

为什么只剩这么点:
    搜索的抓取 / 解析 / 去重 / 分页统计,已经全部下沉到数据服务(tx_server/sources/search.py),
    客户端连搜索接口都不碰了。本文件保留 `search()` 这个名字与返回结构,
    只为让 test/play.py 的 `import search_api` 不用改。

数据来源:
    GET {PLAY_API_BASE}/search?q=<关键词>&page=<页码>
    地址见 config/config.json 的 vgapi.PLAY_API_BASE;数据服务没起来时返回结构完整的空结果。

标准 JSON 结构(与 tx_server/sources/search.py、model/api/search.py 完全一致):
    {
      "source": "vg-server",        # 数据源标识
      "keyword": "斗罗大陆",         # 搜索词
      "page": 1,                    # 当前第几页(从 1 开始)
      "pages": 14,                  # 一共多少页
      "total": 400,                 # 视频类结果总数
      "items": [                    # 当前页要展示的列表
        {
          "kind": "cover",          # cover=剧集/影片/专辑(有 cid,进详情选集)
                                    # video=单条视频(有 vid,可直接解析播放)
          "id":   "mzc00200xf3rir6",
          "title":"斗罗大陆Ⅱ绝世唐门",
          "img":  "https://vcover-vt-pic.puui.qpic.cn/.../260",
          "desc": ""                # 简介/补充说明,没有就留空
        },
        ...
      ]
    }
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 程序目录(根)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from model.api.search import SOURCE, search as _search      # noqa: E402


def search(keyword, page=1):
    """搜索一页:数据来自数据服务(GET {PLAY_API_BASE}/search);失败返回结构完整的空结果"""
    return _search(keyword, page)
