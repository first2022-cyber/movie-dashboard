
import streamlit as st
import requests
import urllib.parse
import streamlit.components.v1 as components

# ----------------------------------
# 기본 설정
# ----------------------------------
st.set_page_config(
    page_title="PubChem 물질 탐구",
    page_icon="⚗️",
    layout="wide"
)

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
TIMEOUT = 20

# ----------------------------------
# PubChem API 함수
# ----------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def search_compound(name):
    """물질 이름으로 CID 검색"""
    encoded_name = urllib.parse.quote(name, safe="")
    url = f"{BASE_URL}/compound/name/{encoded_name}/cids/JSON"

    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    cids = data.get("IdentifierList", {}).get("CID", [])
    if not cids:
        return None

    return cids[0]


@st.cache_data(ttl=3600, show_spinner=False)
def get_properties(cid):
    """분자식과 분자량 조회"""
    url = (
        f"{BASE_URL}/compound/cid/{cid}"
        "/property/MolecularFormula,MolecularWeight/JSON"
    )

    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    properties = data.get("PropertyTable", {}).get("Properties", [])
    return properties[0] if properties else None


@st.cache_data(ttl=3600, show_spinner=False)
def get_2d_image(cid):
    """2D 구조 이미지 가져오기"""
    url = f"{BASE_URL}/compound/cid/{cid}/PNG"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.content


@st.cache_data(ttl=3600, show_spinner=False)
def get_3d_structure(cid):
    """계산된 3D 구조(SDF) 가져오기"""
    url = f"{BASE_URL}/compound/cid/{cid}/SDF"
    response = requests.get(
        url,
        params={"record_type": "3d"},
        timeout=TIMEOUT
    )
    response.raise_for_status()

    sdf = response.text

    # 정상적인 SDF 구조인지 간단히 확인
    if "M  END" not in sdf and "V2000" not in sdf and "V3000" not in sdf:
        return None

    return sdf


# ----------------------------------
# 화면 디자인
# ----------------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #365c45;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #68766c;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    div[data-testid="stMetric"] {
        background: #f4f8f3;
        border: 1px solid #dce8da;
        padding: 16px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-title">⚗️ PubChem 물질 탐구</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">'
    '물질 이름으로 분자 정보와 2D·3D 구조를 탐색해 보세요.'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "미국 국립보건원(NIH)의 PubChem 데이터를 이용합니다. "
    "API 키는 필요하지 않으며, 인터넷 연결이 필요합니다."
)

# ----------------------------------
# 검색 영역
# ----------------------------------
examples = {
    "직접 입력": "",
    "물 (Water)": "water",
    "포도당 (Glucose)": "glucose",
    "염화나트륨 (Sodium chloride)": "sodium chloride",
    "이산화탄소 (Carbon dioxide)": "carbon dioxide",
    "메탄 (Methane)": "methane",
    "구연산 (Citric acid)": "citric acid",
}

left, right = st.columns([2, 1])

with left:
    selected = st.selectbox(
        "🔎 예시 물질",
        options=list(examples.keys()),
        index=0
    )

with right:
    st.markdown(" ")
    st.markdown(" ")
    st.caption("예시를 선택하거나 직접 검색할 수 있습니다.")

default_name = examples[selected]

with st.form("search_form"):
    compound_name = st.text_input(
        "물질 이름",
        value=default_name,
        placeholder="예: water, glucose, sodium chloride"
    )
    submitted = st.form_submit_button(
        "🔍 물질 정보 검색",
        type="primary",
        use_container_width=True
    )

# 검색 결과를 세션에 보관
if submitted:
    if not compound_name.strip():
        st.warning("검색할 물질 이름을 입력해 주세요.")
    else:
        st.session_state["compound_name"] = compound_name.strip()
        st.session_state["compound_search_requested"] = True

