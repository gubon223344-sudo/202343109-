"""행정 도우미 챗봇의 대화 규칙 (Streamlit 없이도 동작하는 순수 파이썬 모듈)

respond(message, state) 함수에 사용자 메시지와 현재 대화 상태를 넣으면
(챗봇 답변, 새 대화 상태)를 돌려준다.
"""

import re
from datetime import date, datetime

# ---------------------------------------------------------------
# 1. 자주 묻는 질문 (키워드 -> 답변)
# ---------------------------------------------------------------
FAQ = [
    {
        "keywords": ["증명서", "재직", "경력증명", "발급"],
        "title": "증명서 발급",
        "answer": (
            "📄 **증명서 발급 안내**\n\n"
            "1. 그룹웨어 → [인사] → [증명서 신청] 메뉴로 이동\n"
            "2. 증명서 종류(재직·경력)와 용도, 매수를 선택\n"
            "3. 신청 후 결재가 끝나면 PDF로 바로 출력할 수 있어요\n\n"
            "⏱ 보통 당일 처리되고, 직인이 필요한 원본은 1~2일 걸려요."
        ),
    },
    {
        "keywords": ["휴가", "연차", "반차", "병가"],
        "title": "휴가 신청",
        "answer": (
            "🏖 **휴가 신청 안내**\n\n"
            "1. 그룹웨어 → [근태] → [휴가 신청]\n"
            "2. 휴가 종류(연차·반차·병가)와 기간 입력\n"
            "3. 팀장 결재 후 확정돼요\n\n"
            "💡 연차는 사용일 **3일 전**까지, 병가는 복귀 후 진단서를 첨부해 주세요."
        ),
    },
    {
        "keywords": ["비품", "사무용품", "소모품", "토너", "복사용지"],
        "title": "비품 신청",
        "answer": (
            "🖊 **비품 신청 안내**\n\n"
            "1. 그룹웨어 → [총무] → [비품 신청서] 작성\n"
            "2. 품목, 수량, 사용 부서를 입력\n"
            "3. 매주 **수요일**에 일괄 구매해 금요일에 배부해요\n\n"
            "급한 소모품(복사용지, 토너)은 총무팀 비품실에서 바로 받을 수 있어요."
        ),
    },
    {
        "keywords": ["출장", "정산", "여비", "영수증"],
        "title": "출장비 정산",
        "answer": (
            "🧾 **출장비 정산 안내**\n\n"
            "1. 출장 복귀 후 **7일 이내**에 출장 보고서와 정산서 제출\n"
            "2. 교통비·숙박비 영수증(카드 전표)을 반드시 첨부\n"
            "3. 회계팀 검토 후 다음 급여일에 함께 지급돼요\n\n"
            "💡 법인카드로 결제한 항목은 정산서에 '법인카드'로 표시해 주세요."
        ),
    },
    {
        "keywords": ["단축키", "엑셀", "excel"],
        "title": "엑셀 단축키",
        "answer": (
            "⌨️ **자주 쓰는 엑셀 단축키**\n\n"
            "| 기능 | 단축키 |\n|---|---|\n"
            "| 오늘 날짜 입력 | Ctrl + ; |\n"
            "| 셀 서식 | Ctrl + 1 |\n"
            "| 표 끝으로 이동 | Ctrl + 방향키 |\n"
            "| 빠른 채우기 | Ctrl + E |\n"
            "| 필터 켜기/끄기 | Ctrl + Shift + L |\n"
            "| 절대참조 전환 | F4 |"
        ),
    },
]

ROOMS = ["대회의실(20명)", "소회의실 A(8명)", "소회의실 B(6명)"]
ROOM_CAPACITY = {ROOMS[0]: 20, ROOMS[1]: 8, ROOMS[2]: 6}

