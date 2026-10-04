import streamlit as st
import pandas as pd
import os
import random
import time
from streamlit_gsheets import GSheetsConnection

# تنظیمات اولیه صفحه
st.set_page_config(page_title="آزمون حافظه اتوبیوگرافیک (AMT)", layout="centered")

# -------------------------------------------------------------------
# استایل راست‌‌چین (RTL) و فونت بزرگ برای کلمه
# -------------------------------------------------------------------
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], div[data-testid="stMarkdownContainer"] {
        direction: rtl;
        text-align: right;
    }
    input, textarea {
        direction: rtl !important;
        text-align: right !important;
    }
    label {
        direction: rtl !important;
        text-align: right !important;
    }
    /* باکس نمایش کلمه با اندازه فونت بسیار بزرگ */
    .word-box {
        background-color: #f0f4f8;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        font-size: 65px;
        font-weight: 900;
        color: #0d47a1;
        margin-top: 15px;
        margin-bottom: 25px;
        border: 3px solid #90caf9;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .hidden-word-box {
        background-color: #fff8e1;
        border-radius: 16px;
        padding: 30px 20px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #f57f17;
        margin-top: 15px;
        margin-bottom: 25px;
        border: 2px dashed #ffe082;
    }
    .instruction-card {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        border-right: 5px solid #1f77b4;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        line-height: 1.8;
    }
    .example-card {
        background-color: #e8f4f8;
        border-radius: 6px;
        padding: 12px 15px;
        margin-top: 10px;
        font-size: 15px;
    }
    </style>