# ----------------------------------
# 검색 결과 표시
# ----------------------------------
if st.session_state.get("compound_search_requested", False):
    name = st.session_state.get("compound_name", "")

    try:
        with st.spinner("PubChem에서 물질 정보를 가져오는 중입니다..."):
            cid = search_compound(name)

            if cid is None:
                st.warning(
                    "검색 결과가 없습니다. 영문 물질 이름이나 "
                    "다른 표기를 사용해 보세요."
                )
                st.stop()

            properties = get_properties(cid)

        if not properties:
            st.error("물질의 기본 정보를 가져오지 못했습니다.")
            st.stop()

        formula = properties.get("MolecularFormula", "정보 없음")
        weight = properties.get("MolecularWeight", "정보 없음")

        st.divider()
        st.subheader(f"📋 {name} 검색 결과")

        metric1, metric2, metric3 = st.columns(3)

        with metric1:
            st.metric("분자식", formula)

        with metric2:
            if weight != "정보 없음":
                st.metric("분자량", f"{float(weight):,.3f} g/mol")
            else:
                st.metric("분자량", "정보 없음")

        with metric3:
            st.metric("PubChem CID", str(cid))

        st.markdown(
            f"[PubChem 원본 물질 페이지 열기]"
            f"(https://pubchem.ncbi.nlm.nih.gov/compound/{cid})"
        )

        # ----------------------------------
        # 2D 구조
        # ----------------------------------
        st.divider()
        st.subheader("🧩 2D 분자 구조")
        st.caption("평면 구조 그림으로 원자와 결합의 배열을 관찰합니다.")

        try:
            with st.spinner("2D 구조 그림을 불러오는 중입니다..."):
                image_data = get_2d_image(cid)

            st.image(
                image_data,
                caption=f"{name}의 2D 구조 (출처: PubChem)",
                width=420
            )

        except requests.RequestException:
            st.warning("2D 구조 이미지를 불러오지 못했습니다.")

        # ----------------------------------
        # 3D 구조
        # ----------------------------------
        st.divider()
        st.subheader("🧊 3D 입체 구조")
        st.caption(
            "마우스로 드래그하면 회전하고, 휠로 확대·축소할 수 있습니다."
        )

        try:
            with st.spinner("3D 구조를 계산·조회하는 중입니다..."):
                sdf_data = get_3d_structure(cid)

            if sdf_data:
                # JSON 문자열로 안전하게 전달
                import json
                sdf_json = json.dumps(sdf_data)

                html_code = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
                    <style>
                        html, body {{
                            margin: 0;
                            padding: 0;
                            background: #ffffff;
                            font-family: sans-serif;
                        }}
                        #viewer {{
                            width: 100%;
                            height: 440px;
                            position: relative;
                            border: 1px solid #e0e6e0;
                            border-radius: 12px;
                            overflow: hidden;
                        }}
                    </style>
                </head>
                <body>
                    <div id="viewer"></div>
                    <script>
                        const sdf = {sdf_json};
                        const element = document.getElementById("viewer");
                        const viewer = $3Dmol.createViewer(element, {{
                            backgroundColor: "white"
                        }});

                        viewer.addModel(sdf, "sdf");
                        viewer.setStyle({{}}, {{
                            stick: {{ radius: 0.16 }},
                            sphere: {{ scale: 0.23 }}
                        }});
                        viewer.zoomTo();
                        viewer.render();
                        viewer.zoom(0.9);
                    </script>
                </body>
                </html>
                """

                components.html(
                    html_code,
                    height=455,
                    scrolling=False
                )

                st.caption(
                    "자료: PubChem 계산 3D 좌표(SDF) · "
                    "3D 시각화: 3Dmol.js"
                )

            else:
                st.info(
                    "이 물질은 PubChem에서 사용할 수 있는 "
                    "3D 구조를 찾지 못했습니다. 2D 구조를 이용해 주세요."
                )

        except requests.RequestException:
            st.info(
                "3D 구조를 가져오지 못했습니다. "
                "잠시 후 다시 시도하거나 2D 구조를 확인해 주세요."
            )

    except requests.Timeout:
        st.error("PubChem 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.")

    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else 0

        if status == 404:
            st.warning(
                "해당 물질의 정보를 찾지 못했습니다. "
                "물질 이름을 확인해 주세요."
            )
        elif status == 503:
            st.warning(
                "PubChem 요청이 많아 일시적으로 응답하지 않습니다. "
                "잠시 후 다시 시도해 주세요."
            )
        else:
            st.error(f"PubChem 서버 오류가 발생했습니다. (HTTP {status})")

    except requests.RequestException:
        st.error(
            "인터넷 연결 또는 PubChem 서버를 확인해 주세요."
        )

    except (ValueError, KeyError, TypeError) as error:
        st.error(
            "응답 데이터를 처리하지 못했습니다. "
            "다른 물질 이름으로 다시 시도해 주세요."
        )

# ----------------------------------
# 하단 안내
# ----------------------------------
st.divider()
st.markdown("### 💡 탐구 질문")
st.markdown("""
- 분자식이 같은 물질은 반드시 같은 구조를 가질까요?
- 2D 구조와 3D 구조는 어떤 차이가 있을까요?
- 원자의 종류와 개수가 달라지면 분자량은 어떻게 변할까요?
""")

st.caption(
    "데이터 출처: PubChem, National Library of Medicine (NIH) · "
    "3D 시각화: 3Dmol.js"
)