WELCOME = (
    "안녕하세요! 저는 **행정 도우미 챗봇**이에요 🤖\n\n"
    "이런 것들을 도와드릴 수 있어요.\n\n"
    "- 📄 증명서 발급 · 🏖 휴가 신청 · 🖊 비품 신청\n"
    "- 🧾 출장비 정산 · ⌨️ 엑셀 단축키\n"
    "- 🏢 **회의실 예약** (대화로 차근차근 진행해요)\n\n"
    "궁금한 내용을 편하게 입력하거나 왼쪽 메뉴 버튼을 눌러 보세요."
)

HELP = (
    "💬 **이렇게 물어보세요**\n\n"
    "- \"재직증명서 어떻게 떼요?\"\n"
    "- \"연차 신청 방법 알려줘\"\n"
    "- \"회의실 예약할래\"\n"
    "- \"엑셀 단축키\"\n\n"
    "진행 중인 예약을 멈추려면 **취소**라고 입력하면 돼요."
)


def new_state():
    """대화 상태 초기값. step이 None이면 일반 대화, 값이 있으면 예약 진행 중."""
    return {"step": None, "booking": {}, "bookings": []}


# ---------------------------------------------------------------
# 2. 입력값 해석 도우미
# ---------------------------------------------------------------
def parse_date(text):
    """'2026-12-03', '12/3', '12월 3일', '오늘', '내일' 형식을 date로 바꾼다."""
    text = text.strip()
    today = date.today()
    if "오늘" in text:
        return today
    if "내일" in text:
        return date.fromordinal(today.toordinal() + 1)
    m = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", text)
    year_given = m is not None
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})\s*(?:월|[/.-])\s*(\d{1,2})", text)
        if not m:
            return None
        y = today.year
        mo, d = map(int, m.groups())
    try:
        result = date(y, mo, d)
        # 연도 없이 이미 지난 날짜를 쓰면 내년 날짜로 본다 (예: 12월에 "1월 5일")
        if not year_given and result < today:
            result = date(y + 1, mo, d)
    except ValueError:
        return None
    return result


