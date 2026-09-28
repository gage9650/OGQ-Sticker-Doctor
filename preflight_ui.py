# preflight_ui.py — 파일별 결과 카드(위치 표시 + 수정 시안). app.py에서 render_card만 호출한다.
import streamlit as st
from checker import SPECS, check_image, locate_issues
from preflight import SEV_COLOR, SEV_LABEL, load_rgba, overlay, fit_content, add_outline, to_png


def _fails(results):
    return sum(1 for g, _, _ in results if g == "fail")


def render_card(name, file_bytes, img_type, results):
    uid = f"{name}_{len(file_bytes)}"
    rgba = load_rgba(file_bytes)
    loc = locate_issues(file_bytes, img_type)
    col1, col2 = st.columns([1, 2])
    sel = None

    with col2:
        for grade, item, msg in results:  # 기존 자동 검사 결과 (변경 없음)
            if grade == "pass":
                st.success(f"**{item}** — {msg}")
            elif grade == "warn":
                st.warning(f"**{item}** — {msg}")
            else:
                st.error(f"**{item}** — {msg}")
        if loc:
            st.markdown("**📍 위치가 표시되는 추가 진단** · 점수에는 반영되지 않아요")
            sel = st.radio("추가 진단 선택", range(len(loc)), key=f"loc_{uid}", label_visibility="collapsed",
                           format_func=lambda i: f"{SEV_LABEL[loc[i]['sev']]} · {loc[i]['title']}")
            it = loc[sel]
            x0, y0, x1, y1 = it["bbox"]
            st.markdown(
                f"<div style='border-left:5px solid {SEV_COLOR[it['sev']]};padding:8px 12px;background:#EEFBF9;border-radius:6px'>"
                f"<b>{it['title']}</b><br>📍 위치: x {x0}–{x1}, y {y0}–{y1}<br>📏 적용 규칙: {it['rule']}<br>"
                f"❓ 판단 근거: {it['why']}<br>🛠 수정 방법: {it['fix']}<br>"
                f"<small>코드가 계산한 실측값이에요 (AI 추정 아님)</small></div>", unsafe_allow_html=True)

    with col1:
        st.image(overlay(rgba, loc, sel) if loc else file_bytes)

    if st.toggle("🛠 수정 시안 만들기 (원본은 그대로 유지돼요)", key=f"fx_{uid}"):
        tw, th = SPECS.get(img_type) or rgba.size
        o1, o2 = st.columns(2)
        refit = o1.checkbox("여백 없이 최대한 크게", key=f"refit_{uid}")
        px = o2.slider("흰색 외곽선 두께 px (다크모드 대응, 0=없음)", 0, 8, 0, key=f"px_{uid}")
        fixed = fit_content(rgba, (tw, th)) if refit else rgba
        if px:
            fixed = add_outline(fixed, px)
        fb = to_png(fixed)
        ftype, fres = check_image(fb, name)
        floc = locate_issues(fb, ftype)
        a, b = st.columns(2)
        a.image(overlay(rgba, loc), use_container_width=True,
                caption=f"원본 · {len(file_bytes) / 1024:.0f}KB · 필수 위반 {_fails(results)}건 · 추가 진단 {len(loc)}건")
        b.image(overlay(fixed, floc), use_container_width=True,
                caption=f"수정 시안 · {len(fb) / 1024:.0f}KB · 필수 위반 {_fails(fres)}건 · 추가 진단 {len(floc)}건")
        st.download_button("⬇️ 수정 시안 PNG 다운로드", fb, f"{name.rsplit('.', 1)[0]}_fixed.png", "image/png", key=f"dl_{uid}")
        st.caption("재배치·외곽선 같은 기계적 변환의 결과예요. 재검사 결과도 위 규칙 기준일 뿐, 심사 통과를 보장하지 않아요.")
