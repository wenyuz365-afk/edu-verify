"""生成学历核验系统流程图"""
from PIL import Image, ImageDraw, ImageFont
import os

W = 1200
H = 2800
img = Image.new('RGB', (W, H), '#0F172A')
draw = ImageDraw.Draw(img)

# 尝试系统字体
font_paths = [
    "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",   # 黑体
    "C:/Windows/Fonts/simsun.ttc",   # 宋体
]
font_file = None
for fp in font_paths:
    if os.path.exists(fp):
        font_file = fp
        break

def get_font(size, bold=False):
    if font_file:
        return ImageFont.truetype(font_file, size)
    return ImageFont.load_default()

# Colors
BG = '#0F172A'
CARD_BG = '#1E293B'
BORDER = '#334155'
GREEN = '#22C55E'
ORANGE = '#F59E0B'
RED = '#EF4444'
BLUE = '#3B82F6'
CYAN = '#06B6D4'
WHITE = '#F1F5F9'
GRAY = '#94A3B8'
PURPLE = '#A855F7'
YELLOW = '#EAB308'

def box(x, y, w, h, color=CARD_BG, border=BORDER, radius=12):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=color, outline=border, width=2)

def text(x, y, s, color=WHITE, size=14, bold=False, center=False):
    f = get_font(size, bold)
    if center:
        bbox = draw.textbbox((0,0), s, font=f)
        tw = bbox[2] - bbox[0]
        x = x - tw // 2
    draw.text((x, y), s, fill=color, font=f)

def arrow_down(x, y, length=30, color=GRAY):
    draw.line([(x, y), (x, y+length)], fill=color, width=2)
    draw.polygon([(x-5, y+length-8), (x+5, y+length-8), (x, y+length)], fill=color)

def section_header(x, y, title, color, icon=""):
    box(x, y, 1050, 48, color=color, border=color)
    text(x+20, y+10, f"{icon} {title}", WHITE, 20, True)

def check_item(x, y, name, result, result_color):
    box(x, y, 320, 36)
    text(x+12, y+7, name, GRAY, 13)
    text(x+320-80, y+7, result, result_color, 13, True)

def note(x, y, s, color=GRAY):
    text(x, y, s, color, 11)

y = 30

# ─── Title ───
text(600, y, "🎓 学历信息AI核验系统 v2.0 完整流程图", WHITE, 28, True, center=True)
y += 50

# ═══════════════════ 上传层 ═══════════════════
section_header(75, y, "📤 上传层", BLUE)
y += 60
box(75, y, 1050, 150)
text(100, y+15, "① 选择招聘渠道", GREEN, 16, True)
text(100, y+42, "  [校招] 有证验真伪，无证→待取证   [社招] 所有学历必须有证   [实习] 已毕业缺证→ALERT，在读跳过", GRAY, 13)
text(100, y+72, "② 选择上传模式", GREEN, 16, True)
text(100, y+99, "  [单人] 动态添加学历层级(本/硕/博)，每层级2证(学位+毕业)   [批量] ZIP压缩包，子文件夹=候选人", GRAY, 13)
text(100, y+126, "③ 上传文件: 学位证 + 毕业证（可选） + 简历（必传）", GREEN, 16, True)
arrow_down(600, y+155)
y += 230

# ═══════════════════ 识别层 ═══════════════════
section_header(75, y, "🔍 识别层", CYAN)
y += 60
box(75, y, 500, 120)
text(100, y+15, "PaddleOCR 2.6.2", CYAN, 16, True)
text(100, y+42, "红色印章去除(HSV) → 自适应缩放(2000px)", GRAY, 13)
text(100, y+62, "CLAHE增强 → 双通道OCR(去印章+原图)", GRAY, 13)
text(100, y+85, "→ 输出: 证书/简历图片的全部文字内容", GREEN, 13)

box(625, y, 500, 120)
text(650, y+15, "DeepSeek V4 Pro (LLM)", CYAN, 16, True)
text(650, y+42, "证书提取: 姓名/性别/出生日期/学校/专业/学历", GRAY, 13)
text(650, y+62, "          学位/毕业日期/签发日期/证书编号", GRAY, 13)
text(650, y+85, "简历提取: [{学校,专业,学历,起止年份,status}]", GRAY, 13)

arrow_down(310, y+125, 20)
arrow_down(810, y+125, 20)
y += 160

