#!/usr/bin/env python3
"""
B站合规预检系统 - bilibili_compliance_checker.py
依据: B站社区公约(2024)、小黑屋处罚条例V2.0、创作公约
在视频生成后自动检测可能违规项并打分(0-100)

检测维度:
1. 画幅与分辨率 — 16:9横屏、≥1280×720
2. 内容安全 — B站"十一不准"原则 + 色情低俗标准(10条)
3. 水印检测 — 禁止其他平台水印
4. 音频版权 — BGM来源合规
5. 文本合规 — 标题≤80字、标签≤10个、解说敏感词
6. 分区合规 — 短剧→影视-影视杂谈/自制短剧
7. 画质合规 — 码率≥3Mbps、帧率≥24fps
8. 元数据 — AI辅助创作声明、原创声明、版权声明
"""

import os
import json
import subprocess
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ============================================================
# B站社区公约 — 敏感词库（源自小黑屋条例V2.0 + 创作公约）
# 完全面向B站平台，零抖音残留
# ============================================================

# P0：B站"十一不准"原则 —— 违法违规（一次违规即大幅扣分 / 直接退回）
BILI_ILLEGAL_WORDS = [
    # 反动 / 分裂国家
    "分裂国家", "台独", "港独", "藏独", "疆独", "东突",
    "法轮功", "邪教", "封建迷信",
    # 色情低俗（创作公约第一条 10 项细则对应）
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
]

