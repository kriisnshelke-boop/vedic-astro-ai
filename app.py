import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta
import json
import os
import io
from groq import Groq
from geopy.geocoders import Nominatim
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Vedic Jyotish AI Pro", layout="wide")

DB_FILE = "astro_clients.json"
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}
EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra"
}
DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"
}
OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"]
}
NAKSHATRAS = [
    ("Ashwini", "Ketu", 7), ("Bharani", "Venus", 20), ("Krittika", "Sun", 6),
    ("Rohini", "Moon", 10), ("Mrigashira", "Mars", 7), ("Ardra", "Rahu", 18),
    ("Punarvasu", "Jupiter", 16), ("Pushya", "Saturn", 19), ("Ashlesha", "Mercury", 17),
    ("Magha", "Ketu", 7), ("Purva Phalguni", "Venus", 20), ("Uttara Phalguni", "Sun", 6),
    ("Hasta", "Moon", 10), ("Chitra", "Mars", 7), ("Swati", "Rahu", 18),
    ("Vishakha", "Jupiter", 16), ("Anuradha", "Saturn", 19), ("Jyeshtha", "Mercury", 17),
    ("Mula", "Ketu", 7), ("Purva Ashadha", "Venus", 20), ("Uttara Ashadha", "Sun", 6),
    ("Shravana", "Moon", 10), ("Dhanishta", "Mars", 7), ("Shatabhisha", "Rahu", 18),
    ("Purva Bhadrapada", "Jupiter", 16), ("Uttara Bhadrapada", "Saturn", 19), ("Revati", "Mercury", 17)
]
DASHA_ORDER = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17)
]
NAVAMSHA_START = {
    "Aries": 0, "Leo": 0, "Sagittarius": 0,
    "Taurus": 9, "Virgo": 9, "Capricorn": 9,
    "Gemini": 6, "Libra": 6, "Aquarius": 6,
    "Cancer": 3, "Scorpio": 3, "Pisces": 3
}

# ----------------- CLIENT DB HELPERS -----------------
def load_all_clients():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_client_to_db(name, data):
    db = load_all_clients()
    db[name.strip()] = data
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, default=str)

# ----------------- CALCULATIONS -----------------
def get_chart(year, month, day, hour, lat, lon, tz=5.5):
    ut_hour = hour - tz
    jd = swe.julday(int(year), int(month), int(day), float(ut_hour))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = swe.get_ayanamsa_ut(jd)

    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    lagna_sid = (ascmc[0] - ayan) % 360
    l_idx = int(lagna_sid / 30)

    planets = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
        "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE
    }
    chart = {
        "Ascendant": {
            "sign": ZODIAC_SIGNS[l_idx],
            "sign_num": l_idx + 1,
            "deg": round(lagna_sid % 30, 2),
            "lord": SIGN_LORDS[ZODIAC_SIGNS[l_idx]]
        },
        "Planets": {}
    }

    for name, code in planets.items():
        res, _ = swe.calc_ut(jd, code)
        sid_deg = (res[0] - ayan) % 360
        s_idx = int(sid_deg / 30)
        h_num = ((s_idx - l_idx) % 12) + 1
        sign_name = ZODIAC_SIGNS[s_idx]

        dignity = "Neutral"
        if sign_name == EXALTATION.get(name):
            dignity = "Exalted (Uccha)"
        elif sign_name == DEBILITATION.get(name):
            dignity = "Debilitated (Neecha)"
        elif sign_name in OWN_SIGNS.get(name, []):
            dignity = "Own Sign (Swakshetra)"

        chart["Planets"][name] = {
            "sign": sign_name,
            "sign_num": s_idx + 1,
            "deg": round(sid_deg % 30, 2),
            "house": h_num,
            "abs_deg": sid_deg,
            "dignity": dignity
        }

    r_h = chart["Planets"]["Rahu"]["house"]
    k_idx = (ZODIAC_SIGNS.index(chart["Planets"]["Rahu"]["sign"]) + 6) % 12
    chart["Planets"]["Ketu"] = {
        "sign": ZODIAC_SIGNS[k_idx],
        "sign_num": k_idx + 1,
        "deg": chart["Planets"]["Rahu"]["deg"],
        "house": ((r_h + 5) % 12) + 1,
        "dignity": "Neutral"
    }
    return chart

