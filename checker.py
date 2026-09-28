# checker.py — OGQ 공식 스펙 기준으로 스티커 이미지를 검사하는 로직
# 공식 가이드 출처: https://creators.ogq.me/guides/contents/sticker
from PIL import Image  # Pillow: 파이썬에서 이미지를 다루는 대표 라이브러리
import io

# OGQ 공식 규격 (가로px, 세로px)
SPECS = {
    "메인 이미지": (240, 240),   # 1개 필요
    "스티커 이미지": (740, 640),  # 24개 필요
    "탭 이미지": (96, 74),       # 1개 필요
}

MAX_BYTES = 1 * 1024 * 1024  # 1MB (공식 기준: 각 이미지 1MB 이하)


def classify_type(width, height):
    """이미지 크기를 보고 어떤 종류(메인/스티커/탭)인지 알아낸다.
    규격에 안 맞으면 None을 돌려준다."""
    for name, (w, h) in SPECS.items():
        if width == w and height == h:
            return name
    return None


def check_transparency(img):
    """배경이 투명인지 검사한다.
    방법: 알파 채널(투명도 정보)이 있는지 + 네 모서리 픽셀이 투명한지 확인."""
    if img.mode != "RGBA":
        return False, "알파 채널(투명도 정보)이 없는 이미지예요."
    w, h = img.size
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    # 모서리 픽셀의 알파값이 0이면 완전 투명
    opaque_corners = sum(1 for c in corners if img.getpixel(c)[3] > 10)
    if opaque_corners >= 3:
        return False, "모서리가 불투명해요. 배경이 투명이 아닐 가능성이 높아요."
    return True, "배경이 투명으로 보여요."


def check_margin(img):
    """여백이 과한지 검사한다.
    방법: 실제 그림이 있는 영역(알파값 존재 영역)이 전체 캔버스에서
    차지하는 비율을 계산한다. 공식 가이드: '여백이 가급적 없도록 최대한 크게'."""
    if img.mode != "RGBA":
        return None, "투명도 정보가 없어 여백을 측정할 수 없어요."
    bbox = img.getchannel("A").getbbox()  # 그림이 존재하는 최소 사각형
    if bbox is None:
        return None, "이미지가 완전히 비어 있어요."
    content_w = bbox[2] - bbox[0]
    content_h = bbox[3] - bbox[1]
    ratio = (content_w * content_h) / (img.size[0] * img.size[1])
    return ratio, f"그림이 캔버스의 {ratio:.0%}를 차지해요."


def check_image(file_bytes, filename):
    """이미지 1장에 대해 모든 검사를 실행하고 결과 목록을 돌려준다.
    결과 형식: (등급, 검사항목, 설명) — 등급은 pass / warn / fail"""
    results = []
    img = Image.open(io.BytesIO(file_bytes))
    w, h = img.size

    # 검사 1: 파일 형식 (스티커는 투명 배경이 필요하므로 PNG가 표준)
    if img.format == "PNG":
        results.append(("pass", "파일 형식", "PNG 형식이에요."))
    else:
        results.append(("fail", "파일 형식",
                        f"{img.format} 형식이에요. 투명 배경을 지원하는 PNG로 저장해주세요. "
                        "(확장자만 바꾸면 심사에서 거절돼요 — 원본부터 PNG로 내보내야 해요)"))

    # 검사 2: 크기 규격
    img_type = classify_type(w, h)
    if img_type:
        results.append(("pass", "크기 규격", f"{w}x{h}px — '{img_type}' 규격에 맞아요."))
    else:
        spec_text = ", ".join(f"{n} {s[0]}x{s[1]}" for n, s in SPECS.items())
        results.append(("fail", "크기 규격",
                        f"{w}x{h}px — OGQ 규격({spec_text})에 맞지 않아요."))

    # 검사 3: 용량
    size = len(file_bytes)
    if size <= MAX_BYTES:
        results.append(("pass", "용량", f"{size / 1024:.0f}KB — 1MB 이하 통과."))
    else:
        results.append(("fail", "용량", f"{size / 1024 / 1024:.2f}MB — 1MB를 넘어요. 압축이 필요해요."))

    # 검사 4: 컬러 모드 (공식 기준: RGB. RGBA는 RGB+투명도이므로 통과)
    if img.mode in ("RGB", "RGBA"):
        results.append(("pass", "컬러 모드", f"{img.mode} — RGB 계열 통과."))
    else:
        results.append(("fail", "컬러 모드",
                        f"{img.mode} 모드예요. RGB로 변환해서 저장해주세요."))

    # 검사 5: 투명 배경
    ok, msg = check_transparency(img)
    results.append(("pass" if ok else "fail", "투명 배경", msg))

    # 검사 6: 여백 (fail은 아니고 개선 제안 수준)
    ratio, msg = check_margin(img)
    if ratio is None:
        results.append(("warn", "여백", msg))
    elif ratio >= 0.6:
        results.append(("pass", "여백", msg + " 캔버스를 잘 활용하고 있어요."))
    else:
        results.append(("warn", "여백",
                        msg + " 공식 가이드는 '여백 없이 최대한 크게'를 권장해요."))

    return img_type, results