def parse_time(text):
    """'14:00', '오후 2시', '2시 30분' 형식을 'HH:MM'으로 바꾼다."""
    m = re.search(r"(\d{1,2})\s*[:시]\s*(\d{1,2})?", text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    # "오후 2시"는 14시로, 업무 시간에 맞춰 "오전" 없이 쓴 1~8시도 오후로 본다
    if hour < 12 and ("오후" in text or (1 <= hour <= 8 and "오전" not in text)):
        hour += 12
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_number(text):
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


# ---------------------------------------------------------------
# 3. 회의실 예약: 날짜 → 시간 → 인원 → 회의실 → 확인 (여러 턴 대화)
# ---------------------------------------------------------------
def booking_step(message, state):
    step = state["step"]
    booking = state["booking"]

    if step == "date":
        d = parse_date(message)
        if d is None:
            return "날짜를 알아보기 어려워요. **12월 3일**, **2026-12-03**, **내일**처럼 입력해 주세요.", state
        if d < date.today():
            return "지난 날짜는 예약할 수 없어요. 오늘 이후 날짜를 입력해 주세요.", state
        booking["date"] = d.isoformat()
        state["step"] = "time"
        return f"📅 **{d.month}월 {d.day}일**로 할게요.\n\n몇 시에 사용하시나요? (예: 오후 2시, 14:00)", state

    if step == "time":
        t = parse_time(message)
        if t is None:
            return "시간을 알아보기 어려워요. **오후 2시** 또는 **14:00**처럼 입력해 주세요.", state
        if not ("09:00" <= t <= "18:00"):
            return "회의실은 **09:00~18:00** 사이에만 예약할 수 있어요. 다시 입력해 주세요.", state
        booking["time"] = t
        state["step"] = "people"
        return f"⏰ **{t}** 시작이에요.\n\n참석 인원은 몇 명인가요?", state

    if step == "people":
        n = parse_number(message)
        if n is None or n <= 0:
            return "인원을 숫자로 입력해 주세요. (예: 5명)", state
        if n > 20:
            return "가장 큰 대회의실이 20명까지라서 예약이 어려워요. 20명 이하로 입력해 주세요.", state
        booking["people"] = n
        options = [r for r in ROOMS if ROOM_CAPACITY[r] >= n]
        state["step"] = "room"
        listing = "\n".join(f"{i}. {r}" for i, r in enumerate(options, 1))
        booking["options"] = options
        return f"👥 **{n}명**이 들어갈 수 있는 회의실이에요.\n\n{listing}\n\n번호를 입력해 주세요.", state

    if step == "room":
        n = parse_number(message)
        options = booking["options"]
        if n is None or not (1 <= n <= len(options)):
            return f"1부터 {len(options)} 사이의 번호를 입력해 주세요.", state
        booking["room"] = options[n - 1]
        state["step"] = "confirm"
        d = date.fromisoformat(booking["date"])
        return (
            "✅ **예약 내용을 확인해 주세요**\n\n"
            f"- 날짜: {d.month}월 {d.day}일\n"
            f"- 시간: {booking['time']}\n"
            f"- 인원: {booking['people']}명\n"
            f"- 회의실: {booking['room']}\n\n"
            "이대로 예약할까요? (**네** / **아니요**)"
        ), state

    if step == "confirm":
        if any(w in message for w in ["네", "예", "응", "좋아", "확인", "yes"]):
            done = {k: v for k, v in booking.items() if k != "options"}
            done["created"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            state["bookings"].append(done)
            state["step"], state["booking"] = None, {}
            return (
                f"🎉 **{done['room']}** 예약이 완료됐어요!\n\n"
                "왼쪽 사이드바의 '내 예약 목록'에서 확인할 수 있어요. 더 도와드릴 일이 있나요?"
            ), state
        if any(w in message for w in ["아니", "no", "다시"]):
            state["step"], state["booking"] = None, {}
            return "예약을 진행하지 않았어요. 다시 하시려면 **회의실 예약**이라고 입력해 주세요.", state
        return "**네** 또는 **아니요**로 답해 주세요.", state

    state["step"] = None
    return "다시 시작할게요. 무엇을 도와드릴까요?", state


# ---------------------------------------------------------------
# 4. 메인 응답 함수
# ---------------------------------------------------------------
def respond(message, state):
    message = message.strip()
    if not message:
        return "메시지를 입력해 주세요.", state

    # 예약 진행 중일 때: 취소가 아니면 예약 단계를 이어간다
    if state["step"]:
        if "취소" in message or "그만" in message:
            state["step"], state["booking"] = None, {}
            return "회의실 예약을 취소했어요. 다른 도움이 필요하면 말씀해 주세요.", state
        return booking_step(message, state)

    low = message.lower()

    if any(w in low for w in ["안녕", "하이", "hello", "hi", "반가"]):
        return WELCOME, state
    if any(w in low for w in ["도움", "도와", "help", "뭐 할 수", "기능"]):
        return HELP, state
    if "회의실" in low or "예약" in low:
        if "목록" in low or "확인" in low:
            return booking_list(state), state
        state["step"], state["booking"] = "date", {}
        return "🏢 **회의실 예약**을 시작할게요.\n\n어느 날짜에 사용하시나요? (예: 12월 3일, 내일)", state
    if any(w in low for w in ["고마", "감사", "땡큐", "thanks"]):
        return "천만에요! 언제든 다시 불러 주세요 😊", state

    for item in FAQ:
        if any(k in low for k in item["keywords"]):
            return item["answer"], state

    return (
        "죄송해요, 아직 그 질문은 잘 모르겠어요 😅\n\n"
        "**증명서, 휴가, 비품, 출장비, 엑셀 단축키, 회의실 예약** 중에서 물어봐 주시거나 "
        "**도움말**이라고 입력해 보세요."
    ), state


def booking_list(state):
    if not state["bookings"]:
        return "아직 예약한 회의실이 없어요. **회의실 예약**이라고 입력해 시작해 보세요."
    lines = []
    for b in state["bookings"]:
        d = date.fromisoformat(b["date"])
        lines.append(f"- {d.month}월 {d.day}일 {b['time']} · {b['room']} · {b['people']}명")
    return "📋 **내 예약 목록**\n\n" + "\n".join(lines)
