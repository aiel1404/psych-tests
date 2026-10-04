import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# ۱. تنظیم صفحه به صورت wide (تمام‌عرض)
st.set_page_config(page_title="آزمون AMT", page_icon="🧠", layout="wide")

# ۲. تزریق CSS برای راست‌به‌چپ کردن (RTL) و بزرگ‌تر کردن فونت‌ها
st.markdown("""
    <style>
    /* راست‌به‌چپ کردن کل صفحه */
    div[data-testid="stAppViewContainer"] {
        direction: rtl;
        text-align: right;
    }
    /* تنظیم فونت و سایز تیترها */
    h1, h2, h3, p, label {
        text-align: right !important;
        font-family: 'Tahoma', 'Vazir', sans-serif !important;
    }
    /* راست‌به‌چپ کردن ورودی متون */
    textarea, input {
        direction: rtl !important;
        text-align: right !important;
    }
    /* مرکزچین کردن باکس اصلی برای ظاهر بهتر */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("آزمون حافظه سرگذشتی (AMT)")
st.write("لطفاً پس از مشاهده کلمه محرک، خاطره خود را تایپ کنید. شما ۶۰ ثانیه زمان دارید.")

# راه‌اندازی اتصال به گوگل شیت
conn = st.connection("gsheets", type=GSheetsConnection)

def save_amt_gsheet(record_dict):
    try:
        existing_data = conn.read(worksheet="AMT_Data", ttl=0)
        df_existing = pd.DataFrame(existing_data)
    except Exception:
        df_existing = pd.DataFrame()

    df_new_row = pd.DataFrame([record_dict])
    df_updated = pd.concat([df_existing, df_new_row], ignore_index=True)
    conn.update(worksheet="AMT_Data", data=df_updated)

TIME_LIMIT = 60

if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

if "is_submitted" not in st.session_state:
    st.session_state.is_submitted = False

participant_id = st.text_input("کد شرکت‌کننده / نام:", value="ناشناس")

st.markdown("---")
st.subheader("کلمه محرک: **خوشحالی**")

elapsed_time = time.time() - st.session_state.start_time
remaining_time = max(0, int(TIME_LIMIT - elapsed_time))

if not st.session_state.is_submitted:
    st.metric(label="⏱️ زمان باقی‌مانده (ثانیه)", value=remaining_time)
    
    user_response = st.text_area(
        "خاطره خود را وارد کنید:", 
        key="amt_text_input",
        height=180,
        disabled=(remaining_time == 0)
    )

    submit_btn = st.button("ثبت پاسخ", type="primary")

    if remaining_time == 0 or submit_btn:
        st.session_state.is_submitted = True
        
        final_text = st.session_state.get("amt_text_input", "").strip()
        
        record = {
            "participant_id": participant_id,
            "response": final_text if final_text else "[بدون پاسخ]",
            "time_taken_sec": round(elapsed_time, 2),
            "submission_type": "خودکار (پایان زمان)" if remaining_time == 0 else "دستی (دکمه ثبت)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with st.spinner("در حال ثبت اطلاعات..."):
            save_amt_gsheet(record)
            
        if remaining_time == 0:
            st.warning("⏰ زمان ۶۰ ثانیه به پایان رسید! متنی که تا این لحظه تایپ کرده بودید ذخیره شد.")
        else:
            st.success("✅ پاسخ شما با موفقیت ثبت شد.")
            
        st.rerun()

    if remaining_time > 0 and not submit_btn:
        time.sleep(1)
        st.rerun()

else:
    st.info("پاسخ این مرحله ثبت شده است. با تشکر از همکاری شما!")
    if st.button("شروع مجدد / کلمه بعدی"):
        st.session_state.start_time = time.time()
        st.session_state.is_submitted = False
        st.rerun()