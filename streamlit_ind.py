import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import uuid
import json
from langchain_mistralai import ChatMistralAI


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Annabelle - Polymer In Stock",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Annabelle - Polymer In Stock")


# =========================================================
# LLM
# =========================================================
llm = ChatMistralAI(
    model="mistral-small-2506",
    temperature=0
)


# =========================================================
# REQUIRED FIELDS
# =========================================================
REQUIRED_FIELDS = [
    "contact_person",
    "persona",
    "product_required",
    "quantity_required",
    "company_name",
    "email_address",
    "country",
    "port_preference"
]


# =========================================================
# STATE EXTRACTION
# =========================================================
def extract_lead_data(message: str, state: dict):

    prompt = f"""
Extract structured lead data.

Return ONLY valid JSON.

FIELDS:
contact_person, persona, product_required, quantity_required,
company_name, email_address, country, port_preference

RULES:
- Use null if unknown
- No markdown
- No explanation

STATE:
{json.dumps(state)}

MESSAGE:
{message}
"""

    try:
        res = llm.invoke(prompt)

        content = (
            res.content
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        return json.loads(content)

    except Exception:
        return {}

EXAMPLES = """

EXAMPLE 1

USER:
hi

ASSISTANT:
Hello! Thank you for your inquiry. My name is Annabelle from Polymer In Stock.
May I ask your name?


-----------------------------------

EXAMPLE 2

USER:
usama

ASSISTANT:
Nice to meet you, Usama! Are you looking to buy materials, or do you have materials to sell us?

-----------------------------------

EXAMPLE 3


USER:
buy
ASSISTANT:
Great! Please visit our website to explore our full product range:"
www.polymerinstock.com
"Which material are you interested in?



-----------------------------------

EXAMPLE 4

USER:
i need pvc and abs

ASSISTANT:
Great! Could you share the grade you need — virgin/prime, near prime, off grade, or recycled?


-----------------------------------

EXAMPLE 5

USER:
virgin prime

ASSISTANT:
Would you also be open to near prime or off-grade material? It offers similar processing performance at a better price.


-----------------------------------

EXAMPLE 6

USER:
yes

ASSISTANT:
Could you share the MFI (Melt Flow Index) and approximate quantity required?


-----------------------------------

EXAMPLE 7
USER:
3000 kg

ASSISTANT:
Unfortunately our minimum order quantity is 25 metric tons. Are you able to proceed with 25 MT or more?


-----------------------------------

EXAMPLE 8

USER:
yes

ASSISTANT:
Could you share your company name and email address?


-----------------------------------

EXAMPLE 9

USER:
company is abc polymers and email is abc@gmail.com

ASSISTANT:
Thank you! What is your preferred port of destination?


-----------------------------------

EXAMPLE 10


USER:
i want to sell pp scrap

ASSISTANT:
Please contact our procurement specialist directly:
Marie Joy Villa | +971 50 920 3834


-----------------------------------

EXAMPLE 12

USER:
yes

ASSISTANT:
Could you share your company name and email address?


IMPORTANT BEHAVIOR RULES:

- NEVER ask about application/use case
- NEVER repeat already confirmed information
- If user says "yes", treat it as confirmation to ALL pending questions from previous assistant message
- DO NOT validate the same information repeatedly
- Keep replies short
- Move the lead forward efficiently
- Sound human and professional
"""
# =========================================================
# WHATSAPP REPLY
# =========================================================
def decide_next_question(state, latest_message, examples=EXAMPLES):

    prompt = f"""
You are Annabelle.

You are a B2B polymer sales qualification assistant.

Your job is NOT to blindly ask fields.

You must reason dynamically.

CURRENT LEAD STATE:
{json.dumps(state, indent=2)}

LATEST CUSTOMER MESSAGE:
{latest_message}
Examples of good replies:
{examples}

Rules:

1. Ask intelligently based on context.Be friendly, direct, and professional — like a knowledgeable salesperson, not a formal customer service rep.

2. Prioritize understanding:
   - material (MUST ask material prior asking for grade and quantity).
   - grade/spec
   - quantity
   before collecting admin details.

3. FIELDS to get if not in chat_history
contact_person, persona, product_required, quantity_required,
company_name, email_address, country, port_preference must not ask irrelevant questions/information.

4. If customer asks unrelated questions,
   handle them naturally.

5. If customer wants SELL:
   redirect politely.

6. Keep replies SHORT.
   Max 2–3 lines.

7. Try collecting multiple missing details
   in ONE concise message when appropriate.

8. MUST NOT repeat known information in next/any succeeding message.

9. If enough info exists,
   move toward:
   company / email / port.

10. Sound human, not robotic.


Return ONLY the assistant reply text.
"""

    try:
        res = llm.invoke(prompt)
        return res.content.strip()

    except Exception:
        return "Could you share more details about your requirement?"


# =========================================================
# EMAIL REPLY
# =========================================================
def decide_email_reply(state, latest_message, missing):

    prompt = f"""
You are Annabelle, a professional B2B export sales executive.

You are replying to an EMAIL.

STATE:
{json.dumps(state, indent=2)}

MISSING:
{missing}

CUSTOMER EMAIL:
{latest_message}

RULES:

- Write formal email ONLY
- No chat tone
- No repetition
- Combine all missing questions in ONE structured block
- Max 8 lines
- No emojis

FORMAT:

Dear Sir/Madam,

Brief acknowledgment (1-2 lines)

If product mentioned → confirm briefly

Then ask missing fields as bullet points:
- Company name
- Email
- Quantity
- Country
- Port

End:
Best regards,
Annabelle
Polymer In Stock

OUTPUT ONLY EMAIL BODY
"""

    try:
        res = llm.invoke(prompt)
        return res.content.strip()

    except Exception:
        return """
Dear Sir/Madam,

Thank you for your inquiry.

Could you please share your material requirement, quantity, company name, and destination country?

Best regards,
Annabelle
Polymer In Stock
"""


# =========================================================
# MAIN FLOW ENGINE
# =========================================================
def handle_message(message, state, channel="whatsapp"):

    state = state or {}

    chat_history = state.get("chat_history", [])

    chat_history.append(f"client: {message}")

    # ----------------------------
    # EXTRACT STATE
    # ----------------------------
    extracted = extract_lead_data(message, state)

    for k, v in extracted.items():
        if v not in [None, "", "null"]:
            state[k] = v

    # ----------------------------
    # FIRST MESSAGE
    # ----------------------------
    if not state.get("contact_person") and len(chat_history) <= 1:

        reply = (
            "Hello! Thank you for your inquiry.\n"
            "My name is Annabelle from Polymer In Stock.\n"
            "May I know your name?"
        )

        chat_history.append(f"assistant: {reply}")

        state["chat_history"] = chat_history

        return reply, state

    # ----------------------------
    # CHECK COMPLETION
    # ----------------------------
    missing = [
        f for f in REQUIRED_FIELDS
        if not state.get(f)
    ]

    if not missing:

        reply = (
            "Thank you for sharing your requirements.\n"
            "Our product specialist will contact you within 3–4 business days."
        )

        chat_history.append(f"assistant: {reply}")

        state["chat_history"] = chat_history
        state["step"] = "DONE"

        return reply, state

    # ----------------------------
    # CHANNEL ROUTING
    # ----------------------------
    if channel == "email":
        reply = decide_email_reply(
            state,
            message,
            missing
        )
    else:
        reply = decide_next_question(
            state,
            message,
            missing
        )

    chat_history.append(f"assistant: {reply}")

    state["chat_history"] = chat_history
    state["step"] = "ACTIVE"

    return reply, state


# =========================================================
# SESSION STATE
# =========================================================
if "whatsapp_messages" not in st.session_state:
    st.session_state.whatsapp_messages = []

if "whatsapp_state" not in st.session_state:
    st.session_state.whatsapp_state = {
        "RF": str(uuid.uuid4())[:8],
        "chat_history": [],
        "channel": "whatsapp"
    }

if "email_state" not in st.session_state:
    st.session_state.email_state = {
        "RF": str(uuid.uuid4())[:8],
        "chat_history": [],
        "channel": "email"
    }


# =========================================================
# TABS
# =========================================================
tab1, tab2 = st.tabs([
    "💬 WhatsApp Demo",
    "📧 Email Demo"
])


# =========================================================
# WHATSAPP TAB
# =========================================================
with tab1:

    st.subheader("WhatsApp Simulation")

    # =====================================================
    # INIT FIRST MESSAGE
    # =====================================================
    if len(st.session_state.whatsapp_messages) == 0:

        reply, state = handle_message(
            "start",
            st.session_state.whatsapp_state,
            "whatsapp"
        )

        st.session_state.whatsapp_state = state

        st.session_state.whatsapp_messages.append({
            "role": "assistant",
            "content": reply
        })

    # =====================================================
    # DISPLAY CHAT (IMPORTANT: DO THIS FIRST)
    # =====================================================
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.whatsapp_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # =====================================================
    # INPUT (MUST ALWAYS BE LAST)
    # =====================================================
    prompt = st.chat_input("Type your message...")

    if prompt:

        # add user message
        st.session_state.whatsapp_messages.append({
            "role": "user",
            "content": prompt
        })

        reply, state = handle_message(
            prompt,
            st.session_state.whatsapp_state,
            "whatsapp"
        )

        st.session_state.whatsapp_state = state

        # add assistant message
        st.session_state.whatsapp_messages.append({
            "role": "assistant",
            "content": reply
        })

        # rerun to force clean bottom rendering
        st.rerun()

    # =====================================================
    # RESET
    # =====================================================
    if st.button("Reset WhatsApp Demo"):

        st.session_state.whatsapp_messages = []
        st.session_state.whatsapp_state = {
            "RF": str(uuid.uuid4())[:8],
            "chat_history": [],
            "channel": "whatsapp"
        }

        st.rerun()

# =========================================================
# EMAIL TAB
# =========================================================
with tab2:

    st.subheader("Email Inbox Simulation")

    email_from = st.text_input("From Email")
    subject = st.text_input("Subject")
    email_body = st.text_area(
        "Email Content",
        height=220
    )

    if st.button("Generate Email Reply"):

        reply, state = handle_message(
            email_body,
            st.session_state.email_state,
            "email"
        )

        st.session_state.email_state = state

        st.success("Email processed successfully")

        formatted_email = f"""
Subject: Re: {subject}

{reply}
"""

        st.markdown("### Generated Email Reply")

        st.code(
            formatted_email,
            language="text"
        )

        st.markdown("### Extracted Lead State")

        st.json(state)

    # RESET
    if st.button("Reset Email Demo"):

        st.session_state.email_state = {
            "RF": str(uuid.uuid4())[:8],
            "chat_history": [],
            "channel": "email"
        }

        st.rerun()