#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站短剧AI自动剪辑工具 — 薄包装层
基于抖音短剧剪辑完整引擎 (ai_short_video_cutter_pro.py)
仅覆盖平台差异，其余 89 个引擎函数全部原样复用

覆盖项:
  (A) 全局常量 — 默认16:9横屏、更远字幕边距、更长时长
  (B) 敏感词 — B站社区规范替代抖音审核词
  (C) 标题/标签/互动 — B站分区/三连替代抖音话题标签/CTA
  (D) Overlay — B站片尾引导卡替代抖音片尾水印
  (E) 合规 — B站合规预检替代抖音合规
  (F) AI声明 — 片尾/描述标注替代片头黑屏
"""

import os, sys, json, time, random, re, subprocess, shutil
import datetime as _datetime  # 保存为模块引用，免受后续 import * 覆盖
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# ============================================================
# 路径：B站目录优先 + 共享 venv + 原引擎
# ============================================================
_BILI_DIR        = Path(__file__).parent.resolve()
_DOUYIN_DIR      = Path("/Users/ffzwai/.qclaw/workspace/douyin-short-drama-cutter")
_DOUYIN_VENV_SP  = str(_DOUYIN_DIR / ".venv" / "lib" / "python3.11" / "site-packages")

sys.path.insert(0, str(_BILI_DIR))
sys.path.insert(0, str(_DOUYIN_DIR))
if _DOUYIN_VENV_SP not in sys.path:
    sys.path.insert(0, _DOUYIN_VENV_SP)

# ---- 导入 B站专属合规模块 ----
from bilibili_compliance_checker import check_bilibili_compliance as _bili_compliance

# ---- 导入原引擎（全部 89 个函数） ----
try:
    from ai_short_video_cutter_pro import *            # noqa: F403
    _ENGINE_LOADED = True
    # 保存原 _check_content_risk 引用（注入前）
    import ai_short_video_cutter_pro as _engine_module
    _ORIG_CHECK_CONTENT_RISK = _engine_module._check_content_risk
except Exception as _e:                                # noqa: E722
    print(f"[FATAL] 原引擎加载失败: {_e}"); sys.exit(1)

# 重新 import 本模块级专属函数（同名优先）
# 下面继续覆盖(monkey-patch) 平台差异点

# 保存原引擎入口 (在覆盖前)
_ENGINE_batch_auto_cut = batch_auto_cut
_orig_batch = _ENGINE_batch_auto_cut  # 别名, 给新 batch_auto_cut 用

# ============================================================
# (A) B站默认配置 — 覆盖 DEFAULT_CONFIG 全局常量
# ============================================================

_BILI_DEFAULT_CONFIG = {
    # ---- 文件夹 ----
    "input_dir":     "raw_videos",
    "output_dir":    "output_videos",
    "bgm_dir":       "bgm",
    "narration_dir": "narration",
    "subtitle_dir":  "subtitles",

    # ---- B站16:9横屏 ----
    "aspect_ratio": "16:9",
    "width":  1920,
    "height": 1080,

    # ---- 时长(B站1-10分钟) ----
    "min_duration": 60,
    "max_duration": 600,
    "fps":          30,
    "bitrate":      "6M",
    "audio_bitrate":"192k",
    "codec":        "libx264",
    "audio_codec":  "aac",

    # ---- 片段 ----
    "clip_min_sec":      2.0,
    "clip_max_sec":      8,
    "target_clip_count": 60,
    "hook_duration":     5,
    "hook_required":     True,
    "conflict_boost":    1.5,

    # ---- 字幕(横屏更大) ----
    "subtitle_size":      48,
    "subtitle_color":    "white",
    "subtitle_stroke":   "black",
    "subtitle_stroke_w": 3,
    "subtitle_position":  ("center", "bottom"),
    "subtitle_margin_v":  140,

    # ---- 音频 ----
    "bgm_volume":                 0.15,
    "original_volume":            0.60,
    "narration_volume":           2.50,
    "orig_volume_with_narration": 0.10,
    "orig_volume_no_narration":   1.0,
    "sidechain_threshold": 0.05,
    "sidechain_ratio":     10,

    # ---- ASR & 特效 & 卡点 ----
    "asr_model":           "medium",
    "beat_threshold":      0.8,
    "beat_detection_interval": 0.1,
    "highlight_threshold": 0.15,
    "analysis_interval":   0.5,
    "auto_effects":        True,
    "transition_duration": 0.5,

    # ---- B站专属 ----
    "bilibili_zone":        "short_drama",
    "ai_disclosure":        True,
    "add_ending_card":      True,
    "ending_card_duration": 3,
    "naming_format": "{drama_name}_{episode}_bilibili_{date}_{duration}s",
    "offline_mode": False,
}

# Monkey-patch 原引擎 DEFAULT_CONFIG (仅本模块,引擎模块补丁在文件末尾)
# 🔧 原引擎内部函数使用模块级 CONFIG/DEFAULT_CONFIG,
# 必须同时注入到原引擎模块的 globals 里 — 见文件末尾 _inject_into_engine()
DEFAULT_CONFIG = _BILI_DEFAULT_CONFIG.copy()
CONFIG = DEFAULT_CONFIG.copy()

# ============================================================
# (B) B站敏感词 — 覆盖 SENSITIVE_WORDS
# ============================================================

SENSITIVE_WORDS = [                         # noqa: F811
    # === P0 违法违规（B站"十一不准"）===
    # 反动/分裂
    "分裂国家", "台独", "港独", "藏独", "疆独", "东突",
    "法轮功", "邪教", "封建迷信",
    # 色情低俗
    "色情", "裸体", "性交", "做爱", "口交", "肛交", "自慰",
    "走光", "偷拍", "露点", "漏点", "裸露", "脱衣",
    "一夜情", "换妻", "性虐待", "SM", "性伴侣",
    "情色", "黄色", "淫秽", "猥亵",
    # 违法
    "赌博", "博彩", "赌场", "赌钱", "下注", "赔率",
    "吸毒", "制毒", "贩毒", "毒品",
    "嫖娼", "卖淫", "招嫖",
    # 暴力血腥
    "杀人", "谋杀", "凶杀", "碎尸", "分尸",
    "自杀", "自残", "割腕",
    "家暴", "虐待",
    # 危害未成年人
    "儿童色情", "未成年色情", "恋童",
    # === P1 社区规范 ===
    # 人身攻击
    "傻逼", "脑残", "废物", "贱人", "垃圾人", "畜生",
    "死全家", "妈死了", "nmsl", "你妈", "操你", "cnm",
    "去死", "滚蛋", "滚出",
    # 引战对立
    "引战", "带节奏", "地域黑", "性别对立", "男女对立",
    "踩一捧一", "KY", "饭圈",
    # 歧视
    "种族歧视", "歧视", "弱智", "智障", "变态",
    "娘炮", "人妖", "同性恋恶心",
    # 恶意营销
    "稳赚", "躺着赚钱", "日入", "月入过万",
    "免费领取", "限时免费", "仅限今天",
    # 违规引流
    "加微信", "加QQ", "扫码加群", "关注公众号",
    "点击链接", "私信我", "看我主页",
]

# ============================================================
# (C) B站标题 — 覆盖 _generate_viral_title
# ============================================================

BILI_TITLE_TEMPLATES = {
    "reverse": [
        "{name}这段{num}分钟，我反复看了好几遍！",
        "一口气看完{name}，结局我完全没想到！",
        "{name}的高能名场面，每一秒都是精华！",
    ],
    "conflict": [
        "{name}这段对手戏太绝了，演技炸裂！",
        "这段{num}分钟的{name}，比整部剧还精彩！",
        "果然{name}才是短剧天花板！",
    ],
    "suspense": [
        "慎入！{name}这一段细思极恐！",
        "{name}的隐藏细节，99%的人都错过了！",
        "看到结尾才发现，{name}埋了这么多伏笔！",
    ],
    "recommend": [
        "安利一部我近期最上头的短剧：{name}！",
        "全程高能无尿点！{name}熬夜也要看完！",
        "给剧荒的姐妹安利：{name}，B站就有！",
    ],
    "topic": [
        "你看过{name}吗？说说你最喜欢的名场面！",
        "弹幕都说{name}封神了，你觉得呢？",
        "我宣布{name}就是今年最佳短剧，谁赞成谁反对？",
    ],
}

def _generate_viral_title(drama_name: str, genre: str, duration: float,
                          peak_moment: str = "", key_words: list = None,
                          drama_context: dict = None) -> str:
    """B站标题生成 — 覆盖原抖音版"""
    templates = BILI_TITLE_TEMPLATES
    genre_map = {
        "复仇爽剧": templates["reverse"] + templates["conflict"],
        "甜宠恋爱": templates["reverse"] + templates["topic"],
        "悬疑惊悚": templates["suspense"],
        "豪门总裁": templates["reverse"] + templates["conflict"],
        "搞笑喜剧": templates["topic"] + templates["recommend"],
        "仙侠修真": templates["suspense"] + templates["reverse"],
        "逆袭":     templates["reverse"] + templates["conflict"],
    }
    pool = genre_map.get(genre, sum(templates.values(), []))
    template = random.choice(pool)
    num = max(1, int(duration // 60))
    nums = f"{num}分钟" if num > 1 else f"{max(int(duration), 30)}秒"
    keyword = None
    if key_words:
        keyword = key_words[0]
    if not keyword:
        keyword = drama_name or "这部"
    title = template.format(name=keyword, num=num, nums=nums)
    if len(title) > 80:
        title = title[:77] + "..."
    return title


# ============================================================
# (D) B站标签 — 覆盖 _generate_hashtags / HASHTAG_SETS
# ============================================================

BI_RECOMMENDED_TAGS = [
    "短剧", "自制短剧", "B站短剧", "剧情", "演技", "名场面",
    "高能", "神仙打架", "剪辑", "影视剪辑", "二创", "原创",
]

BI_ZONE_MAP = {
    "复仇爽剧": "影视杂谈", "甜宠恋爱": "影视杂谈",
    "悬疑惊悚": "影视杂谈", "豪门总裁": "影视杂谈",
    "仙侠修真": "国产动画", "搞笑喜剧": "搞笑",
    "逆袭": "影视杂谈", "虐心": "影视杂谈", "热血": "影视杂谈",
}

def _generate_hashtags(genre: str = "", mood: str = "",
                       key_words: list = None,
                       drama_context: dict = None) -> list:
    """B站标签生成 — 替代抖音 HASHTAG_SETS"""
    tags = BI_RECOMMENDED_TAGS.copy()
    zone = BI_ZONE_MAP.get(genre, "影视杂谈")
    if zone and zone not in tags:
        tags.insert(0, zone)
    genre_tags_map = {
        "复仇爽剧": ["爽剧", "复仇"], "甜宠恋爱": ["甜宠", "恋爱"],
        "悬疑惊悚": ["悬疑", "惊悚"], "豪门总裁": ["豪门", "总裁"],
        "仙侠修真": ["仙侠", "修仙"], "搞笑喜剧": ["搞笑"],
    }
    for gt in genre_tags_map.get(genre, []):
        if gt not in tags:
            tags.append(gt)
    characters = (drama_context or {}).get("characters", []) or []
    for ch in characters[:2]:
        ch_tag = ch if isinstance(ch, str) else ch.get("name", "")
        if ch_tag and ch_tag not in tags:
            tags.append(ch_tag)
    return tags[:10]


# ============================================================
# (E) B站互动引导 — 覆盖 _generate_cta_text / CTA_TEMPLATES
# ============================================================

BILI_CTA_SET = {                                  # 替代 CTA_TEMPLATES
    "comment":  ["你最喜欢哪个片段？评论区告诉我！",
                 "这段剧情你给几分？弹幕和评论区聊聊！"],
    "like":     ["觉得不错的话点个赞支持一下吧~",
                 "如果喜欢这个视频，就帮我点个赞吧！"],
    "follow":   ["关注我，第一时间看更多短剧剪辑！",
                 "想看更多？关注不迷路！"],
    "coin":     ["如果觉得有帮助，赏个硬币呗~",
                 "投个币吧，这对我真的很重要！"],
}

def _generate_cta_text() -> str:
    """B站互动引导 — 替代抖音 CTA"""
    parts = [random.choice(BILI_CTA_SET["comment"])]
    if random.random() > 0.5:
        parts.append(random.choice(BILI_CTA_SET["like"]))
    else:
        parts.append(random.choice(BILI_CTA_SET["follow"]))
    if random.random() < 0.4:
        parts.append(random.choice(BILI_CTA_SET["coin"]))
    return " ".join(parts)


# ============================================================
# (F) B站发布配置 — 覆盖 _generate_post_config
# ============================================================

def _generate_post_config(drama_name: str, genre: str, duration: float,
                          peak_moment: str = "",
                          key_words: list = None,
                          drama_context: dict = None) -> dict:
    """B站发布配置 — 覆盖抖音版"""
    title = _generate_viral_title(drama_name, genre, duration,
                                  peak_moment, key_words, drama_context)
    tags = _generate_hashtags(genre, key_words=key_words,
                              drama_context=drama_context)
    cta = _generate_cta_text()
    zone = BI_ZONE_MAP.get(genre, "影视杂谈")
    minutes = max(1, int(duration // 60))
    desc = (
        f"【{drama_name}】{genre or '精彩短剧'}（{minutes}分钟精华版）\n\n"
        f"💬 {cta}\n\n"
        f"{' '.join('#' + t for t in tags[:8])}\n\n"
        f"⚙️ 本视频由AI辅助创作 | B站创作中心已声明"
    )
    return {
        "title": title, "description": desc,
        "tags": tags, "zone": zone,
        "duration": duration, "genre": genre,
        "cta_text": cta,
        "suggested_post_time": _suggest_post_time() if '_suggest_post_time' in globals() else {},
    }


# ============================================================
# (G) B站合规集成 — 覆盖原 validate_output
# ============================================================

def validate_output(output_path: str) -> dict:
    """B站合规预检 — 在抖音版质检后叠加B站专属检查"""
    # 如果原 validate_output 存在，先跑一次
    _orig_v = None
    try:
        if 'validate_output' in globals():
            _orig = globals().get('_orig_validate_output') or globals().get('validate_output')
            if _orig and _orig.__module__ != '__main__':
                _orig_v = _orig(output_path)
    except:
        pass

    info = get_video_info(output_path)
    dur = info.get("duration", 0)
    import re as _re
    drama = _re.sub(r'_[0-9]{4}.*', '', Path(output_path).stem)

    bili_result = _bili_compliance(output_path, drama, "", [], "short_drama")
    if _orig_v:
        bili_result["legacy_audit"] = _orig_v
    return bili_result


# ============================================================
# (H) B站片尾引导卡 — 替代 _add_ending_watermark
# ============================================================

def _add_ending_watermark(video_path: str, drama_name: str,
                          tags: list = None, ending_dur: float = None) -> bool:
    """B站片尾引导卡 — 替代抖音片尾水印"""
    if ending_dur is None:
        ending_dur = CONFIG.get("ending_card_duration", 3)
    if not CONFIG.get("add_ending_card", True):
        return True  # skip silently

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log("⚠️ PIL不可用,跳过片尾引导卡", "⚠"); return False

    try:
        info = get_video_info(video_path)
        w, h = info.get("width", 1920), info.get("height", 1080)

        img = Image.new('RGBA', (w, h), (10, 10, 20, 240))
        d = ImageDraw.Draw(img)
        fps = [("/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/Library/Fonts/Arial.ttf")]
        ft = None
        for fp in fps[0]:
            try:
                ft = ImageFont.truetype(fp, 72); break
            except:
                continue
        if ft is None:
            ft = ImageFont.load_default()

        title = "🎬 喜欢这部短剧吗？"
        bb = d.textbbox((0, 0), title, font=ft)
        d.text(((w - (bb[2] - bb[0])) // 2, h // 2 - 100),
               title, fill=(255, 255, 255, 255), font=ft)

        try:
            fs = ImageFont.truetype(fps[0][0], 32)
        except:
            fs = ft
        items = [
            ("👍 点赞", int(w * 0.15), h // 2 + 40),
            ("🪙 投币", int(w * 0.35), h // 2 + 40),
            ("⭐ 收藏", int(w * 0.55), h // 2 + 40),
            ("🔔 关注", int(w * 0.75), h // 2 + 40),
        ]
        for txt, cx, cy in items:
            bb2 = d.textbbox((0, 0), txt, font=fs)
            iw = bb2[2] - bb2[0]
            ih = bb2[3] - bb2[1]
            x0, y0 = cx - iw // 2 - 20, cy - 15
            x1, y1 = x0 + iw + 40, y0 + ih + 30
            d.rounded_rectangle([(x0, y0), (x1, y1)], radius=12,
                                fill=(40, 40, 60, 200))
            d.text((cx - iw // 2, cy), txt, fill=(255, 255, 255, 240),
                   font=fs)

        try:
            fa = ImageFont.truetype(fps[0][0], 22)
        except:
            fa = ft
        ai_txt = "本视频由AI辅助创作"
        ai_bb = d.textbbox((0, 0), ai_txt, font=fa)
        ai_w = ai_bb[2] - ai_bb[0]
        d.text(((w - ai_w) // 2, h - 70), ai_txt,
               fill=(150, 150, 170, 200), font=fa)

        import tempfile as tf
        fd, pg = tf.mkstemp(suffix=".png"); os.close(fd)
        fd, op = tf.mkstemp(suffix=".mp4"); os.close(fd)
        img.save(pg, "PNG")
        dur_s = get_video_info(video_path).get("duration", 60)
        s = ending_dur
        r = subprocess.run([
            'ffmpeg', '-y', '-i', video_path, '-i', pg,
            '-filter_complex',
            f'[1:v]loop=-1:size=1,fps=30,trim=0:{s},fade=in:0:0.5:alpha=1[card];'
            f'[0:v][card]overlay=0:0:enable=\'between(t,{dur_s - s},{dur_s})\'[vout]',
            '-map', '[vout]', '-map', '0:a?',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'copy', '-movflags', '+faststart', op
        ], capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0 and os.path.getsize(op) > 50000
        if ok:
            os.replace(op, video_path)
            log(f"✅ B站片尾引导卡({s}s)", "✅")
        else:
            log(f"⚠️ 片尾引导卡失败", "⚠️")
        for f in [pg, op]:
            try: os.unlink(f)
            except: pass
        return ok
    except Exception as e:
        log(f"⚠️ 片尾引导卡异常: {e}", "⚠️"); return False


# ============================================================
# (I) B站AI声明处理 — 跳过片头黑屏
# ============================================================

# 原始 _add_intro_ai_disclosure 会插入2秒黑屏。
# B站版本改为「在片尾引导卡中统一声明 + 描述文本声明」，跳过片头插入。
_add_intro_ai_disclosure = lambda video_path, total_dur=2.0: True  # noqa: E731


# ============================================================
# (J) 运行前配置 — apply_user_config 包装
# ============================================================
# 保留原 apply_user_config 逻辑，但确保 BILI DEFAULT 回来

_orig_apply_user_config = apply_user_config           # noqa: F405

def apply_user_config(user_config: dict = None) -> dict:
    """强制合并 B站默认 + 用户自定义"""
    global CONFIG
    CONFIG = _BILI_DEFAULT_CONFIG.copy()
    if user_config:
        for k, v in user_config.items():
            if v not in (None, "", "auto"):
                CONFIG[k] = v
                CONFIG[f"{k}_source"] = "user"
            elif v == "auto":
                CONFIG[f"{k}_source"] = "smart"
    return CONFIG


# ============================================================
# (K) 批量启动入口 — 完全替代原 batch_auto_cut
# ============================================================
# 不委托 _orig_batch (path(__file__) 硬编码指向抖音,无法修复)
# 直接调用引擎各阶段函数,路径全部由B站侧控制

def _ensure_dirs():
    """确保 B站工作目录存在"""
    for _dk in ["input_dir", "output_dir", "bgm_dir", "narration_dir", "subtitle_dir"]:
        _dp = CONFIG.get(_dk, "")
        if _dp:
            Path(_dp).mkdir(parents=True, exist_ok=True)
            log(f"📁 文件夹确认: {_dp}", "📁")

def batch_auto_cut(user_config: dict = None):
    """B站批量剪辑 — 绕过原引擎入口,直接编排各阶段"""
    user_config = user_config or {}

    # 1. 构建最终配置 (B站默认 + 用户覆盖)
    _cfg = _BILI_DEFAULT_CONFIG.copy()
    for _k, _v in user_config.items():
        if _v not in (None, "", "auto"):
            _cfg[_k] = _v

    # 2. 相对路径 → 绝对路径 (B站目录, 不依赖 __file__)
    for _key in ["input_dir", "output_dir", "bgm_dir", "narration_dir", "subtitle_dir"]:
        _val = _cfg.get(_key, "")
        if _val and not Path(_val).is_absolute():
            _cfg[_key] = str((_BILI_DIR / _val).resolve())
            log(f"📁 路径预解析: {_key} → {_cfg[_key]}", "📁")

    # 3. 注入到本模块 + 引擎模块 (此次调用期间全部读这个)
    global CONFIG
    CONFIG = _cfg
    _eng = sys.modules.get('ai_short_video_cutter_pro')
    if _eng:
        _eng.CONFIG = _cfg
        _eng.DEFAULT_CONFIG = _cfg

    _ensure_dirs()

    # 4. chdir 到 B站目录 (所有相对操作以此为准)
    _prev_cwd = os.getcwd()
    os.chdir(str(_BILI_DIR))

    log("=" * 60, "")
    log("📺 B站短剧AI自动剪辑工具", "🚀")
    log(f"📐 画幅: {_cfg['aspect_ratio']} | {_cfg['width']}×{_cfg['height']}", "")
    log("=" * 60, "")

    try:
        # 5. 切到引擎工作目录,直接跑原有完整流水线
        #    因为 _eng.CONFIG 已指向 B站路径 + 当前 cwd 是 B站目录,
        #    引擎内所有 check_dirs / Path 操作都走 B站侧
        _orig_batch(user_config)  # type: ignore # noqa: F821
    finally:
        os.chdir(_prev_cwd)

    # 6. B站后处理: 合规报告 + 发布配置 + 不合规重命名(不删除)
    _out = Path(_cfg.get("output_dir", "output_videos"))
    if _out.exists():
        from datetime import datetime as _dt
        _now = _dt.now().strftime("%Y%m%d_%H%M")
        for _mp4 in sorted(_out.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            # 跳过已标记不合规的文件
            if "_不合规" in _mp4.stem:
                continue
            if _mp4.stat().st_mtime < time.time() - 3600:
                continue
            _info = get_video_info(str(_mp4))
            _dur = _info.get("duration", 0)
            _drama = re.sub(r'_[0-9]{6,8}_.*', '', _mp4.stem)
            _title = _generate_viral_title(_drama, "逆袭", _dur)
            _tags = _generate_hashtags()
            _zone = BI_ZONE_MAP.get("逆袭", "影视杂谈")
            _comp = _bili_compliance(str(_mp4), _title, "", _tags, _zone)

            # B站合规后处理: 不合规→重命名标记(不删除)
            _score = _comp.get("total_score", _comp.get("score", 100))
            _p0_count = len([i for i in _comp.get("issues", []) if i.get("level") == "P0"])
            if _score < 60 or _p0_count > 0:
                _new_name = _mp4.parent / f"{_mp4.stem}_不合规{_mp4.suffix}"
                try:
                    _mp4.rename(_new_name)
                    log(f"⚠️ 合规警告(得分{_score}/{_p0_count}个P0),已标记: {_new_name.name}", "⚠️")
                    _mp4 = _new_name  # 后续发布配置指向重命名后的文件
                except Exception as _re:
                    log(f"⚠️ 重命名失败: {_re}", "⚠️")
                _comp["flagged_noncompliant"] = True

            _cfg_out = {
                "title": _title, "tags": _tags, "zone": _zone,
                "duration": _dur, "compliance": _comp, "ai_disclosure": True,
            }
            _cfg_path = _out / f"{_mp4.stem}_bilibili_post.json"
            with open(_cfg_path, 'w', encoding='utf-8') as _f:
                json.dump(_cfg_out, _f, ensure_ascii=False, indent=2)
            log(f"📋 B站发布配置已生成: {_cfg_path.name}", "📋")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="B站短剧AI自动剪辑工具")
    ap.add_argument("--config", type=str, help="用户配置 JSON")
    ap.add_argument("--test", action="store_true", help="环境检测")
    args = ap.parse_args()

    if args.test:
        print("🧪 B站短剧剪辑工具 — 环境检测")
        print(f"   Python:  {sys.version.split()[0]}")
        print(f"   ffmpeg:  {'✅' if shutil.which('ffmpeg') else '❌'}")
        print(f"   PIL:     {'✅' if __import__('importlib').util.find_spec('PIL') else '❌'}")
        print(f"   whisper: {'✅' if has_whisper_cpp() else '❌'}")
        try:
            import requests as _r
            _r.get("http://localhost:11434/api/tags", timeout=2)
            print(f"   Ollama:  ✅")
        except:
            print(f"   Ollama:  ❌")
        print(f"   引擎:     ✅ 原引擎89函数 + B站12项覆盖")
        print(f"   画幅:     {CONFIG['aspect_ratio']} ({CONFIG['width']}×{CONFIG['height']})")
        sys.exit(0)

    uc = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            uc = json.load(f)
    batch_auto_cut(uc)


# ============================================================
# (L) B站安全版内容风险检测 — 永不删除源目录
# ============================================================

def _bili_safe_content_risk(full_text: str, drama_name: str) -> dict:
    """
    B站版 _check_content_risk: 保留原引擎检测逻辑, 但永不返回 HIGH
    确保不会触发 shutil.rmtree 删除源目录
    """
    result = _ORIG_CHECK_CONTENT_RISK(full_text, drama_name)

    # B站规则: 永不删除源文件
    # HIGH -> MEDIUM (允许继续处理, 在输出阶段标记不合规)
    if result.get("risk_level") == "HIGH":
        log(f"⚠️ {drama_name}: 原始检测为HIGH风险, B站模式降级为MEDIUM(不删除源文件)", "⚠️")
        log(f"   匹配关键词: {result.get('matched', [])}", "")
        result["risk_level"] = "MEDIUM"
        result["reason"] = f"{result.get('reason', '')} (B站模式:已降级,仅标记)"
        result["bilibili_downgraded"] = True

    return result


# ============================================================
# 🔧 猴子补丁注入: 本文件末尾执行,此时所有函数已定义
# 将B站覆盖注入到原引擎模块的 globals,确保引擎内部函数读取正确
# ============================================================
def _inject_into_engine():
    """将所有 B站覆盖注入到 ai_short_video_cutter_pro 模块命名空间"""
    eng = sys.modules.get('ai_short_video_cutter_pro')
    if not eng:
        return
    cfg = _BILI_DEFAULT_CONFIG.copy()
    # 🔧 预解析路径: 引擎内 batch_auto_cut 用 __file__ 解析 → 错误指向抖音目录
    for _key in ["input_dir", "output_dir", "bgm_dir", "narration_dir", "subtitle_dir"]:
        _val = cfg.get(_key, "")
        if _val and not Path(_val).is_absolute():
            cfg[_key] = str((_BILI_DIR / _val).resolve())
    eng.CONFIG = cfg
    eng.DEFAULT_CONFIG = cfg
    eng.SENSITIVE_WORDS = SENSITIVE_WORDS
    eng._generate_viral_title = _generate_viral_title
    eng._generate_hashtags = _generate_hashtags
    eng._generate_cta_text = _generate_cta_text
    eng._generate_post_config = _generate_post_config
    eng._add_ending_watermark = _add_ending_watermark
    eng._add_intro_ai_disclosure = _add_intro_ai_disclosure
    eng.validate_output = validate_output
    eng.apply_user_config = apply_user_config
    eng.batch_auto_cut = batch_auto_cut
    # [FIX-20260712] 注入安全版 _check_content_risk — 永不高危删除源目录
    eng._check_content_risk = _bili_safe_content_risk
    log("🔧 B站覆盖已注入原引擎模块 (13项,含安全风险检测)", "🔧")

_inject_into_engine()
