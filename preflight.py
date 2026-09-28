# preflight.py — 문제 위치 표시 + 수정 시안용 이미지 유틸 (Streamlit 의존 없음)
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# checker.py의 등급 이름(fail/warn/info)을 그대로 쓴다
SEV_COLOR = {"fail": "#e5484d", "warn": "#f76b15", "info": "#d6a400"}
SEV_LABEL = {"fail": "🔴 필수 수정", "warn": "🟠 주의", "info": "🟡 개선 권장"}


def load_rgba(file_bytes):
    return Image.open(io.BytesIO(file_bytes)).convert("RGBA")


def _checker(size, s=12):
    """투명 영역이 보이도록 깔아주는 체크무늬 배경"""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    v = np.where(((xx // s) + (yy // s)) % 2 == 0, 235, 200).astype("uint8")
    return Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]), "RGBA")


def overlay(rgba, issues, sel=None):
    """문제 위치(bbox)를 등급 색 박스로 그린 미리보기. sel번째 문제는 굵게."""
    base = Image.alpha_composite(_checker(rgba.size), rgba).convert("RGB")
    d = ImageDraw.Draw(base)
    for i, it in enumerate(issues):
        if it.get("bbox"):
            d.rectangle(it["bbox"], outline=SEV_COLOR[it["sev"]], width=max(rgba.size) // 60 + 2 if i == sel else 2)
    return base


def fit_content(rgba, size, margin=4):
    """공식 권장 '여백 없이 최대한 크게': 그림 영역만 잘라 캔버스에 꽉 차게 키워 중앙 배치"""
    bb = rgba.getchannel("A").getbbox() or (0, 0, *rgba.size)
    c = rgba.crop(bb)
    tw, th = size
    sc = min((tw - 2 * margin) / c.width, (th - 2 * margin) / c.height)
    c = c.resize((max(1, int(c.width * sc)), max(1, int(c.height * sc))), Image.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(c, ((tw - c.width) // 2, (th - c.height) // 2), c)
    return out


def add_outline(rgba, px, color=(255, 255, 255)):
    """공식 권장 '다크모드용 흰색 테두리'"""
    grown = rgba.getchannel("A").filter(ImageFilter.MaxFilter(2 * px + 1))
    layer = Image.new("RGBA", rgba.size, color + (255,))
    layer.putalpha(grown)
    return Image.alpha_composite(layer, rgba)


def to_png(rgba):
    # 256색 양자화는 컬러 모드가 P로 바뀌어 기존 '컬러 모드/투명 배경' 검사에 실패하므로 넣지 않았다
    b = io.BytesIO()
    rgba.save(b, "PNG", optimize=True)
    return b.getvalue()
