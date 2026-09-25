# -*- coding: utf-8 -*-
# 裁剪 videovlc 的 codec/demux/access 插件：保留播放常见视频(HLS/TS/MP4 + H264/H265+AAC)
# 所需的最小集，其余移动到 videovlc_removed/（保持相对结构，可随时还原）。
# 仅移动，不删除。
$ErrorActionPreference = 'SilentlyContinue'
$plugins = "F:\编程\VG视频\新建文件夹\video\videovlc\plugins"
$removed = "F:\编程\VG视频\新建文件夹\video\videovlc_removed\plugins"

# 保留清单（按子目录）：只有这些留原地，其余一律移走
$keep = @{
  'codec' = @(
    'libavcodec_plugin.dll',   # 通用 FFmpeg 解码：H264/H265/AAC/AV1/VP9/MP3/FLAC/OPUS...
    'libdav1d_plugin.dll',     # AV1 解码加速
    'libd3d11va_plugin.dll',   # Windows 硬件加速
    'libdxva2_plugin.dll',
    'libmft_plugin.dll',
    'libqsv_plugin.dll',
    'liblibass_plugin.dll',    # 字幕渲染 ASS/SSA
    'libsubsdec_plugin.dll',   # 文本字幕 SRT
    'libwebvtt_plugin.dll',    # WebVTT 字幕
    'libdvbsub_plugin.dll',    # DVB 字幕（直播）
    'libspudec_plugin.dll'     # VobSub 字幕
  )
  'demux' = @(
    'libadaptive_plugin.dll',  # HLS / DASH 自适应（直播/点播 m3u8）
    'libts_plugin.dll',        # MPEG-TS（HLS 分片/直播）
    'libmp4_plugin.dll',       # MP4（下载成品）
    'libmkv_plugin.dll',       # MKV
    'libplaylist_plugin.dll',  # m3u/pls 播放列表
    'libh26x_plugin.dll',      # H264/H265 裸流
    'libsubtitle_plugin.dll'   # 外挂字幕文件
  )
  'access' = @(
    'libhttp_plugin.dll',      # HTTP/HTTPS 直链/HLS 拉流
    'libhttps_plugin.dll',
    'libfilesystem_plugin.dll',# 本地文件
    'libudp_plugin.dll',       # UDP（IPTV 直播）
    'libtcp_plugin.dll',
    'librtp_plugin.dll',
    'libaccess_realrtsp_plugin.dll',
    'liblive555_plugin.dll',   # RTSP/RTP 直播
    'libimem_plugin.dll',
    'libaccess_imem_plugin.dll',
    'libsdp_plugin.dll',
    'libidummy_plugin.dll'
  )
}

$total = 0; $count = 0
foreach ($cat in @('codec', 'demux', 'access')) {
  $dir = Join-Path $plugins $cat
  if (-not (Test-Path -LiteralPath $dir)) { continue }
  Get-ChildItem -LiteralPath $dir -File | ForEach-Object {
    if ($keep[$cat] -notcontains $_.Name) {
      $rel    = Join-Path $cat $_.Name
      $target = Join-Path $removed $rel
      $tDir   = Split-Path -Parent $target
      if (-not (Test-Path -LiteralPath $tDir)) { New-Item -ItemType Directory -Path $tDir -Force | Out-Null }
      $sz = $_.Length
      Move-Item -LiteralPath $_.FullName -Destination $target -Force
      $total += $sz; $count++
      Write-Host ("MOVED {0}  ({1:N2} MB)" -f $rel, ($sz / 1MB))
    }
  }
}
Write-Host ("`nDONE: 移动 {0} 个文件，释放 {1:N2} MB" -f $count, ($total / 1MB))