""", unsafe_allow_html=True)

AMT_FILE = "amt_responses.csv"
MAX_VIEW_TIME = 30  # حداکثر زمان یادآوری کلمه (۳۰ ثانیه)
TYPE_TIME = 60      # زمان تایپ پس از ناپدید شدن (۶۰ ثانیه)

def save_data(data_dict):
    """ذخیره همزمان در فایل محلی CSV و Google Sheets"""
    # ۱. ذخیره محلی در CSV
    df_new = pd.DataFrame([data_dict])
    file_exists = os.path.isfile(AMT_FILE)
    df_new.to_csv(AMT_FILE, mode='a' if file_exists else 'w', header=not file_exists, index=False, encoding='utf-8-sig')

    # ۲. ذخیره آنلاین در Google Sheets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)
        updated_df = pd.concat([existing_data, df_new], ignore_index=True)
        conn.update(data=updated_df)
    except Exception as e:
        st.error(f"⚠️ خطای اتصال/ذخیره در گوگل شیت: {e}")

if 'page' not in st.session_state:
    st.session_state.page = 'intro'

if 'subject_id' not in st.session_state:
    st.session_state.subject_id = ""

# -------------------------------------------------------------------
# کلمات آزمون
# -------------------------------------------------------------------
if 'amt_words' not in st.session_state:
    pos_words = [("مثبت", w) for w in ["شاد", "موفق", "امیدوار", "آرام", "دوست داشتنی", "افتخار"]]
    neg_words = [("منفی", w) for w in ["غمگین", "شکست", "تنها", "نا امید", "بی ارزش", "خسته"]]
    neu_words = [("خنثی", w) for w in ["میز", "صندلی", "لیوان", "دیوار", "خودکار", "نیمکت"]]
    
    all_words = pos_words + neg_words + neu_words
    random.shuffle(all_words)
    st.session_state.amt_words = all_words

if 'word_index' not in st.session_state:
    st.session_state.word_index = 0

if 'phase' not in st.session_state:
    st.session_state.phase = 'viewing'  # دو حالت: 'viewing' یا 'typing'

if 'phase_start_time' not in st.session_state:
    st.session_state.phase_start_time = None

if 'view_duration' not in st.session_state:
    st.session_state.view_duration = 0.0

if 'typed_memory_text' not in st.session_state:
    st.session_state.typed_memory_text = ""

# ===================================================================
# بخش ۱: راهنمای آزمون
# ===================================================================
if st.session_state.page == 'intro':
    st.title("آزمون حافظه اتوبیوگرافیک (AMT)")
    
    st.markdown("""
    <div class="instruction-card">
        <h3>دستورالعمل آزمون:</h3>
        <p>در این آزمون ما می‌خواهیم بدانیم شما تا چه اندازه می‌توانید <b>خاطرات خاص زندگی خود</b> را به یاد آورید.</p>
        <p>منظور از خاطره، اتفاقی است که در <b>زمان و مکان خاصی</b> اتفاق افتاده و <b>یک روز یا کمتر از یک روز</b> طول کشیده است.</p>
        <ul>
            <li>این خاطره می‌تواند مربوط به <b>روزهای اخیر یا زمان‌های گذشته</b> باشد.</li>
            <li>این خاطره می‌تواند یک اتفاق <b>مهم یا کاملاً عادی</b> در زندگی باشد.</li>
            <li>برای هر لغت باید <b>فقط یک خاطره</b> تعریف کنید.</li>
            <li>خاطره نباید برای لغت‌های مختلف <b>تکرار شود</b>.</li>
        </ul>
        <p><b>روند زمان‌بندی:</b></p>
        <ul>
            <li>برای یادآوری هر کلمه حداکثر <b>۳۰ ثانیه</b> فرصت دارید.</li>
            <li>به محض اینکه خاطره‌ای به ذهنتان آمد، سریعاً روی دکمه <b>«خاطره به ذهنم آمد / شروع تایپ»</b> کلیک کنید.</li>
            <li>اگر در مدت ۳۰ ثانیه خاطره‌ای به یاد نیاوردید، سیستم به‌طور خودکار کلمه بعدی را نمایش می‌دهد.</li>
            <li>پس از کلیک روی دکمه، کلمه مخفی شده و <b>۶۰ ثانیه</b> فرصت تایپ خواهید داشت.</li>
        </ul>
        <div class="example-card">
            <b>مثال:</b> کلمه <b>«معلم»</b> را مشاهده می‌کنید. به محض یادآوری دکمه را می‌زنید و خاطره خاص خود را تایپ می‌کنید:<br>
            <i>«سال گذشته روز معلم، معلممان از هدیه‌ای که من به او دادم خیلی خوشش آمد و من را بوسید.»</i>
        </div>
    </div>
    """, unsafe_allow_html=True)

    subject_input = st.text_input("لطفاً کد / شناسه شرکت‌کننده را وارد کنید:")

    if st.button("شروع آزمون"):
        if not subject_input.strip():
            st.error("لطفاً ابتدا شناسه شرکت‌کننده را وارد کنید.")
        else:
            st.session_state.subject_id = subject_input.strip()
            st.session_state.page = 'amt_task'
            st.session_state.phase = 'viewing'
            st.session_state.phase_start_time = time.time()
            st.rerun()

# ===================================================================
# بخش ۲: اجرای آزمون
# ===================================================================
elif st.session_state.page == 'amt_task':
    words = st.session_state.amt_words
    current_idx = st.session_state.word_index
    total_words = len(words)

    if current_idx < total_words:
        category, word = words[current_idx]
        
        st.caption(f"کلمه {current_idx + 1} از {total_words}")

        elapsed = time.time() - st.session_state.phase_start_time

        # ---------------------------------------------------------------
        # فاز ۱: مشاهده کلمه (حداکثر ۳۰ ثانیه برای یادآوری)
        # ---------------------------------------------------------------
        if st.session_state.phase == 'viewing':
            if elapsed < MAX_VIEW_TIME:
                rem_view = int(MAX_VIEW_TIME - elapsed)
                st.markdown(f'<div class="word-box">{word}</div>', unsafe_allow_html=True)
                st.info(f"👀 **فرصت یادآوری:** {rem_view} ثانیه باقی‌مانده است...")
                
                if st.button("💡 خاطره به ذهنم آمد / شروع تایپ", use_container_width=True):
                    st.session_state.view_duration = round(elapsed, 2)
                    st.session_state.phase = 'typing'
                    st.session_state.phase_start_time = time.time()
                    st.session_state.typed_memory_text = ""
                    st.rerun()
            else:
                # اگر ۳۰ ثانیه تمام شد و دکمه را نزد
                record = {
                    "Subject_ID": st.session_state.subject_id,
                    "Word_Index": current_idx + 1,
                    "Word": word,
                    "Category": category,
                    "Response_Text": "بدون پاسخ (عدم یادآوری در ۳۰ ثانیه)",
                    "Retrieval_Latency_Sec": MAX_VIEW_TIME,
                    "Typing_Duration_Sec": 0,
                    "Total_Time_Sec": MAX_VIEW_TIME,
                    "Time_Out": True
                }
                save_data(record)

                st.session_state.word_index += 1
                st.session_state.phase = 'viewing'
                st.session_state.phase_start_time = time.time()
                st.rerun()

        # ---------------------------------------------------------------
        # فاز ۲: ناپدید شدن کلمه و ۶۰ ثانیه فرصت تایپ
        # ---------------------------------------------------------------
        elif st.session_state.phase == 'typing':
            if elapsed < TYPE_TIME:
                rem_type = int(TYPE_TIME - elapsed)
                st.markdown('<div class="hidden-word-box">🙈 کلمه ناپدید شد! خاطره خود را تایپ کنید.</div>', unsafe_allow_html=True)
                st.warning(f"✍️ **زمان باقی‌مانده جهت تایپ خاطره:** {rem_type} ثانیه")

                # باکس متنی مستقیم
                memory_text = st.text_area(
                    "خاطره خود را تایپ کنید:",
                    value=st.session_state.typed_memory_text,
                    key=f"amt_text_{current_idx}",
                    height=140
                )
                st.session_state.typed_memory_text = memory_text

                if st.button("ثبت و کلمه بعدی", use_container_width=True):
                    typing_time = round(time.time() - st.session_state.phase_start_time, 2)
                    
                    record = {
                        "Subject_ID": st.session_state.subject_id,
                        "Word_Index": current_idx + 1,
                        "Word": word,
                        "Category": category,
                        "Response_Text": memory_text.strip() if memory_text.strip() else "خالی",
                        "Retrieval_Latency_Sec": st.session_state.view_duration,
                        "Typing_Duration_Sec": typing_time,
                        "Total_Time_Sec": round(st.session_state.view_duration + typing_time, 2),
                        "Time_Out": False
                    }
                    save_data(record)

                    # آماده‌سازی برای کلمه بعدی
                    st.session_state.typed_memory_text = ""
                    st.session_state.word_index += 1
                    st.session_state.phase = 'viewing'
                    st.session_state.phase_start_time = time.time()
                    st.rerun()
            else:
                # اتمام زمان تایپ (۶۰ ثانیه) - حفظ متن تایپ‌شده تا لحظه آخر
                current_text = st.session_state.get(f"amt_text_{current_idx}", st.session_state.typed_memory_text)
                final_text = current_text.strip() if current_text.strip() else "نیمه‌کاره (اتمام ۶۰ ثانیه تایپ)"
                
                record = {
                    "Subject_ID": st.session_state.subject_id,
                    "Word_Index": current_idx + 1,
                    "Word": word,
                    "Category": category,
                    "Response_Text": final_text,
                    "Retrieval_Latency_Sec": st.session_state.view_duration,
                    "Typing_Duration_Sec": TYPE_TIME,
                    "Total_Time_Sec": round(st.session_state.view_duration + TYPE_TIME, 2),
                    "Time_Out": True
                }
                save_data(record)

                st.session_state.typed_memory_text = ""
                st.session_state.word_index += 1
                st.session_state.phase = 'viewing'
                st.session_state.phase_start_time = time.time()
                st.rerun()

        time.sleep(1)
        st.rerun()

    else:
        st.session_state.page = 'thank_you'
        st.rerun()

# ===================================================================
# بخش ۳: پایان آزمون
# ===================================================================
elif st.session_state.page == 'thank_you':
    st.header("پایان آزمون")
    st.balloons()
    st.success("پاسخ‌ها و زمان‌های ثبت خاطرات شما با موفقیت ذخیره شد.")
    st.write(f"فایل نتایج در مسیر برنامه با نام **`{AMT_FILE}`** ایجاد شد.")