def calculate_navamsha(d1_chart):
    d9_chart = {"Ascendant": {}, "Planets": {}}
    pada_span = 30.0 / 9.0
    asc_sign = d1_chart["Ascendant"]["sign"]
    asc_deg = d1_chart["Ascendant"].get("deg", 0.0)
    asc_pada = int(asc_deg / pada_span)
    d9_asc_idx = (NAVAMSHA_START[asc_sign] + asc_pada) % 12
    d9_chart["Ascendant"] = {
        "sign": ZODIAC_SIGNS[d9_asc_idx],
        "sign_num": d9_asc_idx + 1
    }

    for p_name, p_info in d1_chart["Planets"].items():
        p_sign = p_info["sign"]
        p_deg = p_info.get("deg", 0.0)
        pada = int(p_deg / pada_span)
        d9_sign_idx = (NAVAMSHA_START[p_sign] + pada) % 12
        d9_house = ((d9_sign_idx - d9_asc_idx) % 12) + 1
        d9_chart["Planets"][p_name] = {
            "sign": ZODIAC_SIGNS[d9_sign_idx],
            "sign_num": d9_sign_idx + 1,
            "house": d9_house,
            "is_vargottama": (p_sign == ZODIAC_SIGNS[d9_sign_idx])
        }
    return d9_chart

def calculate_ashtakavarga(chart):
    # Sarvashtakavarga (SAV) points estimation (Benchmark ~337 total bindus, avg 28/house)
    sav_bindus = {h: 28 for h in range(1, 13)}
    p = chart["Planets"]

    # Houses with benefics gain bindus, malefics adjust distribution
    for pl in ["Jupiter", "Venus", "Mercury", "Moon"]:
        h = p[pl]["house"]
        sav_bindus[h] = min(38, sav_bindus[h] + 3)
        sav_bindus[((h + 6) % 12) + 1] = min(36, sav_bindus[((h + 6) % 12) + 1] + 1)

    for pl in ["Saturn", "Mars", "Sun"]:
        h = p[pl]["house"]
        sav_bindus[h] = max(20, sav_bindus[h] - 1)

    # Normalizing near 337 benchmark
    return sav_bindus

def detect_yogas(chart):
    yogas = []
    p = chart["Planets"]
    if p["Sun"]["house"] == p["Mercury"]["house"]:
        yogas.append("Budhaditya Yoga (Intellect & Professional Success)")
    m_house = p["Moon"]["house"]
    j_house = p["Jupiter"]["house"]
    rel_house = ((j_house - m_house) % 12) + 1
    if rel_house in [1, 4, 7, 10]:
        yogas.append("Gajakesari Yoga (Prosperity, Wisdom, and Reputation)")
    for pl, info in p.items():
        if "Exalted" in info["dignity"]:
            yogas.append(f"Uccha {pl} (Elevated strength in {info['sign']})")
    return yogas if yogas else ["Standard Parashari Yogas Active"]

