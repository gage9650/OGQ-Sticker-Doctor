# app.py — OGQ 스티커 닥터: 화면(UI) 담당
# 검사 로직은 checker.py에 분리되어 있다.
import streamlit as st
from checker import check_image, SPECS
from diagnosis import diagnose

st.set_page_config(page_title="OGQ 스티커 닥터", page_icon="🩺")

st.title("🩺 OGQ 스티커 닥터")
st.write("스티커가 안 팔리는 이유를 진단하고, 심사 통과와 판매를 도와주는 AI 도구입니다.")

# ---------- 1단계: 이미지 스펙 검사 ----------
st.header("1단계 · 심사 스펙 자동 검사")
st.caption("OGQ 공식 제작 가이드 기준: 메인 240x240 · 스티커 740x640 · 탭 96x74, 각 1MB 이하, RGB, 투명 배경")

# 여러 장을 한 번에 올릴 수 있는 업로드 버튼
files = st.file_uploader(
    "스티커 이미지를 올려주세요 (여러 장 가능)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if files:
    # 종류별로 몇 장 올라왔는지 세기 위한 준비
    type_counts = {name: 0 for name in SPECS}

    for f in files:
        file_bytes = f.getvalue()  # 업로드된 파일의 실제 데이터(바이트)
        img_type, results = check_image(file_bytes, f.name)
        if img_type:
            type_counts[img_type] += 1

        # 파일마다 접을 수 있는 결과 박스 표시
        fail_count = sum(1 for grade, _, _ in results if grade == "fail")
        icon = "❌" if fail_count else "✅"
        with st.expander(f"{icon} {f.name} — 문제 {fail_count}건", expanded=fail_count > 0):
            col1, col2 = st.columns([1, 2])  # 왼쪽: 미리보기 / 오른쪽: 결과
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

            # ---------- 2단계: AI 진단 ----------
            st.divider()
            # 같은 파일을 다시 진단하지 않도록, 받은 결과를 세션에 저장해둔다
            cache_key = f"diag_{f.name}_{len(file_bytes)}"

            if cache_key in st.session_state:
                st.markdown(st.session_state[cache_key])
            elif st.button(f"🧠 AI 심층 진단 받기", key=f"btn_{cache_key}"):
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
                if not api_key:
                    st.error("API 키가 설정되지 않았어요. .streamlit/secrets.toml을 확인해주세요.")
                else:
                    with st.spinner("AI가 스티커를 살펴보는 중..."):
                        try:
                            result = diagnose(file_bytes, f.type, api_key)
                            st.session_state[cache_key] = result
                            st.markdown(result)
                        except Exception as e:
                            st.error(f"진단 중 오류가 발생했어요: {e}")

    # ---------- 제출 구성 요약 ----------
    st.subheader("제출 구성 체크")
    st.write("OGQ 제출 규격: 메인 1개 · 스티커 24개 · 탭 1개")
    need = {"메인 이미지": 1, "스티커 이미지": 24, "탭 이미지": 1}
    for name, required in need.items():
        have = type_counts[name]
        if have == required:
            st.success(f"{name}: {have}/{required} 완료")
        else:
            st.info(f"{name}: {have}/{required}")
else:
    st.info("이미지를 올리면 OGQ 심사 기준에 맞는지 즉시 검사해드려요.")
