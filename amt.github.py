import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# ۱. تنظیمات اولیه صفحه
st.set_page_config(page_title="آزمون AMT", page_icon="🧠", layout="centered")

st.title("آزمون حافظه سرگذشتی (AMT)")
st.write("لطفاً پس از مشاهده کلمه محرک، خاطره خود را تایپ کنید. شما ۶۰ ثانیه زمان دارید.")

# ۲. راه‌اندازی اتصال به گوگل شیت
conn = st.connection("gsheets", type=GSheetsConnection)

# ۳. تابع ذخیره‌سازی داده در گوگل شیت
def save_amt_gsheet(record_dict):
    try:
        # خواندن داده‌های فعلی از تب AMT_Data
        existing_data = conn.read(worksheet="AMT_Data", ttl=0)
        df_existing = pd.DataFrame(existing_data)
    except Exception:
        df_existing = pd.DataFrame()

    # تبدیل داده جدید به دیتافریم
    df_new_row = pd.DataFrame([record_dict])
    
    # ترکیب داده‌های قبلی و جدید
    df_updated = pd.concat([df_existing, df_new_row], ignore_index=True)
    
    # بروزرسانی گوگل شیت
    conn.update(worksheet="AMT_Data", data=df_updated)

# ۴. مدیریت حالت‌های برنامه‌ (Session State)
TIME_LIMIT = 60  # مهلت زمانی برحسب ثانیه

if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

if "is_submitted" not in st.session_state:
    st.session_state.is_submitted = False

# کد شرکت‌کننده
participant_id = st.text_input("کد شرکت‌کننده / نام:", value="ناشناس")

st.markdown("---")
st.subheader("کلمه محرک: **خوشحالی**")

# ۵. محاسبه زمان
elapsed_time = time.time() - st.session_state.start_time
remaining_time = max(0, int(TIME_LIMIT - elapsed_time))

# ۶. جریان اصلی برنامه
if not st.session_state.is_submitted:
    # نمایش تایمر
    st.metric(label="⏱️ زمان باقی‌مانده (ثانیه)", value=remaining_time)
    
    # ورودی متن
    user_response = st.text_area(
        "خاطره خود را وارد کنید:", 
        key="amt_text_input",
        height=150,
        disabled=(remaining_time == 0)
    )

    submit_btn = st.button("ثبت پاسخ", type="primary")

    # شرط ثبت: رسیدن زمان به صفر یا کلیک روی دکمه ثبت
    if remaining_time == 0 or submit_btn:
        st.session_state.is_submitted = True
        
        # برداشت متن تایپ‌شده تا این لحظه
        final_text = st.session_state.get("amt_text_input", "").strip()
        
        # ثبت رکورد
        record = {
            "participant_id": participant_id,
            "response": final_text if final_text else "[بدون پاسخ]",
            "time_taken_sec": round(elapsed_time, 2),
            "submission_type": "خودکار (پایان زمان)" if remaining_time == 0 else "دستی (دکمه ثبت)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # ذخیره در گوگل شیت
        with st.spinner("در حال ثبت اطلاعات..."):
            save_amt_gsheet(record)
            
        if remaining_time == 0:
            st.warning("⏰ زمان ۶۰ ثانیه به پایان رسید! تمامی متونی که تا این لحظه تایپ کرده بودید ذخیره شد.")
        else:
            st.success("✅ پاسخ شما با موفقیت ثبت شد.")
            
        st.rerun()

    # رفرش خودکار صفحه هر ۱ ثانیه برای شمارش معکوس
    if remaining_time > 0 and not submit_btn:
        time.sleep(1)
        st.rerun()

else:
    st.info("پاسخ این مرحله ثبت شده است. با تشکر از همکاری شما!")
    if st.button("شروع مجدد / کلمه بعدی"):
        st.session_state.start_time = time.time()
        st.session_state.is_submitted = False
        st.rerun()