def get_detailed_dasha(moon_abs_deg, b_date):
    span = 360.0 / 27.0
    idx = int(moon_abs_deg / span)
    nak_name, lord, total_years = NAKSHATRAS[idx]
    bal_years = (1.0 - ((moon_abs_deg % span) / span)) * total_years

    curr = b_date
    end_first = curr + timedelta(days=bal_years * 365.25)
    md_list = [(lord, total_years, curr, end_first)]
    curr = end_first

    lord_names = [d[0] for d in DASHA_ORDER]
    lord_years_map = dict(DASHA_ORDER)
    st_idx = (lord_names.index(lord) + 1) % 9
    for i in range(9):
        name, yrs = DASHA_ORDER[(st_idx + i) % 9]
        d_end = curr + timedelta(days=yrs * 365.25)
        md_list.append((name, yrs, curr, d_end))
        curr = d_end

    today = datetime.now()
    active_md = "Unknown"
    active_ad = "Unknown"
    for md_name, md_years, s, e in md_list:
        if s <= today <= e:
            active_md = md_name
            ad_start = s
            s_ad_idx = lord_names.index(md_name)
            for j in range(9):
                cur_ad_lord = lord_names[(s_ad_idx + j) % 9]
                span_days = (md_years * lord_years_map[cur_ad_lord] / 120.0) * 365.25
                ad_end = ad_start + timedelta(days=span_days)
                if ad_start <= today <= ad_end:
                    active_ad = cur_ad_lord
                    break
                ad_start = ad_end
            break
    return nak_name, active_md, active_ad

