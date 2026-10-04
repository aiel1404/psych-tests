import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. تنظیمات اولیه صفحه
# ==========================================
st.set_page_config(
    page_title="آزمون حافظه خودزندگینامه‌ای (AMT)",
    page_icon="🧠",
    layout="centered"
)

# ==========================================
# 2. لیست کلمات آزمون (دسته‌بندی و هنجاریابی‌شده)
# ==========================================
WORD_LIST = [
    # کلمات مثبت
    {"word": "موفق", "category": "Positive"},
    {"word": "امیدوار", "category": "Positive"},
    {"word": "شاد", "category": "Positive"},
    # کلمات خنثی
    {"word": "میز", "category": "Neutral"},
    {"word": "صندلی", "category": "Neutral"},
    {"word": "پنجره", "category": "Neutral"},
    # کلمات منفی
    {"word": "غمگین", "category": "Negative"},
    {"word": "شکست", "category": "Negative"},
    {"word": "اضطراب", "category": "Negative"},
]

MAX_TIME_LIMIT = 60.0  # حداکثر زمان مجاز برای هر کلمه (ثانیه)

# ==========================================
# 3. مدیریت Session State
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = "INTAKE"  # مراحل: INTAKE -> INSTRUCTIONS -> TEST -> FINISHED

if "subject_id" not in st.session_state:
    st.session_state.subject_id = ""

if "current_word_index" not in st.session_state:
    st.session_state.current_word_index = 0

if "all_responses" not in st.session_state:
    st.session_state.all_responses = []

if "word_start_time" not in st.session_state:
    st.session_state.word_start_time = None

if "first_char_time" not in st.session_state:
    st.session_state.first_char_time = None

# ==========================================
# 4. تابع همگام‌سازی با Google Sheets
# ==========================================
def sync_all_data_to_gsheets():
    """ارسال تمام داده‌های ثبت‌شده آزمون به Google Sheets بر اساس Environment Variables"""
    if not st.session_state.all_responses:
        return True
    
    try:
        df_new = pd.DataFrame(st.session_state.all_responses)
        
        # اتصال خودکار که پارامترها را مستقیم از Environment Variables می‌خواند
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # خواندن داده‌های موجود (ttl=0 برای عدم کش)
        try:
            existing_data = conn.read(ttl=0)
            updated_df = pd.concat([existing_data, df_new], ignore_index=True)
        except Exception:
            # اگر شیت کاملا خالی بود
            updated_df = df_new
        
        # به‌روزرسانی شیت
        conn.update(data=updated_df)
        return True
    except Exception as e:
        st.error(f"⚠️ خطای اتصال/ذخیره نهایی در گوگل شیت: {e}")
        return False

# ==========================================
# 5. جریان اجرای برنامه (Flow Control)
# ==========================================

# --- مرحله ۱: دریافت اطلاعات اولیه شرکت‌کننده ---
if st.session_state.step == "INTAKE":
    st.title("🧠 آزمون حافظه خودزندگینامه‌ای (AMT)")
    st.write("لطفاً شناسه یا کد شرکت‌کننده را وارد کنید:")
    
    subject_input = st.text_input("شناسه شرکت‌کننده (Subject ID):", value=st.session_state.subject_id)
    
    if st.button("تایید و ادامه"):
        if subject_input.strip() == "":
            st.warning("لطفاً شناسه را وارد کنید.")
        else:
            st.session_state.subject_id = subject_input.strip()
            st.session_state.step = "INSTRUCTIONS"
            st.rerun()

# --- مرحله ۲: راهنمای آزمون ---
elif st.session_state.step == "INSTRUCTIONS":
    st.title("راهنمای اجرای آزمون")
    st.markdown("""
    در این آزمون یک سری کلمات به شما نشان داده می‌شود.
    
    * با دیدن هر کلمه، سعی کنید **اولین خاطره مشخصی** (مرتبط با زمان و مکان خاص) که به ذهنتان می‌رسد را یادداشت کنید.
    * برای هر کلمه حداکثر **۶۰ ثانیه** زمان دارید.
    * پس از تایپ خاطره، روی دکمه **«ثبت و کلمه بعدی»** کلیک کنید.
    """)
    
    if st.button("شروع آزمون"):
        st.session_state.step = "TEST"
        st.session_state.current_word_index = 0
        st.session_state.word_start_time = time.time()
        st.session_state.first_char_time = None
        st.rerun()

