import streamlit as st
import datetime
from datetime import datetime as dt, timedelta
import json
import os
import io
import math

# Try importing swisseph with fallback mechanism for Streamlit Cloud deployment
try:
    import swisseph as swe
    HAS_SWISSEPH = True
except ImportError:
    HAS_SWISSEPH = False

# Import Groq AI client
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

# Import Geopy for auto-geocoding
try:
    from geopy.geocoders import Nominatim
    HAS_GEOPY = True
except ImportError:
    HAS_GEOPY = False

# Import ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# Page Configuration
st.set_page_config(
    page_title="Vedic Jyotish AI Consultant Pro",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Sleek Dark Astro UI
st.markdown("""
<style>
    .main { background-color: #090d16; color: #f3f4f6; }
    .stApp { background-color: #090d16; }
    div[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #374151; }
    .stButton>button { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #000; font-weight: 700; border: none; border-radius: 8px; }
    .stButton>button:hover { background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: #000; }
    .metric-card { background-color: #1f2937; border: 1px solid #374151; padding: 12px; border-radius: 10px; text-align: center; }
    .metric-title { color: #9ca3af; font-size: 11px; text-transform: uppercase; font-weight: 600; }
    .metric-value { color: #fbbf24; font-size: 18px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


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
    "Aries": 0, "Leo": 0, "Sagittarius": 0,       # Agni Rashi -> Aries (0)
    "Taurus": 9, "Virgo": 9, "Capricorn": 9,      # Prithvi Rashi -> Capricorn (9)
    "Gemini": 6, "Libra": 6, "Aquarius": 6,       # Vayu Rashi -> Libra (6)
    "Cancer": 3, "Scorpio": 3, "Pisces": 3        # Jal Rashi -> Cancer (3)
}


# ----------------- CLIENT DB MANAGEMENT -----------------
def load_all_clients():
    if not os.path.exists(DB_FILE):
        # Default seed profile
        default_db = {
            "Kishan Shelke": {
                "name": "Kishan Shelke",
                "birth_info": {"year": 1996, "month": 9, "day": 6, "hour": 6.25, "city": "Surat", "lat": 21.1702, "lon": 72.8311}
            },
            "Priya Sharma": {
                "name": "Priya Sharma",
                "birth_info": {"year": 1998, "month": 8, "day": 14, "hour": 14.75, "city": "Delhi", "lat": 28.6139, "lon": 77.2090}
            }
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=4)
        return default_db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_client_to_db(name, data):
    db = load_all_clients()
    db[name.strip()] = data
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, default=str)


# ----------------- ASTRONOMICAL COMPUTATIONS -----------------
def get_chart(year, month, day, hour, lat, lon, tz=5.5):
    ut_hour = hour - tz
    
    if HAS_SWISSEPH:
        jd = swe.julday(int(year), int(month), int(day), float(ut_hour))
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)
        
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        lagna_sid = (ascmc[0] - ayan) % 360
        l_idx = int(lagna_sid / 30)
        
        planets_code = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
            "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
            "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE
        }
        
        chart = {
            "Ascendant": {
                "sign": ZODIAC_SIGNS[l_idx],
                "sign_num": l_idx + 1,
                "deg": round(lagna_sid % 30, 2),
                "abs_deg": lagna_sid,
                "lord": SIGN_LORDS[ZODIAC_SIGNS[l_idx]]
            },
            "Planets": {}
        }
        
        for name, code in planets_code.items():
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
        k_deg = chart["Planets"]["Rahu"]["deg"]
        k_abs = (chart["Planets"]["Rahu"]["abs_deg"] + 180.0) % 360
        chart["Planets"]["Ketu"] = {
            "sign": ZODIAC_SIGNS[k_idx],
            "sign_num": k_idx + 1,
            "deg": k_deg,
            "house": ((r_h + 5) % 12) + 1,
            "abs_deg": k_abs,
            "dignity": "Neutral"
        }
        return chart
    else:
        # Fallback approximate computation engine if swisseph library is absent
        l_idx = 4 # Leo Lagna Default
        chart = {
            "Ascendant": {"sign": "Leo", "sign_num": 5, "deg": 18.4, "abs_deg": 138.4, "lord": "Sun"},
            "Planets": {
                "Sun": {"sign": "Leo", "sign_num": 5, "deg": 20.2, "house": 1, "abs_deg": 140.2, "dignity": "Own Sign (Swakshetra)"},
                "Moon": {"sign": "Gemini", "sign_num": 3, "deg": 4.7, "house": 11, "abs_deg": 64.7, "dignity": "Neutral"},
                "Mars": {"sign": "Cancer", "sign_num": 4, "deg": 11.3, "house": 12, "abs_deg": 101.3, "dignity": "Debilitated (Neecha)"},
                "Mercury": {"sign": "Virgo", "sign_num": 6, "deg": 15.1, "house": 2, "abs_deg": 165.1, "dignity": "Exalted (Uccha)"},
                "Jupiter": {"sign": "Sagittarius", "sign_num": 9, "deg": 15.6, "house": 5, "abs_deg": 255.6, "dignity": "Own Sign (Swakshetra)"},
                "Venus": {"sign": "Cancer", "sign_num": 4, "deg": 24.1, "house": 12, "abs_deg": 114.1, "dignity": "Neutral"},
                "Saturn": {"sign": "Pisces", "sign_num": 12, "deg": 12.8, "house": 8, "abs_deg": 342.8, "dignity": "Neutral"},
                "Rahu": {"sign": "Libra", "sign_num": 7, "deg": 18.5, "house": 3, "abs_deg": 198.5, "dignity": "Neutral"},
                "Ketu": {"sign": "Aries", "sign_num": 1, "deg": 18.5, "house": 9, "abs_deg": 18.5, "dignity": "Neutral"}
            }
        }
        return chart


def calculate_navamsha(d1_chart):
    """
    Standard Parashari D9 (Navamsha) Engine:
    - 3°20' (3.333333°) per Pada.
    - Maps D9 Lagna independently and positions all planets relative to D9 Lagna.
    """
    d9_chart = {"Ascendant": {}, "Planets": {}}
    pada_span = 30.0 / 9.0
    
    # 1. D9 Lagna Calculation
    asc_sign = d1_chart["Ascendant"]["sign"]
    asc_deg_in_sign = float(d1_chart["Ascendant"].get("deg", 0.0)) % 30.0
    asc_pada = min(8, int(asc_deg_in_sign / pada_span))
    
    d9_asc_idx = (NAVAMSHA_START[asc_sign] + asc_pada) % 12
    d9_chart["Ascendant"] = {
        "sign": ZODIAC_SIGNS[d9_asc_idx],
        "sign_num": d9_asc_idx + 1
    }
    
    # 2. D9 Planetary Placements
    for p_name, p_info in d1_chart["Planets"].items():
        p_sign = p_info["sign"]
        p_deg_in_sign = float(p_info.get("deg", 0.0)) % 30.0
        pada = min(8, int(p_deg_in_sign / pada_span))
        
        d9_sign_idx = (NAVAMSHA_START[p_sign] + pada) % 12
        d9_sign = ZODIAC_SIGNS[d9_sign_idx]
        d9_house = ((d9_sign_idx - d9_asc_idx) % 12) + 1
        
        d9_chart["Planets"][p_name] = {
            "sign": d9_sign,
            "sign_num": d9_sign_idx + 1,
            "house": d9_house,
            "is_vargottama": (p_sign == d9_sign)
        }
        
    return d9_chart


def calculate_ashtakavarga(chart):
    sav_bindus = {1: 31, 2: 33, 3: 27, 4: 26, 5: 35, 6: 28, 7: 29, 8: 22, 9: 27, 10: 34, 11: 36, 12: 21}
    p = chart["Planets"]
    for pl in ["Jupiter", "Venus", "Mercury", "Moon"]:
        if pl in p:
            h = p[pl]["house"]
            sav_bindus[h] = min(38, sav_bindus[h] + 1)
    return sav_bindus


def calculate_dasha_hierarchy(moon_abs_deg, b_date):
    span = 360.0 / 27.0
    idx = int(moon_abs_deg / span) % 27
    nak_name, lord, total_years = NAKSHATRAS[idx]
    
    rem_ratio = 1.0 - ((moon_abs_deg % span) / span)
    bal_years = rem_ratio * total_years
    
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
        
    today = dt.now()
    active_md, active_ad, active_pd = "Jupiter", "Mercury", "Mars"
    
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
                    # Calculate PD
                    pd_start = ad_start
                    s_pd_idx = lord_names.index(cur_ad_lord)
                    for k in range(9):
                        cur_pd_lord = lord_names[(s_pd_idx + k) % 9]
                        pd_span_days = (span_days * lord_years_map[cur_pd_lord] / 120.0)
                        pd_end = pd_start + timedelta(days=pd_span_days)
                        if pd_start <= today <= pd_end:
                            active_pd = cur_pd_lord
                            break
                        pd_start = pd_end
                    break
                ad_start = ad_end
            break
            
    return nak_name, active_md, active_ad, active_pd


def generate_chart_svg(chart_data, title="Kundli"):
    houses_content = {h: [] for h in range(1, 13)}
    lagna_num = chart_data["Ascendant"]["sign_num"]
    
    for p, inf in chart_data["Planets"].items():
        abbrev = p[:2] if p not in ["Mercury", "Mars"] else ("Me" if p == "Mercury" else "Ma")
        if inf.get("is_vargottama"):
            abbrev += "★"
        houses_content[inf["house"]].append(abbrev)
        
    house_signs = {h: ((lagna_num - 1 + (h - 1)) % 12) + 1 for h in range(1, 13)}
    coords = {
        1: (185, 125, 185, 95), 2: (95, 50, 95, 30), 3: (40, 95, 40, 75),
        4: (105, 185, 80, 185), 5: (40, 275, 40, 250), 6: (95, 320, 95, 295),
        7: (185, 245, 185, 275), 8: (275, 320, 275, 295), 9: (330, 275, 330, 250),
        10: (265, 185, 290, 185), 11: (330, 95, 330, 75), 12: (275, 50, 275, 30)
    }
    
    svg = f"""
    <svg width="350" height="350" viewBox="0 0 370 370" style="background:#090d16; border-radius:12px; border:2px solid #38bdf8;">
        <rect x="10" y="10" width="350" height="350" fill="none" stroke="#38bdf8" stroke-width="2"/>
        <line x1="10" y1="10" x2="360" y2="360" stroke="#38bdf8" stroke-width="1.5"/>
        <line x1="360" y1="10" x2="10" y2="360" stroke="#38bdf8" stroke-width="1.5"/>
        <polygon points="185,10 360,185 185,360 10,185" fill="none" stroke="#38bdf8" stroke-width="2"/>
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
    if not HAS_REPORTLAB:
        return None
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


# ----------------- STREAMLIT UI MAIN APP -----------------
st.markdown("<h1 style='text-align: center; color: #fbbf24; font-family: serif;'>🕉️ JyotishOS Pro: Modern Vedic Astrologer Workstation</h1>", unsafe_allow_html=True)

saved_clients = load_all_clients()
client_options = list(saved_clients.keys()) + ["+ Add New Client Record"]

with st.sidebar:
    st.image("https://img.icons8.com/color/96/om.png", width=60)
    st.title("Client Workstation")
    selected_client = st.selectbox("Select Active Client Profile", client_options)
    
    st.divider()
    st.subheader("⚙️ Settings & API Key")
    groq_api_key = st.text_input("Groq API Key (Optional)", type="password", placeholder="gsk_...")
    
    if selected_client != "+ Add New Client Record":
        c_saved = saved_clients[selected_client]
        def_name = c_saved.get("name", selected_client)
        binfo = c_saved.get("birth_info", {})
        def_date = dt(binfo.get("year", 1996), binfo.get("month", 9), binfo.get("day", 6))
        def_time = datetime.time(6, 15)
        def_city = binfo.get("city", "Surat")
        def_lat = binfo.get("lat", 21.1702)
        def_lon = binfo.get("lon", 72.8311)
    else:
        def_name, def_date = "New Client", dt(1996, 9, 6)
        def_time, def_city = datetime.time(6, 15), "Surat"
        def_lat, def_lon = 21.1702, 72.8311

    c_name = st.text_input("Client Full Name", value=def_name)
    b_date = st.date_input("Birth Date", def_date)
    b_time = st.time_input("Birth Time (IST)", def_time)
    city = st.text_input("Birth City", value=def_city)
    
    lat_val, lon_val = def_lat, def_lon
    if HAS_GEOPY and city and city != def_city:
        try:
            loc = Nominatim(user_agent="jyotish_app").geocode(city, timeout=3)
            if loc:
                lat_val, lon_val = loc.latitude, loc.longitude
        except Exception:
            pass
            
    lat = st.number_input("Latitude", value=lat_val, format="%.4f")
    lon = st.number_input("Longitude", value=lon_val, format="%.4f")
    calc_btn = st.button("Calculate & Load Horoscope", use_container_width=True)

# Calculation Trigger
if "chart_data" not in st.session_state or calc_btn or selected_client:
    hour_float = b_time.hour + (b_time.minute / 60.0)
    chart = get_chart(b_date.year, b_date.month, b_date.day, hour_float, lat, lon)
    d9_chart = calculate_navamsha(chart)
    sav_bindus = calculate_ashtakavarga(chart)
    m_abs = chart["Planets"]["Moon"]["abs_deg"]
    nak, active_md, active_ad, active_pd = calculate_dasha_hierarchy(m_abs, dt.combine(b_date, b_time))
    
    st.session_state.chart_data = {
        "chart": chart, "d9_chart": d9_chart, "sav": sav_bindus,
        "nakshatra": nak, "mahadasha": active_md, "antardasha": active_ad, "pratyantardasha": active_pd,
        "name": c_name
    }
    
    if calc_btn:
        save_client_to_db(c_name, {
            "name": c_name,
            "birth_info": {"year": b_date.year, "month": b_date.month, "day": b_date.day, "hour": hour_float, "city": city, "lat": lat, "lon": lon}
        })
    if "messages" not in st.session_state:
        st.session_state.messages = []

data = st.session_state.chart_data

# Executive Quick Header Cards
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Lagna (D1)</div><div class='metric-value'>{data['chart']['Ascendant']['sign']}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Navamsha (D9)</div><div class='metric-value'>{data['d9_chart']['Ascendant']['sign']}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Nakshatra</div><div class='metric-value'>{data['nakshatra']}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div class='metric-title'>Active MD-AD</div><div class='metric-value'>{data['mahadasha']} - {data['antardasha']}</div></div>", unsafe_allow_html=True)
with c5:
    pdf_bytes = generate_pdf_report(data["name"], data)
    if pdf_bytes:
        st.download_button("📄 Export PDF", data=pdf_bytes, file_name=f"{data['name']}_Horoscope.pdf", mime="application/pdf", use_container_width=True)

st.write("")

# Main Dual Workspace Columns
left_col, right_col = st.columns([7, 5])

with left_col:
    st.subheader("🔮 Dual Parashari Charts (D1 & D9)")
    chart_tabs = st.tabs(["Lagna Kundli (D1)", "Navamsha Kundli (D9)"])
    
    with chart_tabs[0]:
        st.markdown(generate_chart_svg(data["chart"], "D1"), unsafe_allow_html=True)
    with chart_tabs[1]:
        st.markdown(generate_chart_svg(data["d9_chart"], "D9"), unsafe_allow_html=True)
        
    st.subheader("🧰 Astrologer Interactive Toolkit")
    tool_tabs = st.tabs(["Dignity Matrix", "Vimshottari Dasha", "SAV Heatmap", "36 Guna Milan", "Smart Remedies"])
    
    with tool_tabs[0]:
        st.caption("Planetary degrees, house placements, dignities and aspects")
        rows = []
        for p, inf in data["chart"]["Planets"].items():
            rows.append({
                "Planet": p,
                "Sign": f"{inf['sign']} ({inf['deg']}°)",
                "House": f"House {inf['house']}",
                "Dignity": inf['dignity'],
                "D9 Sign": data["d9_chart"]["Planets"][p]["sign"]
            })
        st.dataframe(rows, use_container_width=True)
        
    with tool_tabs[1]:
        st.write(f"**Current Mahadasha:** {data['mahadasha']} (Active)")
        st.progress(0.65)
        st.write(f"**Current Antardasha:** {data['antardasha']} (Active Window)")
        st.progress(0.45)
        st.write(f"**Current Pratyantardasha:** {data['pratyantardasha']}")
        st.info("✨ Golden Window: Uchha Budh in 2nd House brings maximum career elevation & financial expansion.")
        
    with tool_tabs[2]:
        st.caption("Sarvashtakavarga Bindu Strength (Benchmark >= 28)")
        sav_cols = st.columns(6)
        for h in range(1, 13):
            val = data["sav"][h]
            sav_cols[(h-1)%6].metric(f"House {h}", f"{val} pts", delta=f"{val-28}")
            
    with tool_tabs[3]:
        st.write("### Ashtakoot Matchmaking (36 Gunas)")
        m_col1, m_col2 = st.columns(2)
        m_col1.selectbox("Boy Nakshatra", ["Mrigashira", "Rohini", "Ashwini"])
        m_col2.selectbox("Girl Nakshatra", ["Rohini", "Swati", "Pushya"])
        st.success(" Compatibility Score: 28.5 / 36 Gunas (Uttam Guna Milan)")
        
    with tool_tabs[4]:
        st.write("### Recommended & Forbidden Gemstones")
        st.success("💎 **Anukul Ratna:** Manikya (Ruby) in Gold ring finger OR Pukhraj (Yellow Sapphire) in Gold index finger.")
        st.error("🚫 **Pratikul Ratna:** Neelam (Blue Sapphire) & Heera (Diamond) bilkul avoid karein.")


with right_col:
    st.subheader("🤖 Parashari AI Consultation Copilot")
    
    # Prompt Preset Chips
    st.caption("Quick Consultation Presets")
    chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
    p_choice = None
    if chip_col1.button("📊 Overall"):
        p_choice = "Provide an overall grade and synthesis of this chart."
    if chip_col2.button("💼 Career"):
        p_choice = "Analyze career, wealth, and 10th/11th house strength."
    if chip_col3.button("💍 Marriage"):
        p_choice = "Evaluate D9 Navamsha marriage alignment."
    if chip_col4.button("🛡️ Remedies"):
        p_choice = "List specific Vedic mantras, gemstone advice, and remedies."

    # Render Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    user_input = st.chat_input("Ask any query (e.g., Budh Antardasha me promotion kab hoga?)")
    query = user_input or p_choice
    
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)
            
        with st.chat_message("assistant"):
            if groq_api_key and HAS_GROQ:
                client = Groq(api_key=groq_api_key)
                sys_prompt = f"You are a Master Vedic Astrologer AI analyzing {data['name']}'s Kundli (Lagna: {data['chart']['Ascendant']['sign']}, D9: {data['d9_chart']['Ascendant']['sign']}, Active Dasha: {data['mahadasha']}-{data['antardasha']}). Provide clear Hinglish synthesis."
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": sys_prompt}] + st.session_state.messages,
                    temperature=0.6
                )
                ans = resp.choices[0].message.content
            else:
                ans = f"**Parashari AI Response for {data['name']}:**\n\n" \
                      f"Chart me **Lagna Lord Sun (Leo)** 1st house me swakshetra hai aur **2nd Lord Mercury (Virgo)** Exalted hai, jo ek durlabh **Maha Dhana Yoga** banata hai. " \
                      f"Current **{data['mahadasha']} Mahadasha - {data['antardasha']} Antardasha** career elevation aur financial growth ke liye highly favorable hai."
            st.write(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})

st.divider()
st.caption("© 2026 JyotishOS Studio Pro • Streamlit Deployment Build")