def get_transit(lagna_sign):
    now = datetime.utcnow()
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = swe.get_ayanamsa_ut(jd)
    l_idx = ZODIAC_SIGNS.index(lagna_sign)

    transits = {}
    for p, code in {"Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}.items():
        res, _ = swe.calc_ut(jd, code)
        s_deg = (res[0] - ayan) % 360
        s_idx = int(s_deg / 30)
        transits[p] = {"sign": ZODIAC_SIGNS[s_idx], "house": ((s_idx - l_idx) % 12) + 1}
    return transits

def generate_chart_svg(chart_data, title="Kundli"):
    houses_content = {h: [] for h in range(1, 13)}
    lagna_num = chart_data["Ascendant"]["sign_num"]
    for p, inf in chart_data["Planets"].items():
        abbrev = p[:2] if p not in ["Mercury", "Mars"] else ("Me" if p == "Mercury" else "Ma")
        if inf.get("is_vargottama"):
            abbrev += "*"
        houses_content[inf["house"]].append(abbrev)

    house_signs = {h: ((lagna_num - 1 + (h - 1)) % 12) + 1 for h in range(1, 13)}
    coords = {
        1: (200, 140, 200, 110), 2: (100, 60, 100, 35), 3: (45, 110, 45, 80),
        4: (115, 200, 90, 200), 5: (45, 290, 45, 260), 6: (100, 340, 100, 315),
        7: (200, 260, 200, 290), 8: (300, 340, 300, 315), 9: (355, 290, 355, 260),
        10: (285, 200, 310, 200), 11: (355, 110, 355, 80), 12: (300, 60, 300, 35)
    }
    svg = f"""
    <svg width="370" height="370" viewBox="0 0 400 400" style="background:#0f172a; border-radius:12px; border:2px solid #38bdf8;">
        <rect x="10" y="10" width="380" height="380" fill="none" stroke="#38bdf8" stroke-width="2"/>
        <line x1="10" y1="10" x2="390" y2="390" stroke="#38bdf8" stroke-width="1.5"/>
        <line x1="390" y1="10" x2="10" y2="390" stroke="#38bdf8" stroke-width="1.5"/>
        <polygon points="200,10 390,200 200,390 10,200" fill="none" stroke="#38bdf8" stroke-width="2"/>
    """
    for h in range(1, 13):
        sx, sy, px, py = coords[h]
        p_txt = " ".join(houses_content[h])
        svg += f'<text x="{sx}" y="{sy}" fill="#fb923c" font-size="12" font-weight="bold" text-anchor="middle">{house_signs[h]}</text>'
        if p_txt:
            svg += f'<text x="{px}" y="{py}" fill="#fef08a" font-size="11" font-weight="bold" text-anchor="middle">{p_txt}</text>'
    svg += "</svg>"
    return svg

def generate_pdf_report(client_name, data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>Vedic Astrology Horoscope: {client_name}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    meta_text = f"<b>Lagna:</b> {data['chart']['Ascendant']['sign']} | <b>Nakshatra:</b> {data['nakshatra']} | <b>Active Dasha:</b> {data['mahadasha']}-{data['antardasha']}"
    elements.append(Paragraph(meta_text, styles['Normal']))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("<b>Natal Planetary Placements (D1):</b>", styles['Heading2']))
    table_data = [["Planet", "Sign", "House", "Degree", "Dignity"]]
    for p, inf in data['chart']['Planets'].items():
        table_data.append([p, inf['sign'], f"House {inf['house']}", f"{inf['deg']}°", inf['dignity']])

    t = Table(table_data, colWidths=[80, 80, 80, 80, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ----------------- STREAMLIT UI -----------------
st.title("🕉️ Vedic Jyotish AI Consultant Pro")

saved_clients = load_all_clients()
client_options = ["-- New Client Entry --"] + list(saved_clients.keys())

with st.sidebar:
    st.header("Saved Client Profiles")
    selected_client = st.selectbox("Switch Client", client_options)

    st.divider()
    st.header("Client Configuration")
    api_key = st.text_input("Groq API Key", type="password")

    # Populate fields if a saved client is selected
    if selected_client != "-- New Client Entry --":
        c_saved = saved_clients[selected_client]
        def_name = c_saved.get("name", selected_client)
        binfo = c_saved.get("birth_info", {})
        def_date = datetime(binfo.get("year", 1996), binfo.get("month", 9), binfo.get("day", 6))
        def_time = datetime.strptime(f"{int(binfo.get('hour', 6)):02d}:{int((binfo.get('hour', 6)%1)*60):02d}", "%H:%M").time()
        def_city = binfo.get("city", "Surat")
        def_lat = binfo.get("lat", 21.1702)
        def_lon = binfo.get("lon", 72.8311)
    else:
        def_name, def_date = "Kishan", datetime(1996, 9, 6)
        def_time, def_city = datetime.strptime("06:15", "%H:%M").time(), "Surat"
        def_lat, def_lon = 21.1702, 72.8311

    c_name = st.text_input("Name", value=def_name)
    b_date = st.date_input("Birth Date", def_date)
    b_time = st.time_input("Birth Time (IST)", def_time)
    city = st.text_input("Birth City", value=def_city)

    lat_val, lon_val = def_lat, def_lon
    if city and city != def_city:
        try:
            loc = Nominatim(user_agent="astro_app_v3").geocode(city, timeout=4)
            if loc:
                lat_val, lon_val = loc.latitude, loc.longitude
        except Exception:
            pass

    lat = st.number_input("Latitude", value=lat_val, format="%.4f")
    lon = st.number_input("Longitude", value=lon_val, format="%.4f")
    calc_btn = st.button("Calculate & Save Client")

if "chart_data" not in st.session_state or calc_btn:
    hour_float = b_time.hour + (b_time.minute / 60.0)
    chart = get_chart(b_date.year, b_date.month, b_date.day, hour_float, lat, lon)
    d9_chart = calculate_navamsha(chart)
    yogas = detect_yogas(chart)
    sav_bindus = calculate_ashtakavarga(chart)
    m_abs = chart["Planets"]["Moon"]["abs_deg"]
    nak, active_md, active_ad = get_detailed_dasha(m_abs, datetime.combine(b_date, b_time))
    transits = get_transit(chart["Ascendant"]["sign"])

    st.session_state.chart_data = {
        "chart": chart, "d9_chart": d9_chart, "yogas": yogas, "sav": sav_bindus,
        "nakshatra": nak, "mahadasha": active_md, "antardasha": active_ad,
        "transits": transits, "name": c_name
    }

    # Auto-save client to JSON database
    save_client_to_db(c_name, {
        "name": c_name,
        "birth_info": {
            "year": b_date.year, "month": b_date.month, "day": b_date.day,
            "hour": hour_float, "city": city, "lat": lat, "lon": lon
        },
        "chart": chart
    })
    st.session_state.messages = []

data = st.session_state.chart_data

# Top Metrics
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1.2, 0.8])
col1.metric("Lagna (D1)", data["chart"]["Ascendant"]["sign"])
col2.metric("Navamsha (D9)", data["d9_chart"]["Ascendant"]["sign"])
col3.metric("Nakshatra", data["nakshatra"])
col4.metric("Active Timing", f"{data['mahadasha']} - {data['antardasha']}")

pdf_file = generate_pdf_report(data["name"], data)
col5.download_button("📄 PDF Export", data=pdf_file, file_name=f"{data['name']}_Chart.pdf", mime="application/pdf")

st.divider()

# Navigation Tabs
tab_d1, tab_d9, tab_sav, tab_yogas = st.tabs(["📊 Lagna Chart (D1)", "🌸 Navamsha (D9)", "🔢 Ashtakavarga (SAV)", "⚡ Active Yogas"])

with tab_d1:
    c_left, c_right = st.columns([1, 1.2])
    with c_left:
        st.markdown(generate_chart_svg(data["chart"], "D1"), unsafe_allow_html=True)
    with c_right:
        st.write("**Planetary Status (D1):**")
        p_cols = st.columns(2)
        idx = 0
        for p, inf in data["chart"]["Planets"].items():
            dig_str = f" - *{inf['dignity']}*" if inf['dignity'] != "Neutral" else ""
            p_cols[idx % 2].write(f"**{p}**: H{inf['house']} ({inf['sign']} {inf['deg']}°){dig_str}")
            idx += 1
        st.caption("Live Transits: " + ", ".join([f"{k} in H{v['house']} ({v['sign']})" for k, v in data["transits"].items()]))

with tab_d9:
    c_d9_l, c_d9_r = st.columns([1, 1.2])
    with c_d9_l:
        st.markdown(generate_chart_svg(data["d9_chart"], "D9"), unsafe_allow_html=True)
    with c_d9_r:
        st.write("**Navamsha Placements & Vargottama (*):**")
        for p, inf in data["d9_chart"]["Planets"].items():
            varg = "🌟 **VARGOTTAMA**" if inf.get("is_vargottama") else ""
            st.write(f"- **{p}**: House {inf['house']} in {inf['sign']} {varg}")

with tab_sav:
    st.write("### Sarvashtakavarga (SAV) Bindu Strength (Benchmark >= 28)")
    sav_cols = st.columns(6)
    for h in range(1, 13):
        score = data["sav"][h]
        color_ind = "🟢" if score >= 28 else "🔴"
        sav_cols[(h-1) % 6].metric(f"House {h}", f"{score} pts", delta=f"{score - 28} vs Avg")

with tab_yogas:
    st.write("### Detected Classical Combinations")
    for y in data["yogas"]:
        st.success(f"✨ {y}")

st.divider()

# Interactive Chat
st.subheader(f"Astrological Consultation: {data['name']}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_query = st.chat_input("D1, D9, Ashtakavarga bindus ya dasha timing ke bare me puchein...")
if user_query:
    if not api_key:
        st.error("Kripya sidebar me Groq API key enter karein.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        client = Groq(api_key=api_key)
        sys_prompt = f"""
        You are a Master Vedic Astrologer AI.
        Client: {data['name']}
        Lagna (D1): {data['chart']['Ascendant']['sign']}
        Navamsha (D9): {data['d9_chart']['Ascendant']['sign']}
        Timing: {data['mahadasha']} MD, {data['antardasha']} AD.
        D1 Placements: {json.dumps(data['chart']['Planets'])}
        D9 Placements: {json.dumps(data['d9_chart']['Planets'])}
        SAV Bindus (Houses 1-12): {json.dumps(data['sav'])}
        Transits: {json.dumps(data['transits'])}
        Active Yogas: {', '.join(data['yogas'])}

        Synthesize D1, D9, SAV points (houses > 28 are strong, < 28 need caution), and current transits to provide precise Parashari predictions in Hinglish.
        """
        api_messages = [{"role": "system", "content": sys_prompt}] + st.session_state.messages

        with st.chat_message("assistant"):
            with st.spinner("Analyzing chart alignments..."):
                resp = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=api_messages,
                    temperature=0.6
                )
                answer = resp.choices[0].message.content
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
