"""행정 도우미 챗봇 - Streamlit 웹 응용 시스템

실행: streamlit run app.py
"""

from datetime import date

import streamlit as st

from bot_logic import WELCOME, new_state, respond

# ---------------- 페이지 기본 설정 ----------------
st.set_page_config(page_title="행정 도우미 챗봇", page_icon="🤖", layout="centered")

# ---------------- 비밀번호 확인 ----------------
# 비밀번호를 맞게 입력하기 전에는 챗봇 화면을 보여주지 않는다.
PASSWORD = "pnumis"

if not st.session_state.get("authenticated", False):
    st.title("🔒 행정 도우미 챗봇")
    st.caption("비밀번호를 입력해야 사용할 수 있어요.")
    with st.form("login"):
        pw = st.text_input("비밀번호", type="password")
        ok = st.form_submit_button("입장하기", use_container_width=True)
    if ok:
        if pw == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 맞지 않아요. 다시 입력해 주세요.")
    st.stop()  # 여기서 멈추므로 아래 챗봇 화면은 실행되지 않는다

# ---------------- 세션 상태 초기화 ----------------
# Streamlit은 입력할 때마다 스크립트를 처음부터 다시 실행하므로
# 대화 기록과 예약 상태는 st.session_state에 보관한다.
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
if "bot_state" not in st.session_state:
    st.session_state.bot_state = new_state()


def send(text):
    """사용자 메시지를 기록하고 챗봇 답변을 받아 기록한다."""
    st.session_state.messages.append({"role": "user", "content": text})
    reply, st.session_state.bot_state = respond(text, st.session_state.bot_state)
    st.session_state.messages.append({"role": "assistant", "content": reply})


# ---------------- 채팅 입력 ----------------
# 입력창은 화면 맨 아래에 고정된다. 사이드바(예약 목록)보다 먼저 처리해야
# 방금 완료한 예약이 같은 화면에 바로 보인다.
user_text = st.chat_input("메시지를 입력하세요 (예: 연차 신청 방법)")
if user_text:
    send(user_text)

# ---------------- 사이드바 ----------------
with st.sidebar:
    st.header("📌 빠른 메뉴")
    st.caption("버튼을 누르면 해당 질문이 바로 전송돼요.")
    quick = {
        "📄 증명서 발급": "증명서 발급 방법",
        "🏖 휴가 신청": "휴가 신청 방법",
        "🖊 비품 신청": "비품 신청 방법",
        "🧾 출장비 정산": "출장비 정산 방법",
        "⌨️ 엑셀 단축키": "엑셀 단축키",
        "🏢 회의실 예약": "회의실 예약",
    }
    for label, question in quick.items():
        if st.button(label, use_container_width=True):
            send(question)

    st.divider()
    st.subheader("📋 내 예약 목록")
    bookings = st.session_state.bot_state["bookings"]
    if bookings:
        for b in bookings:
            d = date.fromisoformat(b["date"])
            st.info(f"{d.month}/{d.day} {b['time']}\n\n{b['room']} · {b['people']}명")
    else:
        st.caption("아직 예약이 없어요.")

    st.divider()
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
        st.session_state.bot_state = new_state()
        st.rerun()

# ---------------- 메인 화면 ----------------
st.title("🤖 행정 도우미 챗봇")
st.caption("증명서·휴가·비품·출장비 안내와 회의실 예약을 대화로 도와드려요.")

if st.session_state.bot_state["step"]:
    st.warning("🏢 회의실 예약 진행 중이에요. 그만두려면 '취소'라고 입력하세요.")

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "🙂"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