# --- مرحله ۳: اجرای کلمات آزمون ---
elif st.session_state.step == "TEST":
    idx = st.session_state.current_word_index
    total_words = len(WORD_LIST)
    
    if idx < total_words:
        current_item = WORD_LIST[idx]
        word = current_item["word"]
        category = current_item["category"]
        
        st.progress((idx) / total_words)
        st.subheader(f"کلمه {idx + 1} از {total_words}")
        st.markdown(f"# **{word}**")
        
        # محاسبه زمان سپری‌شده
        elapsed_time = time.time() - st.session_state.word_start_time
        
        # کنترل تایم‌اوت 60 ثانیه‌ای
        if elapsed_time > MAX_TIME_LIMIT:
            st.warning("⏰ زمان ۶۰ ثانیه‌ای این کلمه به پایان رسید.")
            # ثبت پاسخ اتمام زمان
            st.session_state.all_responses.append({
                "Subject_ID": st.session_state.subject_id,
                "Word_Index": idx + 1,
                "Word": word,
                "Category": category,
                "Response_Text": "[TIME_OUT]",
                "Retrieval_Latency_Sec": None,
                "Typing_Duration_Sec": None,
                "Total_Time_Sec": round(elapsed_time, 2),
                "Time_Out": True
            })
            
            # رفتن به کلمه بعدی
            st.session_state.current_word_index += 1
            st.session_state.word_start_time = time.time()
            st.session_state.first_char_time = None
            st.rerun()

        # فرم دریافت خاطره
        with st.form(key=f"word_form_{idx}"):
            response_text = st.text_area("خاطره خود را بنویسید:", key=f"text_{idx}")
            submit_button = st.form_submit_button("ثبت و کلمه بعدی")
            
            # ثبت زمان شروع تایپ (اولین کاراکتر)
            if response_text and st.session_state.first_char_time is None:
                st.session_state.first_char_time = time.time()
            
            if submit_button:
                end_time = time.time()
                total_time = end_time - st.session_state.word_start_time
                
                # محاسبه زمان بازیابی (تا شروع تایپ) و زمان تایپ
                if st.session_state.first_char_time:
                    retrieval_latency = st.session_state.first_char_time - st.session_state.word_start_time
                    typing_duration = end_time - st.session_state.first_char_time
                else:
                    retrieval_latency = total_time
                    typing_duration = 0.0

                # ذخیره در session_state
                st.session_state.all_responses.append({
                    "Subject_ID": st.session_state.subject_id,
                    "Word_Index": idx + 1,
                    "Word": word,
                    "Category": category,
                    "Response_Text": response_text,
                    "Retrieval_Latency_Sec": round(retrieval_latency, 2),
                    "Typing_Duration_Sec": round(typing_duration, 2),
                    "Total_Time_Sec": round(total_time, 2),
                    "Time_Out": False
                })

                # ارتقا به کلمه بعدی
                st.session_state.current_word_index += 1
                st.session_state.word_start_time = time.time()
                st.session_state.first_char_time = None
                st.rerun()

    else:
        st.session_state.step = "FINISHED"
        st.rerun()

# --- مرحله ۴: پایان آزمون و ذخیره‌سازی داده‌ها ---
elif st.session_state.step == "FINISHED":
    st.title("پایان آزمون")
    st.success("با تشکر، پاسخ‌های شما با موفقیت ثبت شد.")
    
    with st.spinner("در حال ارسال پاسخ‌ها به گوگل شیت..."):
        success = sync_all_data_to_gsheets()
        if success:
            st.balloons()
            st.info("اطلاعات با موفقیت در گوگل شیت ذخیره شد.")
        else:
            st.error("خطا در ارسال داده‌ها به گوگل شیت. لطفا با پشتیبان تماس بگیرید.")