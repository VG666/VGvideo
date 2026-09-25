# -*- coding: utf-8 -*-
"""视频下载 —— 一个大类单独成模块

================== 下载:aria2 负责搬字节(并发抓分片),ffmpeg 负责合成 mp4 ==================
播放链接是 HLS(m3u8),aria2 本身不认识 m3u8 清单,所以流程是:
  aria2 下 m3u8 → 解析出分片地址 → aria2 并发下全部分片 → ffmpeg concat 直接 remux 成 mp4(不重编码)
加密/异常清单交给 ffmpeg 自己拉流(它能处理 AES-128 分片),直链则 aria2 下完再 remux

对外只用一个入口:
    ok, msg = _dl_video(播放地址, 输出目录, 文件名, 封面地址, 进度回调)
"""
import hashlib
import os
import re
import shutil
import subprocess
from urllib.parse import urljoin

from model.paths import IS_WINDOWS, _run_dir, application_path

_DL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _tool_path(name):  # 在 程序目录/utility(旧名 tools)、程序目录、解包目录 与 PATH 里找外部工具(aria2c/ffmpeg);找不到返回 None
      try:
            _exe=name+(".exe" if IS_WINDOWS else "")
            for _d in (_run_dir,application_path):
                  for _n in (_exe,name):
                        for _p in (os.path.join(_d,"utility",_n),os.path.join(_d,"tools",_n),os.path.join(_d,_n)):
                              if os.path.isfile(_p):
                                    return _p
            return shutil.which(_exe) or shutil.which(name)
      except Exception:
            return None


def _run_hidden(cmd):  # 静默跑外部命令(不弹黑框),返回(returncode,输出文本)
      try:
            _kw={"creationflags":0x08000000} if IS_WINDOWS else {}#CREATE_NO_WINDOW
            _r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**_kw)
            return _r.returncode,(_r.stdout or b"").decode("utf-8","replace")
      except Exception as _e:
            return -1,str(_e)


def _aria2_run(urls,out_dir,headers=None,out_name=None,jobs=8,list_file=None):
      """aria2c 下载:分片多时走 -i 输入文件,避免命令行过长"""
      _a2=_tool_path("aria2c")
      if not _a2:
            return -1,"未找到 aria2c"
      try: os.makedirs(out_dir,exist_ok=True)
      except Exception: pass
      _cmd=[_a2,"--continue=true","--allow-overwrite=true","--auto-file-renaming=false",
            "--summary-interval=0","--console-log-level=warn","--file-allocation=none",
            "--max-tries=3","--retry-wait=1","--user-agent="+_DL_UA,
            "-x","16","-s","16","-d",out_dir]
      if out_name:
            _cmd+=["-o",out_name]
      for _h in (headers or []):
            _cmd+=["--header",_h]
      if list_file:
            return _run_hidden(_cmd+["-i",list_file,"-j",str(jobs)])
      return _run_hidden(_cmd+["-j",str(jobs)]+list(urls))


def _parse_m3u8(text):  # 返回(分片地址列表, 加密KEY的URI或None)
      _segs=[];_key=None
      for _l in (text or "").splitlines():
            _l=_l.strip()
            if not _l:
                  continue
            if _l.startswith("#EXT-X-KEY"):
                  if "METHOD=NONE" in _l.upper():
                        continue
                  _m=re.search(r'URI="([^"]+)"',_l)
                  _key=_m.group(1) if _m else "未知"
            elif not _l.startswith("#"):
                  _segs.append(_l)
      return _segs,_key


def _ffmpeg_to_mp4(ffmpeg,src,out,extra=None):  # remux 成 mp4:-c copy 不重编码,快且不损画质
      def _build(with_bsf):
            _cmd=[ffmpeg,"-y","-nostdin","-hide_banner","-loglevel","error"]
            if isinstance(src,(list,tuple)):
                  _cmd+=["-f","concat","-safe","0","-i",src[0]]
            else:
                  _cmd+=["-i",src]
            if with_bsf:
                  _cmd+=["-c","copy","-bsf:a","aac_adtstoasc"]
            else:
                  _cmd+=["-c","copy"]
            return _cmd+list(extra or [])+[out]
      _rc,_log=_run_hidden(_build(True))
      if _rc!=0:#有些流音频不是 aac,带 bsf 会失败,去掉再来一次
            _rc,_log=_run_hidden(_build(False))
      return _rc,_log