# ======================================================================
# 위치(bbox)가 있는 추가 진단 — 점수·PDF에는 반영하지 않는다
# (반영하면 항목 수가 바뀌어 저장된 재검사 히스토리와 점수가 이어지지 않기 때문)
# ======================================================================
import numpy as np
from PIL import ImageFilter


def _lum(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c @ np.array([0.2126, 0.7152, 0.0722])


def _edge_contrast(arr, bg):
    """그림 외곽 픽셀과 배경색의 명암비(WCAG 공식). 외곽 픽셀이 너무 적으면 None."""
    mask = arr[..., 3] > 200
    inner = np.array(Image.fromarray((mask * 255).astype("uint8")).filter(ImageFilter.MinFilter(5))) > 0
    edge = mask & ~inner
    if edge.sum() < 20:
        return None
    l1, l2 = _lum(arr[..., :3][edge]).mean(), float(_lum(bg))
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def locate_issues(file_bytes, img_type=None):
    """위치가 있는 추가 진단 목록: [{sev(fail/warn/info), title, rule, why, fix, bbox}]
    모든 값은 코드가 계산한 실측이며 AI 추정이 아니다."""
    img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    w, h = img.size
    arr = np.array(img)
    a = arr[..., 3]
    if a.min() == 255:
        return []  # 투명 정보가 없으면 가리킬 위치가 없다 (기존 검사가 이미 fail 처리)
    out = []

    # 1) 불투명 모서리 (기존 check_transparency와 같은 기준: 모서리 알파 > 10)
    cs = max(min(w, h) // 6, 8)
    corners = {"좌상": ((0, 0), (0, 0, cs, cs)), "우상": ((w - 1, 0), (w - cs, 0, w, cs)),
               "좌하": ((0, h - 1), (0, h - cs, cs, h)), "우하": ((w - 1, h - 1), (w - cs, h - cs, w, h))}
    for k, ((x, y), box) in corners.items():
        if a[y, x] > 10:
            out.append({"sev": "warn", "title": f"{k} 모서리가 불투명",
                        "rule": "투명 배경 (모서리 픽셀 알파 10 초과 시 표시)",
                        "why": f"이 모서리 픽셀의 알파값이 {int(a[y, x])}이라 배경이 남아 있을 수 있어요.",
                        "fix": "배경을 완전히 제거하고 PNG로 다시 저장하세요.", "bbox": box})

    bb = img.getchannel("A").getbbox()
    if bb:
        # 2) 여백 과다 (기존 check_margin과 같은 기준: 그림 영역 ≥ 캔버스의 60%)
        ratio = (bb[2] - bb[0]) * (bb[3] - bb[1]) / (w * h)
        if ratio < 0.6:
            out.append({"sev": "info", "title": "여백이 커요",
                        "rule": "공식 가이드: 여백 없이 최대한 크게 (내부 기준: 캔버스 면적의 60% 이상)",
                        "why": f"그림이 캔버스의 {ratio:.0%}만 차지해요. 표시된 박스가 실제 그림 영역이에요.",
                        "fix": "아래 '여백 없이 최대한 크게' 시안을 써보세요.", "bbox": bb})
        # 3) 다크모드 외곽 시인성
        c = _edge_contrast(arr, (30, 30, 30))
        if c is not None and c < 1.5:
            out.append({"sev": "warn", "title": "다크모드에서 외곽이 배경과 섞여요",
                        "rule": "공식 권장: 다크모드용 흰색 테두리 (내부 휴리스틱: 외곽-배경 명암비 1.5:1 이상, 공식 수치 아님)",
                        "why": f"그림 외곽과 어두운 배경(#1E1E1E)의 명암비가 {c:.2f}:1로 측정됐어요.",
                        "fix": "아래 '흰색 외곽선' 시안을 써보세요.", "bbox": bb})
    return out
