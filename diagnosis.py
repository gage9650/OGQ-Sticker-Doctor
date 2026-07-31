# diagnosis.py — Claude AI에게 스티커 이미지를 보여주고 진단을 받아오는 로직
import base64  # 이미지를 API로 보낼 수 있는 문자열 형태로 바꿔주는 도구
import anthropic

# AI에게 주는 지시문(프롬프트).
# OGQ 공식 심사 기준과 인기 요소를 그대로 반영해서, 그 관점으로만 진단하게 한다.
SYSTEM_PROMPT = """당신은 NAVER OGQ마켓 스티커 심사 기준을 잘 아는 진단 전문가입니다.
크리에이터가 올린 스티커 이미지를 보고, 아래 OGQ 공식 기준에 따라 진단하세요.

[공식 심사 거절 사유]
- 글씨가 지나치게 많거나, 작거나 선명하지 않아 가독성을 해치는 경우
- 글자에 오탈자가 있는 경우
- 욕설/폭력/선정성/정치·종교색이 짙은 경우
- 커뮤니케이션에 도움이 되지 않는 내용

[공식 권장 사항]
- 다크모드에서 잘 보이도록 흰색 테두리 추가
- 여백 없이 캐릭터를 최대한 크게
- 블로그·댓글 등 일상 대화에서 활용 가능한 내용
- 쉽게 눈에 띄는 개성 있는 표현

반드시 아래 형식의 마크다운으로, 한국어 존댓말로 답하세요:

### 한 줄 총평
(구매자 입장에서의 첫인상 한 문장)

### 심사 리스크
(거절 사유에 해당할 수 있는 항목. 없으면 "발견된 리스크 없음")

### 가독성 · 다크모드
(글씨 크기/선명도, 어두운 배경에서의 시인성 평가)

### 오탈자
(이미지 속 글자를 읽고 오탈자 여부 확인. 글자가 없으면 "텍스트 없음")

### 판매력을 높이는 개선 제안 3가지
1. ...
2. ...
3. ...

추측이 필요한 부분은 "~로 보입니다"라고 표현하고, 이미지에서 확인할 수 없는 것은 지어내지 마세요."""


def diagnose(file_bytes, media_type, api_key):
    """이미지 1장을 Claude에게 보내고 진단 결과(마크다운 텍스트)를 받아온다.

    file_bytes: 이미지 파일의 원본 데이터
    media_type: 파일 종류 (예: "image/png")
    api_key: Anthropic API 키
    """
    client = anthropic.Anthropic(api_key=api_key)

    # 이미지를 base64 문자열로 변환 (API가 요구하는 형식)
    image_data = base64.standard_b64encode(file_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-haiku-4-5",  # 빠르고 저렴한 모델 (이미지 인식 가능)
        max_tokens=1000,           # 답변 최대 길이
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "이 스티커를 진단해주세요.",
                    },
                ],
            }
        ],
    )
    # 응답에서 텍스트 부분만 꺼내서 돌려준다
    return response.content[0].text