_DL_PATH_LIMIT=240#Windows 传统路径上限是 260,这里留出余量(".mp4"/".jpg"、aria2 的 .aria2 控制文件等)


def _dl_name_room(out_dir,ext):#按路径上限算出"文件主名"最多能占几个字符(已扣掉目录、分隔符与扩展名)
      try: _base=len(os.path.abspath(out_dir))
      except Exception: _base=len(str(out_dir))
      return max(12,min(_DL_PATH_LIMIT-_base-len(ext)-1,120))


def _dl_safe_name(name,room=120):#文件名净化 + 限长:超长就截断并补哈希,既不撞名也不会顶爆路径上限
      _s=re.sub(r'[\\/:*?"<>|\r\n\t]',"_",str(name or "")).strip().strip(". ")
      if not _s:
            return "video"
      if len(_s)<=room:
            return _s
      _h=hashlib.md5(_s.encode("utf-8","replace")).hexdigest()[:6]
      return _s[:max(8,room-7)].rstrip(". ")+"_"+_h


def _dl_tmp_dir(out_dir,name):#下载用的临时目录:名字压短,再长的剧名/链接都不会顶爆路径上限;同一部片子固定同名,重下时能就地清理复用
      _tag=re.sub(r'[\\/:*?"<>|\s]',"_",str(name or ""))[:32].strip("_") or "video"
      _h=hashlib.md5(str(name or "").encode("utf-8","replace")).hexdigest()[:8]
      return os.path.join(out_dir,"_dl_%s_%s"%(_tag,_h))