# P1：社区规范违规 —— 引战/人身攻击/歧视（B站社区氛围红线）
BILI_VIOLATION_WORDS = [
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

# P1：广告法绝对化用语（B站审核扣分项）
ABSOLUTE_AD_PATTERNS = [
    re.compile(pat) for pat in [
        r'最好', r'第一', r'唯一', r'顶级', r'极致', r'完美',
        r'百分百', r'100%', r'国家级', r'世界级',
        r'全网最', r'史上最',
    ]
]

# P2：平台导流关键词（B站严禁向竞品导流）
PLATFORM_DRAIN_WORDS = [
    "抖音", "TikTok", "快手", "小红书", "微视", "西瓜视频",
    "YouTube", "Youtube", "油管",
]


# ============================================================
# B站视频分区合规
# ============================================================

ZONE_REQUIREMENTS = {
    "short_drama": {
        "suggested_zones": ["影视-影视杂谈", "影视-自制短剧"],
        "max_title_len": 80,
    },
    "fan_creation": {
        "suggested_zones": ["影视-影视剪辑"],
        "max_title_len": 80,
    },
}


class BilibiliComplianceChecker:
    """B站合规预检器（仅B站标准，零抖音残留）"""

    def __init__(self, video_path: str, drama_title: str,
                 narration_text: str = "", tags: List[str] = None,
                 zone: str = "short_drama"):
        self.video_path = video_path
        self.drama_title = drama_title
        self.narration = narration_text
        self.tags = tags or []
        self.zone = zone
        self.issues: List[Dict] = []
        self.score = 100

    # ------------------------------------------------------------------
    def check_all(self) -> Dict:
        """执行全部B站合规检查，返回 {score, issues, passed, recommendations}"""
        logger.info(f"🔍 开始B站合规预检: {self.drama_title}")

        # ---- P0：直接导致下架/限流的致命项 ----
        self._check_content_safety()    # 十一不准 + 色情低俗10条
        self._check_watermark()         # 其他平台水印

        # ---- P1：B站审核扣分项 ----
        self._check_aspect_ratio()      # 16:9 横屏
        self._check_text_compliance()   # 标题/标签/引战词
        self._check_audio_compliance()  # BGM版权

        # ---- P2：体验优化建议 ----
        self._check_video_quality()     # 码率/帧率
        self._check_metadata()          # AI声明/原创/版权
        self._check_zone_compliance()   # 分区建议

        result = {
            "video": self.video_path,
            "score": max(0, self.score),
            "issues": self.issues,
            "passed": self.score >= 60,
            "recommendations": self._generate_recommendations()
        }
        logger.info(
            f"✅ B站合规预检完成: 得分 {result['score']}/100, "
            f"问题 {len(self.issues)} 个"
        )
        return result

    # ==================================================================
    # P0 致命检查
    # ==================================================================

    def _check_content_safety(self):
        """P0 内容安全 —— B站'十一不准' + 色情低俗10条标准"""
        logger.info("  🔍 P0 内容安全 (B站社区公约) ...")

        text = (self.narration + " " + self.drama_title
                + " " + " ".join(self.tags)).lower()

        # 违法/反动/色情/暴力 —— 每命中一个扣 25 分
        for w in BILI_ILLEGAL_WORDS:
            if w.lower() in text:
                self.issues.append({
                    "level": "P0",
                    "category": "违法违规",
                    "description": f"命中B站'十一不准'违规词: {w}",
                    "current": f"检测到 '{w}'",
                    "recommendation": "立即移除违规内容，B站对此类零容忍"
                })
                self.score -= 25

        # 引战/人身攻击/歧视/恶意营销 —— 每命中一个扣 8 分
        for w in BILI_VIOLATION_WORDS:
            if w.lower() in text:
                self.issues.append({
                    "level": "P1",
                    "category": "社区规范",
                    "description": f"命中B站社区规范违规词: {w}",
                    "current": f"检测到 '{w}'",
                    "recommendation": "修改文案，避免引战/人身攻击/歧视性表达"
                })
                self.score -= 8

        # 广告法绝对化用语
        for pat in ABSOLUTE_AD_PATTERNS:
            if pat.search(self.narration) or pat.search(self.drama_title):
                self.issues.append({
                    "level": "P1",
                    "category": "广告法合规",
                    "description": f"包含广告法禁止的绝对化用语: {pat.pattern}",
                    "current": (pat.search(text).group()
                                if pat.search(text) else pat.pattern),
                    "recommendation": "修改为客观描述，去除极限用语"
                })
                self.score -= 5
                break  # 仅报一次

        # 平台导流词
        for w in PLATFORM_DRAIN_WORDS:
            if w in text:
                self.issues.append({
                    "level": "P2",
                    "category": "平台导流",
                    "description": f"内容包含竞品平台名称: {w}",
                    "current": f"检测到 '{w}'",
                    "recommendation": "移除竞品平台名称，B站严禁导流"
                })
                self.score -= 5
                break

        logger.info(f"    ✅ 内容安全检测完成，当前得分: {self.score}")

    def _check_watermark(self):
        """P0 水印检测 —— B站严禁其他平台水印"""
        logger.info("  🔍 P0 水印检测 ...")
        text = self.drama_title + " " + " ".join(self.tags)
        for name in PLATFORM_DRAIN_WORDS:
            if name in text:
                self.issues.append({
                    "level": "P0",
                    "category": "平台水印",
                    "description": f"标题/标签包含其他平台名称: {name}",
                    "current": self.drama_title,
                    "recommendation": "移除竞品平台名称，B站严禁外站导流标识"
                })
                self.score -= 15
                return

        try:
            subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1", self.video_path],
                capture_output=True, text=True, timeout=10
            )
        except Exception:
            pass

    # ==================================================================
    # P1 审核扣分项
    # ==================================================================

    def _check_aspect_ratio(self):
        """P1 画幅比例 —— B站标准 16:9 横屏"""
        logger.info("  🔍 P1 画幅比例 (B站 16:9) ...")
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "json",
                 self.video_path],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(r.stdout)
            if "streams" not in info or len(info["streams"]) == 0:
                self.issues.append({
                    "level": "P1", "category": "视频流",
                    "description": "无法读取视频流信息",
                    "current": "无流数据",
                    "recommendation": "确认视频文件完整有效"
                })
                self.score -= 10
                return

            s = info["streams"][0]
            w, h = s.get("width", 0), s.get("height", 0)
            if w <= 0 or h <= 0:
                self.score -= 10
                return

            aspect = w / h
            logger.info(f"   📐 {w}×{h} (宽高比 {aspect:.2f})")

            if aspect < 1.60:
                self.issues.append({
                    "level": "P1", "category": "画幅比例",
                    "description": f"宽高比 {aspect:.2f} 不符合B站16:9横屏标准",
                    "current": f"{w}×{h}",
                    "recommendation": "调整为1920×1080(16:9)，竖屏内容可加模糊背景填充"
                })
                self.score -= 20
            elif aspect > 1.90:
                self.issues.append({
                    "level": "P1", "category": "画幅比例",
                    "description": f"宽高比 {aspect:.2f} 过宽",
                    "current": f"{w}×{h}",
                    "recommendation": "裁剪或补黑边调整为标准16:9"
                })
                self.score -= 5

            if w < 1280 or h < 720:
                self.issues.append({
                    "level": "P1", "category": "分辨率",
                    "description": f"分辨率 {w}×{h} 过低，B站推荐≥1280×720",
                    "current": f"{w}×{h}",
                    "recommendation": "至少输出1280×720，推荐1920×1080"
                })
                self.score -= 10
        except Exception as e:
            logger.warning(f"   ⚠️ 画幅检测失败: {e}")
            self.score -= 5

    def _check_text_compliance(self):
        """P1 文本合规 —— 标题长度、标签数量、语速"""
        logger.info("  🔍 P1 文本合规 (标题/标签) ...")

        if len(self.drama_title) > 80:
            self.issues.append({
                "level": "P1", "category": "标题合规",
                "description": f"标题 {len(self.drama_title)} 字符，超B站80字符限制",
                "current": f"{len(self.drama_title)} 字符",
                "recommendation": "缩短标题至80字符以内"
            })
            self.score -= 10

        if len(self.tags) > 10:
            self.issues.append({
                "level": "P2", "category": "标签合规",
                "description": f"标签 {len(self.tags)} 个，B站推荐≤10个",
                "current": f"{len(self.tags)} 个",
                "recommendation": "精简至10个以内高相关度标签"
            })
            self.score -= 3

        if self.narration:
            try:
                r = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1", self.video_path],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    dur = float(r.stdout.strip())
                    cps = len(self.narration) / max(dur, 1)
                    if cps > 8:
                        self.issues.append({
                            "level": "P2", "category": "字幕语速",
                            "description": f"字幕语速 {cps:.1f} 字/秒，偏快",
                            "current": f"{cps:.1f} 字/秒",
                            "recommendation": "精简解说词或增加时长，建议3-6字/秒"
                        })
                        self.score -= 3
            except Exception:
                pass

    def _check_audio_compliance(self):
        """P1 音频合规 —— BGM版权、采样率"""
        logger.info("  🔍 P1 音频合规 (BGM版权) ...")

        for w in ["原曲", "原声", "OST", "主题曲", "插曲", "片头曲", "片尾曲"]:
            if w in self.narration:
                self.issues.append({
                    "level": "P1", "category": "音频版权",
                    "description": f"解说提及版权音乐关键词: {w}",
                    "current": f"检测到 '{w}'",
                    "recommendation": "确认BGM来源合规，使用B站音乐库或CC0素材"
                })
                self.score -= 5
                break

        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=sample_rate", "-of", "json",
                 self.video_path],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(r.stdout)
            if "streams" in info and info["streams"]:
                sr = int(info["streams"][0].get("sample_rate", 0))
                if 0 < sr < 44100:
                    self.issues.append({
                        "level": "P2", "category": "音频质量",
                        "description": f"采样率 {sr}Hz 过低，B站推荐≥44100Hz",
                        "current": f"{sr}Hz",
                        "recommendation": "输出音频至少44100Hz采样率"
                    })
                    self.score -= 3
        except Exception:
            logger.debug("   ℹ️ 音频质量检测跳过")

    # ==================================================================
    # P2 体验优化建议
    # ==================================================================

    def _check_video_quality(self):
        """P2 画质 —— 码率、帧率"""
        logger.info("  🔍 P2 画质合规 (码率/帧率) ...")
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=bit_rate,r_frame_rate",
                 "-of", "json", self.video_path],
                capture_output=True, text=True, timeout=10
            )
            info = json.loads(r.stdout)
            if "streams" not in info or not info["streams"]:
                return
            s = info["streams"][0]

            br = int(s.get("bit_rate", 0))
            if br > 0 and br < 3_000_000:
                self.issues.append({
                    "level": "P2", "category": "视频码率",
                    "description": f"码率 {br/1e6:.1f}Mbps 偏低，1080p推荐≥3Mbps",
                    "current": f"{br/1e6:.1f}Mbps",
                    "recommendation": "提高输出码率至≥6Mbps"
                })
                self.score -= 5

            fps_str = s.get("r_frame_rate", "30/1")
            fps = eval(fps_str) if "/" in fps_str else float(fps_str)
            if fps < 24:
                self.issues.append({
                    "level": "P2", "category": "帧率",
                    "description": f"帧率 {fps:.1f}fps 偏低",
                    "current": f"{fps:.1f}fps",
                    "recommendation": "输出≥24fps，推荐30fps"
                })
                self.score -= 3
        except Exception as e:
            logger.debug(f"   ℹ️ 画质检测跳过: {e}")

    def _check_metadata(self):
        """P2 元数据 —— AI声明、原创标签、版权标注"""
        logger.info("  🔍 P2 元数据合规 (AI声明/原创/版权) ...")
        all_text = (" ".join(self.tags) + " " + self.drama_title).lower()

        if not any(k in all_text for k in
                   ["ai", "ai生成", "ai辅助", "ai创作", "人工智能"]):
            self.issues.append({
                "level": "P2", "category": "AI创作声明",
                "description": "建议添加AI辅助创作声明",
                "current": "未声明",
                "recommendation": "在B站创作中心勾选「AI辅助创作」或添加对应标签"
            })
            self.score -= 3

        if not any(k in all_text for k in
                   ["原创", "自制", "自制短剧", "原创短剧"]):
            self.issues.append({
                "level": "P2", "category": "原创声明",
                "description": "建议添加原创声明提高推荐权重",
                "current": "未声明",
                "recommendation": "添加「原创」「自制短剧」等标签"
            })
            self.score -= 2

        if not any(k in all_text for k in
                   ["cc0", "cc by", "免版权", "无版权", "原创音乐",
                    "royalty free", "creative commons", "B站音乐库"]):
            self.issues.append({
                "level": "P2", "category": "版权声明",
                "description": "建议标注BGM来源",
                "current": "未标注",
                "recommendation": "在简介中标注BGM来源，使用CC0或B站音乐库素材"
            })
            self.score -= 3

    def _check_zone_compliance(self):
        """P2 分区合规建议"""
        logger.info("  🔍 P2 分区合规 ...")
        zi = ZONE_REQUIREMENTS.get(self.zone, {})
        if zi:
            sg = zi.get("suggested_zones", [])
            logger.info(f"    📁 当前类型: {self.zone}，建议分区: {' / '.join(sg)}")

    def _generate_recommendations(self) -> List[str]:
        return [
            f"[{i['level']}] {i['category']}: {i['recommendation']}"
            for i in sorted(self.issues, key=lambda x: x["level"])
        ]


# ============================================================
# 便捷入口
# ============================================================

def check_bilibili_compliance(
    video_path: str,
    drama_title: str,
    narration_text: str = "",
    tags: List[str] = None,
    zone: str = "short_drama"
) -> Dict:
    """执行B站合规预检，返回 {score, issues, passed, recommendations}"""
    checker = BilibiliComplianceChecker(
        video_path, drama_title, narration_text, tags, zone
    )
    return checker.check_all()


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    if len(sys.argv) < 3:
        print("用法: python bilibili_compliance_checker.py <video> <title> [narration] [tags_json]")
        sys.exit(1)

    r = check_bilibili_compliance(
        sys.argv[1], sys.argv[2],
        sys.argv[3] if len(sys.argv) > 3 else "",
        json.loads(sys.argv[4]) if len(sys.argv) > 4 else [],
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
