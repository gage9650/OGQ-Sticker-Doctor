# app.py — OGQ 스티커 닥터: 화면(UI) 담당
# 검사 로직은 checker.py, AI 진단은 diagnosis.py, 리포트/히스토리는 report_utils.py에 분리되어 있다.
# 디자인: 민트/틸 헬스케어 톤
# 신규 기능: 세트 전체 일괄 진단 / 개선 우선순위 Todo / PDF 리포트 / 규정 위반 체크리스트 / 재검사 히스토리 비교

import streamlit as st
from checker import check_image, SPECS
from diagnosis import diagnose
from report_utils import (
    build_priority_todo, compute_score, build_pdf_report,
    load_history, save_history_entry,
)

st.set_page_config(
    page_title="OGQ 스티커 닥터",
    page_icon="🩺",
    layout="centered",
)

# ---------- 커스텀 CSS: 민트/틸 헬스케어 톤 ----------
st.markdown(
    """
    <style>
    :root {
        --mint-primary: #0F9B8E;
        --mint-light: #EEFBF9;
        --mint-border: #BFEFE9;
    }
    div[data-testid="stExpander"] {
        border: 1px solid var(--mint-border);
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(15, 155, 142, 0.08);
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary { font-weight: 600; }
    button[kind="secondary"], button[kind="primary"] {
        border-radius: 999px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stFileUploaderDropzone"] {
        border-radius: 14px;
        border: 1.5px dashed var(--mint-border);
        background-color: var(--mint-light);
    }
    .hero-banner {
        background: linear-gradient(135deg, #0F9B8E 0%, #14B8A6 100%);
        border-radius: 18px;
        padding: 28px 32px;
        color: white;
        margin-bottom: 28px;
    }
    .hero-banner h1 { margin: 0 0 6px 0; font-size: 1.6rem; }
    .hero-banner p { margin: 0; opacity: 0.92; font-size: 0.95rem; }

    .score-card {
        background: var(--mint-light);
        border: 1px solid var(--mint-border);
        border-radius: 16px;
        padding: 18px 22px;
        margin-bottom: 20px;
    }
    .score-card .score-num {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--mint-primary);
    }
    .todo-row {
        border-left: 4px solid var(--mint-primary);
        background: white;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 8px;
    }
    .todo-row.fail { border-left-color: #B3261E; }
    .todo-row.warn { border-left-color: #8A6300; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 히어로 섹션 ----------
st.markdown(
    """
    <div class="hero-banner">
        <h1>🩺 OGQ 스티커 닥터</h1>
        <p>스티커가 안 팔리는 이유를 진단하고, 심사 통과와 판매를 도와주는 AI 도구입니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- 1단계: 이미지 스펙 검사 ----------
st.header("1단계 · 심사 스펙 자동 검사")
st.caption("OGQ 공식 제작 가이드 기준: 메인 240x240 · 스티커 740x640 · 탭 96x74, 각 1MB 이하, RGB, 투명 배경")

files = st.file_uploader(
    "스티커 이미지를 올려주세요 (여러 장 가능)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if files:
    type_counts = {name: 0 for name in SPECS}
    all_file_results = []  # [{"name", "bytes", "mime", "img_type", "results"}]

    for f in files:
        file_bytes = f.getvalue()
        img_type, results = check_image(file_bytes, f.name)
        if img_type:
            type_counts[img_type] += 1
        all_file_results.append({
            "name": f.name, "bytes": file_bytes, "mime": f.type,
            "img_type": img_type, "results": results,
        })

        fail_count = sum(1 for grade, _, _ in results if grade == "fail")
        icon = "❌" if fail_count else "✅"
        with st.expander(f"{icon} {f.name} — 문제 {fail_count}건", expanded=fail_count > 0):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(file_bytes)
            with col2:
                for grade, item, msg in results:
                    if grade == "pass":
                        st.success(f"**{item}** — {msg}")
                    elif grade == "warn":
                        st.warning(f"**{item}** — {msg}")
                    else:
                        st.error(f"**{item}** — {msg}")

    # ---------- 2단계: 세트 전체 일괄 AI 진단 ----------
    st.divider()
    st.header("2단계 · AI 심층 진단 (세트 일괄)")
    st.caption("파일마다 따로 누를 필요 없이, 업로드한 스티커 전체를 한 번에 진단합니다.")

    if st.button(f"🧠 업로드한 {len(files)}개 전체 AI 진단 받기", type="primary"):
        api_key = st.secrets.get("GEMINI_API_KEY")

        st.write("Secret 확인:", "GEMINI_API_KEY" in st.secrets)
        st.write("API Key 길이:", len(api_key) if api_key else 0)
        
        if not api_key:
            st.error("API 키가 설정되지 않았어요.")
        else:
            progress = st.progress(0, text="AI가 스티커 세트를 살펴보는 중...")
            for i, file_result in enumerate(all_file_results):
                cache_key = f"diag_{file_result['name']}_{len(file_result['bytes'])}"
                if cache_key not in st.session_state:
                    try:
                        result = diagnose(file_result["bytes"], file_result["mime"], api_key)
                        st.session_state[cache_key] = result
                    except Exception as e:
                        st.session_state[cache_key] = f"진단 중 오류가 발생했어요: {e}"
                progress.progress((i + 1) / len(all_file_results), text=f"{i + 1}/{len(all_file_results)} 완료")
            progress.empty()
            st.success("전체 진단이 끝났어요. 아래 파일별 결과와 우선순위 Todo를 확인하세요.")

    # 파일별 AI 진단 결과 표시 (이미 진단했다면)
    for file_result in all_file_results:
        cache_key = f"diag_{file_result['name']}_{len(file_result['bytes'])}"
        if cache_key in st.session_state:
            with st.expander(f"🧠 AI 진단 결과 — {file_result['name']}"):
                st.markdown(st.session_state[cache_key])

    # ---------- 3단계: 규정 위반 셀프 체크리스트 ----------
    st.divider()
    st.header("3단계 · 규정 위반 셀프 체크리스트")
    st.caption("이 항목들은 이미지만 보고 자동으로 판단하기 어려워 직접 확인이 필요해요. (OGQ 반려 사유 기준)")

    checklist_items = {
        "저작권 있는 폰트를 상업적으로 이용 가능한 라이선스로만 사용했다": "font_license",
        "생성형 AI로 제작한 이미지가 아니다 (또는 AI 사용 규정을 확인했다)": "no_ai_violation",
        "다른 판매자의 기존 콘텐츠와 중복되지 않는다": "no_duplicate",
        "텍스트가 여백 없이 잘리지 않고, 세이프존 안에 들어와 있다": "text_safezone",
        "욕설·폭력·선정성·정치/종교 색채가 짙은 내용이 없다": "no_sensitive_content",
    }
    checklist_status = {}
    for label, key in checklist_items.items():
        checklist_status[label] = st.checkbox(label, key=f"chk_{key}")

    checklist_done = sum(1 for v in checklist_status.values() if v)
    checklist_total = len(checklist_items)
    st.caption(f"체크리스트 {checklist_done}/{checklist_total} 완료")

    # ---------- 4단계: 심사 통과 확률 스코어 + 우선순위 Todo ----------
    st.divider()
    st.header("4단계 · 심사 통과 확률 & 개선 우선순위")

    score = compute_score(all_file_results, checklist_done, checklist_total)
    st.markdown(
        f"""
        <div class="score-card">
            <div>심사 통과 확률 스코어</div>
            <div class="score-num">{score:.0f}점 <span style="font-size:1rem; font-weight:400;">/ 100점</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    todo_list = build_priority_todo(all_file_results)
    if todo_list:
        st.subheader("이것부터 고치세요")
        for i, t in enumerate(todo_list, start=1):
            grade_label = "❌ 실패" if t["grade"] == "fail" else "⚠️ 주의"
            css_class = "fail" if t["grade"] == "fail" else "warn"
            st.markdown(
                f"""
                <div class="todo-row {css_class}">
                    <b>{i}. {grade_label} · {t['item']}</b><br/>
                    {t['msg']}<br/>
                    <small>영향받은 파일 {t['affected_count']}개: {', '.join(t['affected_files'][:5])}
                    {' 외' if len(t['affected_files']) > 5 else ''}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("자동 검사 기준으로 고칠 항목이 없어요!")

    # ---------- 5단계: PDF 리포트 + 재검사 히스토리 ----------
    st.divider()
    st.header("5단계 · 리포트 내보내기 & 재검사 히스토리")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📄 PDF 리포트 생성"):
            diagnosis_texts = {}
            for fr in all_file_results:
                ck = f"diag_{fr['name']}_{len(fr['bytes'])}"
                if ck in st.session_state:
                    diagnosis_texts[fr["name"]] = st.session_state[ck]
            pdf_bytes = build_pdf_report(all_file_results, todo_list, score, checklist_status, diagnosis_texts)
            st.download_button(
                "⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name="ogq_sticker_doctor_report.pdf",
                mime="application/pdf",
            )
    with col_b:
        if st.button("💾 이번 결과를 히스토리에 저장"):
            pass_count = sum(1 for fr in all_file_results for g, _, _ in fr["results"] if g == "pass")
            warn_count = sum(1 for fr in all_file_results for g, _, _ in fr["results"] if g == "warn")
            fail_count = sum(1 for fr in all_file_results for g, _, _ in fr["results"] if g == "fail")
            save_history_entry(score, pass_count, warn_count, fail_count, checklist_done, checklist_total)
            st.success("히스토리에 저장했어요. 수정 후 다시 검사하고 또 저장하면 변화가 아래 그래프에 쌓여요.")

    history = load_history()
    if len(history) >= 2:
        st.subheader("재검사 히스토리 (점수 변화 추적)")
        st.line_chart({"score": [h["score"] for h in history]})
        st.caption(f"최근 {len(history)}회 검사 · 마지막: {history[-1]['timestamp']} ({history[-1]['score']}점)")
    elif len(history) == 1:
        st.caption("아직 히스토리가 1개예요. 수정 후 다시 저장하면 변화 그래프가 나타납니다.")

    # ---------- 제출 구성 요약 ----------
    st.divider()
    st.subheader("제출 구성 체크")
    st.caption("OGQ 제출 규격: 메인 1개 · 스티커 24개 · 탭 1개")
    need = {"메인 이미지": 1, "스티커 이미지": 24, "탭 이미지": 1}
    for name, required in need.items():
        have = type_counts[name]
        st.write(f"**{name}**  {have} / {required}")
        st.progress(min(have / required, 1.0))
else:
    st.info("이미지를 올리면 OGQ 심사 기준에 맞는지 즉시 검사해드려요.")