def _dl_video(play_url,out_dir,name,cover_url=None,on_msg=None):
      """从"正在播放的链接"下载并转成 mp4。返回(是否成功, 提示文本)"""
      def _say(_t):
            try:
                  if on_msg: on_msg(_t)
            except Exception: pass
      _urllib=__import__("urllib.request",fromlist=["request"])
      _a2=_tool_path("aria2c")
      if not _a2:
            return False,"没找到 aria2c.exe(把它放到程序目录或程序目录的 utility 子目录下)"
      _ff=_tool_path("ffmpeg")
      if not _ff:
            return False,"没找到 ffmpeg.exe(转 mp4 需要它,放到程序目录或 utility 子目录下)"
      _u=str(play_url or "").strip()
      if not _u.startswith("http"):
            return False,"当前没有可下载的播放地址(等解析出地址后再点下载)"
      _name=_dl_safe_name(name,_dl_name_room(out_dir,".mp4"))#限长:剧名/链接过长会顶爆 Windows 路径上限,后面会一路失败
      if not os.path.isdir(out_dir):#下载目录不存在或没权限:先说清楚,别等 aria2 报一堆看不懂的错
            try: os.makedirs(out_dir,exist_ok=True)
            except Exception as _e:
                  return False,"下载目录不可用:%s\n%s"%(out_dir,_e)
      _out=os.path.join(out_dir,_name+".mp4")
      _tmp=_dl_tmp_dir(out_dir,_name)#临时目录名压短(原来把文件名整个拼进目录名,长链接必然超长)
      try:
            if os.path.isdir(_tmp): shutil.rmtree(_tmp,ignore_errors=True)
            os.makedirs(_tmp,exist_ok=True)
      except Exception as _e:
            return False,"建不了临时目录:%s\n%s\n(路径过长或没有写入权限,请在菜单里换一个下载位置)"%(_tmp,_e)
      _hdrs=["Referer: https://v.qq.com/","Origin: https://v.qq.com"]
      _tmpfiles=[]
      try:
            if cover_url:#封面顺手一起下(纯图片直链,aria2 最擅长)
                  _aria2_run([cover_url],out_dir,_hdrs,out_name=_name+".jpg")
            if ".m3u8" in _u.lower():
                  # 1) 先让 aria2 把 m3u8 清单取回来
                  _say("取播放清单…")
                  _rc,_log=_aria2_run([_u],_tmp,_hdrs,out_name="playlist.m3u8")
                  _pl=os.path.join(_tmp,"playlist.m3u8")
                  _text=""
                  if os.path.isfile(_pl):
                        try:
                              with open(_pl,encoding="utf-8",errors="replace") as _f:
                                    _text=_f.read()
                        except Exception:
                              _text=""
                  if not _text:#aria2 偶尔会因为防盗链拿不到,退回 urllib
                        try:
                              _rq=_urllib.Request(_u,headers={"User-Agent":_DL_UA,"Referer":"https://v.qq.com/"})
                              _text=_urllib.urlopen(_rq,timeout=20).read().decode("utf-8","replace")
                        except Exception:
                              _text=""
                  _segs,_key=_parse_m3u8(_text)
                  if _segs and not _key:
                        # 2) 未加密:aria2 并发下分片(每个分片单独成文件,顺序不能乱)
                        _say("下载分片 0/%d…"%len(_segs))
                        _lst=os.path.join(_tmp,"segments.txt")
                        with open(_lst,"w",encoding="utf-8") as _f:
                              for _i,_s in enumerate(_segs):
                                    _f.write(urljoin(_u,_s)+"\n")
                                    _f.write("  out=seg%05d.ts\n"%_i)
                        _rc,_log=_aria2_run(None,_tmp,None,list_file=_lst,jobs=8)
                        _got=len([_n for _n in os.listdir(_tmp) if _n.startswith("seg") and _n.endswith(".ts")])
                        _say("合并 mp4…")
                        if _got>0:
                              _cl=os.path.join(_tmp,"concat.txt")
                              with open(_cl,"w",encoding="utf-8") as _f:
                                    for _i in range(len(_segs)):
                                          _p=os.path.join(_tmp,"seg%05d.ts"%_i)
                                          if os.path.isfile(_p):
                                                _f.write("file '"+_p.replace("\\","/")+"'\n")
                              _rc,_log=_ffmpeg_to_mp4(_ff,[_cl],_out)
                              if _rc==0 and os.path.isfile(_out):
                                    return True,"已保存:"+_out
                              return False,"分片已下完(%d/%d),但 ffmpeg 合并失败:\n%s"%(_got,len(_segs),_log[-300:])
                        return False,"aria2 下载分片失败(%d/%d):\n%s"%(_got,len(_segs),_log[-300:])
                  # 3) 加密清单或解析不出分片:交给 ffmpeg 直接拉流(它能处理 AES-128)
                  _say("ffmpeg 拉流中…")
                  _rc,_log=_ffmpeg_to_mp4(_ff,_u,_out,extra=["-protocol_whitelist","file,http,https,tcp,tls,crypto"])
                  if _rc==0 and os.path.isfile(_out):
                        return True,"已保存:"+_out
                  return False,"下载失败:\n"+_log[-300:]
            # 4) 直链(ts/mp4/flv等):aria2 下原文件 → ffmpeg remux 成 mp4
            _say("aria2 下载中…")
            _src=os.path.join(_tmp,"source"+os.path.splitext(_u.split("?")[0])[1].lower() or ".ts")
            _rc,_log=_aria2_run([_u],_tmp,_hdrs,out_name=os.path.basename(_src))
            if not os.path.isfile(_src):
                  _cands=[_n for _n in os.listdir(_tmp) if not _n.startswith("playlist")] if os.path.isdir(_tmp) else []
                  if _cands:
                        _src=os.path.join(_tmp,_cands[0])
                  else:
                        return False,"aria2 下载失败:\n"+_log[-300:]
            _say("转 mp4…")
            _rc,_log=_ffmpeg_to_mp4(_ff,_src,_out)
            if _rc==0 and os.path.isfile(_out):
                  return True,"已保存:"+_out
            return False,"转 mp4 失败:\n"+_log[-300:]
      except Exception as _e:
            return False,"下载出错:"+str(_e)
      finally:
            try:
                  for _n in os.listdir(_tmp):#只留成品:临时分片一律清掉
                        _p=os.path.join(_tmp,_n)
                        if os.path.isdir(_p): shutil.rmtree(_p,ignore_errors=True)
                        else: os.remove(_p)
                  os.rmdir(_tmp)
            except Exception:
                  pass


__all__ = ["_DL_UA", "_tool_path", "_run_hidden", "_aria2_run", "_parse_m3u8",
           "_ffmpeg_to_mp4", "_dl_video", "_dl_safe_name", "_dl_tmp_dir", "_dl_name_room"]