# connect two branches
draw.line([(310, y-20), (310, y), (810, y), (810, y-20)], fill=GRAY, width=1)

# ═══════════════════ 核验层 ═══════════════════
section_header(75, y, "🛡️ 核验层 — 模块A: 单证单项核验", PURPLE)
y += 60

# Row 1
check_item(75, y, "教育部名单", "不通过→🚨 ALERT", RED)
check_item(420, y, "学信库查询", "未查到→🚨 ALERT  不一致→⚠️ REVIEW", ORANGE)
check_item(765, y, "证书状态", "结业/肄业→⚠️ REVIEW", ORANGE)
y += 52

# Row 2
check_item(75, y, "毕业年龄", "异常→⚠️ REVIEW", ORANGE)
check_item(420, y, "院校-专业一致性", "不匹配→⚠️ REVIEW", ORANGE)
check_item(765, y, "ELA图片篡改", "low→✅  medium→⚠️  high→🚨", RED)
y += 52

# Module B header
y += 10
section_header(75, y, "🛡️ 核验层 — 模块B: 多材料交叉验证", PURPLE)
y += 60

box(75, y, 510, 130)
text(100, y+15, "双证交叉比对", YELLOW, 16, True)
text(100, y+42, "学位证 vs 毕业证: 姓名/学校/专业/学历/日期", GRAY, 13)
text(100, y+65, "不一致→⚠️ REVIEW", ORANGE, 14, True)
text(100, y+90, "毕业证可选（同等学力/海外可不传）", GRAY, 11)

box(615, y, 510, 130)
text(640, y+15, "简历分层交叉验证", YELLOW, 16, True)
text(640, y+42, "按学历层级逐段比对: 学校(归一化)+专业(包含)+年份(严格)", GRAY, 13)
text(640, y+65, "ongoing/在读→✅跳过  dropout/交换/辅修→✅跳过", CYAN, 13)
text(640, y+90, "已毕业缺证: 社招/实习→🚨ALERT  校招→⚠️REVIEW", ORANGE, 13)

arrow_down(600, y+135)
y += 210

# ─── 判定分流 ───
section_header(75, y, "👨‍💼 判定分流层", GREEN)
y += 60

# 综合判定规则
box(75, y, 1050, 80)
text(100, y+10, "综合判定规则", WHITE, 16, True)
text(100, y+40, "存在🚨ALERT → 🚨 ALERT    无ALERT但有⚠️REVIEW → ⚠️ REVIEW    全部✅ → ✅ PASS", GRAY, 14)
arrow_down(350, y+85, 20)
arrow_down(850, y+85, 20)
y += 100

# Two branches
box(75, y, 500, 130)
text(100, y+15, "✅ PASS", GREEN, 20, True)
text(100, y+50, "自动进入通过名单", GREEN, 14)
text(100, y+75, "无需人工介入", GRAY, 13)

box(625, y, 500, 130)
text(650, y+15, "🚨 ALERT / ⚠️ REVIEW", ORANGE, 20, True)
text(650, y+50, "进入人工核验台 → HR查看原始材料", GRAY, 14)
text(650, y+75, "HR三选一: [✅ pass] [❌ fail] [⏸ hold]", WHITE, 14, True)
text(650, y+100, "已核验可重新判定", GRAY, 11)

arrow_down(325, y+135, 20)
arrow_down(875, y+135, 20)
y += 175

# ═══════════════════ 数据看板 ═══════════════════
section_header(75, y, "📊 数据看板", BLUE)
y += 60

box(75, y, 1050, 100)
text(100, y+15, "📋 全部候选人  │  ✅ 通过  │  ❌ 不通过  │  ⏸ 待定  │  🔴 待核验", WHITE, 16, True)
text(100, y+45, "内联下拉框修改状态 → 自动归类  │  CSV导出  │  实时统计", GRAY, 14)
text(100, y+70, "学信库独立维护(588国内+191海外)  │  简历必传  │  实习已毕业缺证=ALERT", GRAY, 12)

# ─── Footer ───
y += 130
text(600, y, "⚠️ Demo系统 | PaddleOCR 2.6.2 + DeepSeek V4 Pro + Streamlit | 2026.07", GRAY, 11, center=True)

# Save
img.save("D:/edu-verify/学历核验系统流程图.jpg", quality=90)
print(f"Saved: D:/edu-verify/学历核验系统流程图.jpg ({W}x{H})")
