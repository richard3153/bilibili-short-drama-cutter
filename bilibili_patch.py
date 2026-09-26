#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站短剧-配置与行为覆盖补丁
通过monkey-patch方式覆盖原抖音项目的关键行为，适配B站平台规范

核心覆盖项:
1. 视频参数: 16:9横屏(1920x1080), 1-10分钟时长
2. 合规检查: B站社区规范替代抖音审核规则
3. 元数据: B站标题/标签/分区规范
4. 字幕样式: 适配横屏布局
5. 敏感词库: B站社区规范
"""

import sys
import os
from pathlib import Path

# ============================================================
# 路径设置：将抖音项目加入sys.path以便导入共享模块
# ============================================================
_BILI_WORK_DIR = Path(__file__).parent.resolve()

# 确保b站目录在path最前面（共享模块已内置在本目录，无需依赖抖音）
if str(_BILI_WORK_DIR) not in sys.path:
    sys.path.insert(0, str(_BILI_WORK_DIR))

# 本目录自带 .venv（符号链接到本地虚拟环境）
_VENV_SP = str(_BILI_WORK_DIR / ".venv" / "lib" / "python3.11" / "site-packages")
if _VENV_SP not in sys.path:
    sys.path.insert(0, _VENV_SP)


# ============================================================
# B站专用默认配置(覆盖抖音配置)
# ============================================================

BILI_DEFAULT_CONFIG = {
    # ---- 文件夹配置(沿用抖音项目路径，通过symlink共享) ----
    "input_dir":  "raw_videos",
    "output_dir": "output_videos",
    "bgm_dir":    "bgm",
    "narration_dir": "narration",
    "subtitle_dir":  "subtitles",

    # ---- B站视频比例参数(16:9横屏) ----
    "aspect_ratio": "16:9",  # B站默认横屏
    "width":  1920,
    "height": 1080,

    # ---- B站视频参数 ----
    "min_duration": 60,    # 最短1分钟
    "max_duration": 600,   # 最长10分钟(B站短剧推荐)
    "fps":          30,
    "bitrate":      "6M",       # B站1080p推荐6Mbps
    "audio_bitrate":"192k",
    "codec":        "libx264",
    "audio_codec":  "aac",

    # ---- 片段配置(适配更长视频) ----
    "clip_min_sec": 2.0,
    "clip_max_sec": 8,           # B站可接受更长单片段
    "target_clip_count": 60,     # 更多片段(适配更长总时长)

    # ---- B站开场配置 ----
    "hook_duration": 5,          # B站开场可稍长
    "hook_required": True,
    "conflict_boost": 1.5,

    # ---- 字幕配置(适配横屏) ----
    "subtitle_size":     48,          # 横屏字幕稍大
    "subtitle_color":    "white",
    "subtitle_stroke":   "black",
    "subtitle_stroke_w": 3,
    "subtitle_position":  ("center", "bottom"),
    "subtitle_margin_v":  120,        # 横屏底部边距更大

    # ---- 音频混音配置 ----
    "bgm_volume":      0.15,
    "original_volume": 0.60,
    "narration_volume": 2.50,
    "orig_volume_with_narration": 0.10,
    "orig_volume_no_narration": 1.0,
    "sidechain_threshold": 0.05,
    "sidechain_ratio": 10,

    # ---- ASR模型配置(共享抖音项目模型) ----
    "asr_model": "medium",

    # ---- B站专属功能 ----
    "bilibili_zone": "short_drama",     # 分区: short_drama/fan_creation
    "ai_disclosure": True,              # AI辅助创作声明
    "add_ending_card": True,            # B站片尾引导卡(关注/三连)
    "ending_card_duration": 3,          # 片尾引导卡时长

    # ---- 卡点配置 ----
    "beat_threshold": 0.8,
    "beat_detection_interval": 0.1,

    # ---- 高光检测 ----
    "highlight_threshold": 0.15,
    "analysis_interval": 0.5,

    # ---- 智能特效 ----
    "auto_effects": True,
    "transition_duration": 0.5,

    # ---- 命名格式 ----
    "naming_format": "{drama_name}_{episode}_bilibili_{date}_{duration}s",

    # ---- 离线模式 ----
    "offline_mode": False,
}


# ============================================================
# B站敏感词库(覆盖抖音敏感词)
# ============================================================

BILI_SENSITIVE_WORDS = [
    # ---- B站社区规范: 引战/人身攻击 ----
    "辱骂", "人身攻击", "地域黑", "性别对立", "引战", "带节奏",
    "傻逼", "脑残", "废物", "贱人", "死全家", "nmsl",

    # ---- 歧视性言论 ----
    "种族歧视", "歧视", "弱智", "智障", "变态",

    # ---- 违法违规 ----
    "赌博", "博彩", "赌场", "吸毒", "制毒", "嫖娼", "色情",

    # ---- B站引流违规 ----
    "加微信", "加QQ", "扫码加群", "关注公众号", "点击链接",

    # ---- 平台竞争 ----
    "抖音", "快手",

    # ---- 政治敏感 ----
    "政府", "上访", "维权", "翻墙", "VPN",

    # ---- 恶意营销 ----
    "稳赚", "躺着赚钱", "日入", "月入过万", "免费领取", "包治", "根治",

    # ---- 广告法禁止 ----
    "最", "第一", "百分百", "绝对", "国家级", "顶级", "唯一", "极致",

    # ---- 虚假承诺 ----
    "保证", "承诺", "无效退款", "彻底治愈",
]


# ============================================================
# B站爆款标题模板(替代抖音模板)
# ============================================================

BILI_VIRAL_TITLE_TEMPLATES = {
    "reverse": [
        "{name}这段{num}分钟，我反复看了好几遍！",
        "一口气看完{name}，结局我完全没想到！",
        "{name}的高能名场面，每一秒都是精华！",
        "当{name}说出这句话，我整个人都不好了！",
    ],
    "conflict": [
        "{name}这段对手戏太绝了，演技炸裂！",
        "这段{num}分钟的{name}，比整部剧还精彩！",
        "你敢信？{name}的原声这么牛！",
        "果然{name}才是短剧天花板！",
    ],
    "suspense": [
        "慎入！{name}这一段细思极恐！",
        "{name}的隐藏细节，99%的人都错过了！",
        "看到结尾才发现，{name}埋了这么多伏笔！",
        "这个镜头的信息量太大了！{name}值得逐帧分析！",
    ],
    "recommend": [
        "安利一部我近期最上头的短剧：{name}！",
        "全程高能无尿点！{name}熬夜也要看完！",
        "已经在等{name}第二季了，有人一起吗？",
        "给剧荒的姐妹安利：{name}，B站就有！",
    ],
    "topic": [
        "你看过{name}吗？说说你最喜欢的名场面！",
        "弹幕都说{name}封神了，你觉得呢？",
        "我宣布{name}就是今年最佳短剧，谁赞成谁反对？",
        "{name}这波操作，老二次元都直呼内行！",
    ],
}


# ============================================================
# B站分区推荐(替代抖音话题标签)
# ============================================================

BI_ZONE_MAP = {
    "复仇爽剧": "影视杂谈",
    "甜宠恋爱": "影视杂谈",
    "悬疑惊悚": "影视杂谈",
    "豪门总裁": "影视杂谈",
    "仙侠修真": "国产动画",
    "搞笑喜剧": "搞笑",
    "逆袭": "影视杂谈",
    "虐心": "影视杂谈",
    "热血": "影视杂谈",
}

BI_RECOMMENDED_TAGS = [
    "短剧", "自制短剧", "B站短剧", "剧情",
    "演技", "名场面", "高能", "神仙打架",
    "剪辑", "影视剪辑", "二创", "原创",
]

# ============================================================
# B站互动引导文案(替代抖音CTA)
# ============================================================

BILI_CTA_TEMPLATES = {
    "comment": [
        "你最喜欢哪个片段？评论区告诉我！",
        "这段剧情你给几分？弹幕和评论区聊聊！",
        "大家觉得结局还能怎么改？来评论区发挥！",
    ],
    "like": [
        "觉得不错的话点个赞支持一下吧~",
        "如果喜欢这个视频，就帮我点个赞吧！",
        "点赞过千就剪续集，说到做到！",
    ],
    "follow": [
        "关注我，第一时间看更多短剧剪辑！",
        "想看更多？关注不迷路！",
        "点个关注，下期更精彩！",
    ],
    "coin": [
        "如果觉得有帮助，赏个硬币呗~",
        "投个币吧，这对我真的很重要！",
    ],
}


def apply_bilibili_patch():
    """
    应用B站补丁的主函数
    在导入原项目前调用此函数，将全局配置替换为B站版本
    """
    global _patch_applied
    if _patch_applied:
        return

    print("[BILIBILI PATCH] 应用B站合规配置覆盖...")

    # 标记已应用
    _patch_applied = True

    # 返回配置供外部使用
    return {
        "config": BILI_DEFAULT_CONFIG,
        "sensitive_words": BILI_SENSITIVE_WORDS,
        "title_templates": BILI_VIRAL_TITLE_TEMPLATES,
        "zone_map": BI_ZONE_MAP,
        "recommended_tags": BI_RECOMMENDED_TAGS,
        "cta_templates": BILI_CTA_TEMPLATES,
    }


_patch_applied = False


def get_bili_config():
    """获取B站完整配置"""
    patch = apply_bilibili_patch()
    return patch["config"]


def get_bili_title_templates():
    """获取B站标题模板"""
    patch = apply_bilibili_patch()
    return patch["title_templates"]


if __name__ == "__main__":
    cfg = get_bili_config()
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
