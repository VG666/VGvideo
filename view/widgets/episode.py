# -*- coding: utf-8 -*-
"""选集(从 main.py 拆出)

    switch_episode      : 点击选集:解析该集地址并记下续播集数(解析失败不改当前播放)
    style_episode_list  : 选集按钮统一样式(当前集橙底高亮、预告灰字、其余浅灰字)
    attach_episode_hover: 给选集按钮挂上悬浮反馈
"""
import model.state as state
from model.records import _rec_save, _rec_album_name
from model.api import _resolve_url, play_fail_msg


def switch_episode(x,i):#点击选集:解析该集播放地址并记录续播集数;解析失败不切换、不写假进度
  try:
    _cur=state.current_url.rsplit("=vg")[0][::-1].rsplit("&")[0][::-1] if "=vg" in str(state.current_url) else ""
    if _cur!=x:
      state.current_episode=i
      _vu=_resolve_url(x)
      if not _vu:
        try:#把失败原因(内容加密 / 会员权益 / 网络)显示到播放器右侧,而不是点了没反应
          _ap=state.active_player
          if _ap is not None:
            _ap._play_fail_hint(play_fail_msg())
        except Exception:
          pass
        return#解析失败(如接口暂不可用):保持当前播放不变,由用户稍后重试
      state.current_url=_vu+"&"+x+"=vg"
      try:#换集:集数改成新集、进度归零,剧名沿用(历史 .ini / .vgini 记录在这里就被升级成 JSON 了)
        _rec_save(state.argv[2],episode=i,progress=0.0,name=_rec_album_name())
      except Exception:
        pass
      try:#确保选集切换能被自动开播/换集监控响应(哪怕信息获取阶段失败过)
        _ap=state.active_player
        if _ap is not None:
          _ap.after(0,_ap._auto_play_ready)
      except Exception:
        pass
  except Exception:
    pass

def style_episode_list(vgi_index):#选集按钮统一样式:当前集橙底深字(一眼可见)、预告灰字、其余浅灰字
  _vl=state.episode_buttons
  for _k,_b in enumerate(_vl):
    try:
      _on=(_k==vgi_index)
      try: _tr=not str(_b.cget("text")).strip().isdigit()#预告/MV/花絮等非正片标签:压暗一档,和纯集数区分开
      except Exception: _tr=False
      _b.configure(highlightthickness=0,
                   bg="#FF5945" if _on else "#26262B",
                   fg="#26262B" if _on else ("#8A8A93" if _tr else "#DBDBDC"))
      try: _b.configure(activebackground="#FF5945" if _on else "#181915",activeforeground="#26262B" if _on else "#FF5945")#按下时不要闪系统灰
      except Exception: pass
    except Exception:
      pass

def attach_episode_hover(x):#选集按钮悬浮反馈:进入变橙预览可点,移出按"当前集/预告/其他"规则整体还原
  def _restore(*novg):
    style_episode_list(state.current_episode)
  x.bind("<Enter>",lambda *novg:x.configure(bg="#181915",fg="#FF5945"))#进入时变色
  x.bind("<Leave>",_restore)#离开时还原(当前集自动保持橙底高亮,不会再变回黑字)
