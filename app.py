"""
Fintech Identity Demo — Streamlit App
Portable, privacy-preserving digital identity flow (full mock).
"""

import hashlib
import random
import re
import string
import time
import uuid
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fintech Identity Demo",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Demo Cases  (key must exactly match the selectbox options)
# ─────────────────────────────────────────────────────────────
DEMO_CASES = {
    "✅ Clean User": {
        "name": "Priya Sharma",
        "dob": date(1995, 6, 15),
        "pan": "ABCPS1234F",
        "income": 850000,
        "device_id": "DEV-CLEAN-001",
        "fraud_signals": {
            "device_reuse": False,
            "pan_velocity_high": False,
            "age_mismatch": False,
            "synthetic_identity": False,
        },
    },
    "⚠️ High Velocity": {
        "name": "Rahul Verma",
        "dob": date(1988, 3, 22),
        "pan": "DEFPV5678G",
        "income": 320000,
        "device_id": "DEV-VEL-002",
        "fraud_signals": {
            "device_reuse": False,
            "pan_velocity_high": True,
            "age_mismatch": False,
            "synthetic_identity": False,
        },
    },
    "🚨 Device Reuse": {
        "name": "Anil Kumar",
        "dob": date(1979, 11, 5),
        "pan": "GHIKD9012H",
        "income": 120000,
        "device_id": "DEV-REUSE-003",
        "fraud_signals": {
            "device_reuse": True,
            "pan_velocity_high": False,
            "age_mismatch": False,
            "synthetic_identity": False,
        },
    },
    "💀 Synthetic Identity": {
        "name": "Xyz Abc",
        "dob": date(2001, 1, 1),
        "pan": "JKLSY3456I",
        "income": 999999,
        "device_id": "DEV-SYN-004",
        "fraud_signals": {
            "device_reuse": True,
            "pan_velocity_high": True,
            "age_mismatch": True,
            "synthetic_identity": True,
        },
    },
}

DEMO_OPTIONS = ["🔧 Create Custom"] + list(DEMO_CASES.keys())

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def validate_pan(pan: str) -> bool:
    return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan.upper()))


def compute_risk_score(signals: dict) -> float:
    weights = {
        "device_reuse": 0.30,
        "pan_velocity_high": 0.25,
        "age_mismatch": 0.20,
        "synthetic_identity": 0.25,
    }
    return round(sum(weights[k] * (1 if v else 0) for k, v in signals.items()), 2)


def mock_kyc_result(name, dob, pan, signals):
    age = (date.today() - dob).days // 365
    issues = []
    if age < 18:
        issues.append("Applicant under 18")
    if not validate_pan(pan):
        issues.append("Invalid PAN format")
    if signals.get("synthetic_identity"):
        issues.append("Synthetic identity detected")
    if signals.get("age_mismatch"):
        issues.append("Age mismatch with bureau data")
    passed = len(issues) == 0
    return {"passed": passed, "issues": issues, "age": age}


def generate_did(name: str) -> str:
    seed = hashlib.sha256(f"{name}{time.time()}".encode()).hexdigest()[:16]
    return f"did:example:{seed}"


def generate_vc(did: str, name: str, dob: date, pan: str, income: int) -> dict:
    return {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "KYCVerification"],
        "issuer": "did:example:issuer-fintech-demo",
        "issuanceDate": datetime.utcnow().isoformat() + "Z",
        "credentialSubject": {
            "id": did,
            "name": name,
            "dob": str(dob),
            "pan": pan[-4:].rjust(len(pan), "*"),  # mask PAN
            "incomeBand": ">10L" if income >= 1000000 else (">5L" if income >= 500000 else "<5L"),
            "kycStatus": "verified",
        },
        "proof": {
            "type": "Ed25519Signature2020",
            "created": datetime.utcnow().isoformat() + "Z",
            "signature": hashlib.sha256(f"{did}{name}{dob}".encode()).hexdigest(),
        },
    }


def verify_vc(vc: dict) -> bool:
    cs = vc.get("credentialSubject", {})
    expected_sig = hashlib.sha256(
        f"{cs.get('id','')}{cs.get('name','')}{cs.get('dob','')}".encode()
    ).hexdigest()
    return vc.get("proof", {}).get("signature") == expected_sig


def generate_zkp(is_adult: bool) -> dict:
    return {
        "protocol": "groth16",
        "curve": "bn128",
        "proof": {
            "pi_a": [str(random.randint(10**10, 10**15)), str(random.randint(10**10, 10**15)), "1"],
            "pi_b": [[str(random.randint(10**10, 10**15)), str(random.randint(10**10, 10**15))]],
            "pi_c": [str(random.randint(10**10, 10**15)), str(random.randint(10**10, 10**15)), "1"],
        },
        "publicSignals": ["1" if is_adult else "0"],
    }


# ─────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.metric-card {
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 16px;
    padding: 20px;
    color: white;
    text-align: center;
    margin-bottom: 8px;
    border: 1px solid rgba(139,92,246,0.3);
}
.metric-card .value { font-size: 2rem; font-weight: 700; }
.metric-card .label { font-size: 0.85rem; opacity: 0.8; margin-top: 4px; }

.status-ok {
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.4);
    border-radius: 10px;
    padding: 12px 16px;
    color: #34d399;
    font-weight: 600;
}
.status-fail {
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 10px;
    padding: 12px 16px;
    color: #f87171;
    font-weight: 600;
}
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #a78bfa;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(167,139,250,0.2);
    padding-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "did": None,
        "vc": None,
        "zkp": None,
        "kyc_result": None,
        "risk_score": None,
        "fraud_signals": None,
        "vc_verified": None,
        "zkp_verified": None,
        "step": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    _init()

    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.title("🔐 Identity Demo")
        st.caption("Portable, privacy-preserving KYC")
        st.divider()

        selected_demo = st.selectbox(
            "Load Demo Case",
            options=DEMO_OPTIONS,
            index=0,
            key="selected_demo",
        )

        st.divider()
        st.markdown("**Flow Steps**")
        steps = ["1 · Input", "2 · KYC", "3 · VC Issue", "4 · ZKP", "5 · Verify"]
        for i, s in enumerate(steps):
            icon = "✅" if st.session_state.step > i else ("▶️" if st.session_state.step == i else "⬜")
            st.markdown(f"{icon} {s}")

        st.divider()
        if st.button("🔄 Reset", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ── Resolve input defaults ────────────────────────────────
    if selected_demo == "🔧 Create Custom":
        name_default = ""
        dob_default = date(1995, 1, 1)
        pan_default = ""
        income_default = 500000
        device_default = "DEV-CUSTOM-" + "".join(random.choices(string.digits, k=4))
        fraud_defaults = {
            "device_reuse": False,
            "pan_velocity_high": False,
            "age_mismatch": False,
            "synthetic_identity": False,
        }
    else:
        demo_data = DEMO_CASES[selected_demo]
        name_default = demo_data["name"]
        dob_default = demo_data["dob"]
        pan_default = demo_data["pan"]
        income_default = demo_data["income"]
        device_default = demo_data["device_id"]
        fraud_defaults = demo_data["fraud_signals"]

    # ─────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────
    st.title("🏦 Fintech Identity Verification")
    st.caption("End-to-end mock flow: KYC → Verifiable Credential → ZKP → Bank Verification")

    tabs = st.tabs(["📋 Input & KYC", "🪪 Credential", "🔒 ZKP Proof", "🏛️ Bank Verify", "📊 Analytics"])

    # ─────────────────────────────────────────────────────────
    # TAB 1 — Input & KYC
    # ─────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="section-header">Applicant Details</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=name_default, placeholder="e.g. Priya Sharma")
            dob = st.date_input("Date of Birth", value=dob_default, min_value=date(1920, 1, 1), max_value=date.today())
            pan = st.text_input("PAN Number", value=pan_default, placeholder="ABCDE1234F").upper()

        with col2:
            income = st.number_input("Annual Income (₹)", value=income_default, step=10000, min_value=0)
            device_id = st.text_input("Device ID", value=device_default)

        st.markdown('<div class="section-header" style="margin-top:16px">Fraud Signals (Mock)</div>', unsafe_allow_html=True)
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        device_reuse = fcol1.checkbox("Device Reuse", value=fraud_defaults["device_reuse"])
        pan_velocity = fcol2.checkbox("PAN Velocity High", value=fraud_defaults["pan_velocity_high"])
        age_mismatch = fcol3.checkbox("Age Mismatch", value=fraud_defaults["age_mismatch"])
        synthetic_id = fcol4.checkbox("Synthetic Identity", value=fraud_defaults["synthetic_identity"])

        signals = {
            "device_reuse": device_reuse,
            "pan_velocity_high": pan_velocity,
            "age_mismatch": age_mismatch,
            "synthetic_identity": synthetic_id,
        }

        st.divider()
        if st.button("🚀 Run KYC Check", type="primary", use_container_width=True):
            if not name:
                st.error("Please enter a name.")
            elif not validate_pan(pan):
                st.error("❌ Invalid PAN format. Expected: ABCDE1234F")
            else:
                with st.spinner("Running KYC checks…"):
                    time.sleep(0.8)
                    result = mock_kyc_result(name, dob, pan, signals)
                    risk = compute_risk_score(signals)
                    did = generate_did(name)
                    st.session_state.kyc_result = result
                    st.session_state.risk_score = risk
                    st.session_state.fraud_signals = signals
                    st.session_state.did = did
                    st.session_state.step = max(st.session_state.step, 1)
                st.success("KYC check complete!")

        results = st.session_state.kyc_result
        if results:
            st.divider()
            st.markdown('<div class="section-header">KYC Results</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Status", "✅ PASSED" if results["passed"] else "❌ FAILED")
            c2.metric("Age", results["age"])
            c3.metric("Risk Score", f"{st.session_state.risk_score:.0%}")

            if results["issues"]:
                for issue in results["issues"]:
                    st.error(f"⚠️ {issue}")
            else:
                st.success("✅ No KYC issues found")

            st.divider()
            st.markdown('<div class="section-header">Fraud Signal Details</div>', unsafe_allow_html=True)
            fraud_col1, fraud_col2 = st.columns(2)

            with fraud_col1:
                if st.session_state.fraud_signals["device_reuse"]:
                    st.error("⚠️ Device Reuse Detected")
                else:
                    st.success("✅ No Device Reuse")

            with fraud_col2:
                if st.session_state.fraud_signals["pan_velocity_high"]:
                    st.error("⚠️ High PAN Velocity")
                else:
                    st.success("✅ Normal PAN Velocity")

            fcol_a, fcol_b = st.columns(2)
            with fcol_a:
                if st.session_state.fraud_signals["age_mismatch"]:
                    st.error("⚠️ Age Mismatch Detected")
                else:
                    st.success("✅ Age Matches Bureau")

            with fcol_b:
                if st.session_state.fraud_signals["synthetic_identity"]:
                    st.error("⚠️ Synthetic Identity Risk")
                else:
                    st.success("✅ Identity Looks Genuine")

            st.markdown(f"**DID assigned:** `{st.session_state.did}`")

    # ─────────────────────────────────────────────────────────
    # TAB 2 — VC Issuance
    # ─────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="section-header">Verifiable Credential Issuance</div>', unsafe_allow_html=True)

        if not st.session_state.kyc_result:
            st.info("Complete KYC (Tab 1) first.")
        elif not st.session_state.kyc_result["passed"]:
            st.error("❌ KYC did not pass — cannot issue VC.")
        else:
            st.success(f"KYC passed. DID: `{st.session_state.did}`")

            if st.button("🪪 Issue Verifiable Credential", type="primary"):
                with st.spinner("Issuing VC…"):
                    time.sleep(0.6)
                    vc = generate_vc(
                        st.session_state.did,
                        name_default or "User",
                        dob_default,
                        pan_default or "XXXXX0000X",
                        income_default,
                    )
                    st.session_state.vc = vc
                    st.session_state.step = max(st.session_state.step, 2)
                st.success("✅ VC issued and stored in wallet!")

            if st.session_state.vc:
                st.json(st.session_state.vc)

    # ─────────────────────────────────────────────────────────
    # TAB 3 — ZKP Proof
    # ─────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="section-header">Zero-Knowledge Proof (Age ≥ 18)</div>', unsafe_allow_html=True)

        if not st.session_state.vc:
            st.info("Issue a VC (Tab 2) first.")
        else:
            age_for_zkp = (date.today() - dob_default).days // 365
            st.write(f"Proving age ≥ 18 without revealing exact DOB. Computed age: **{age_for_zkp}**")

            if st.button("🔒 Generate ZKP Proof", type="primary"):
                with st.spinner("Generating proof…"):
                    time.sleep(0.7)
                    zkp = generate_zkp(is_adult=(age_for_zkp >= 18))
                    st.session_state.zkp = zkp
                    st.session_state.step = max(st.session_state.step, 3)
                st.success("✅ Proof generated!")

            if st.session_state.zkp:
                st.json(st.session_state.zkp)
                pub = st.session_state.zkp["publicSignals"]
                if pub[0] == "1":
                    st.success("✅ Public signal: ADULT (age ≥ 18 proven)")
                else:
                    st.error("❌ Public signal: NOT ADULT")

    # ─────────────────────────────────────────────────────────
    # TAB 4 — Bank Verification
    # ─────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="section-header">Bank Verification Dashboard</div>', unsafe_allow_html=True)

        if not st.session_state.vc or not st.session_state.zkp:
            st.info("Complete VC issuance and ZKP proof first.")
        else:
            if st.button("🏛️ Run Bank Verification", type="primary"):
                with st.spinner("Verifying credentials…"):
                    time.sleep(0.8)
                    vc_valid = verify_vc(st.session_state.vc)
                    zkp_valid = st.session_state.zkp["publicSignals"][0] == "1"
                    st.session_state.vc_verified = vc_valid
                    st.session_state.zkp_verified = zkp_valid
                    st.session_state.step = max(st.session_state.step, 4)

            if st.session_state.vc_verified is not None:
                r1, r2, r3 = st.columns(3)

                vc_ok = st.session_state.vc_verified
                zkp_ok = st.session_state.zkp_verified
                risk_ok = (st.session_state.risk_score or 1.0) <= 0.5
                overall = vc_ok and zkp_ok and risk_ok

                r1.metric("VC Signature", "✅ Valid" if vc_ok else "❌ Invalid")
                r2.metric("ZKP Age Proof", "✅ Verified" if zkp_ok else "❌ Failed")
                r3.metric("Risk Score", f"{(st.session_state.risk_score or 0):.0%}", delta="Low" if risk_ok else "High", delta_color="normal" if risk_ok else "inverse")

                st.divider()
                if overall:
                    st.markdown('<div class="status-ok">🎉 APPROVED — All checks passed. Account can be opened.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="status-fail">🚫 REJECTED — One or more checks failed.</div>', unsafe_allow_html=True)

                st.divider()
                st.markdown("**Credential Subject Details**")
                cs = st.session_state.vc.get("credentialSubject", {})
                st.table(pd.DataFrame(list(cs.items()), columns=["Field", "Value"]))

    # ─────────────────────────────────────────────────────────
    # TAB 5 — Analytics
    # ─────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown('<div class="section-header">Analytics & Insights</div>', unsafe_allow_html=True)

        # Risk gauge
        risk = st.session_state.risk_score or 0.0
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk * 100,
            title={"text": "Fraud Risk Score (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#6c63ff"},
                "steps": [
                    {"range": [0, 30], "color": "#d1fae5"},
                    {"range": [30, 60], "color": "#fef3c7"},
                    {"range": [60, 100], "color": "#fee2e2"},
                ],
                "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": 60},
            },
        ))
        fig_gauge.update_layout(height=300, margin=dict(t=40, b=10, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.divider()

        # Fraud signal bar chart
        signals_data = st.session_state.fraud_signals or {
            "device_reuse": False,
            "pan_velocity_high": False,
            "age_mismatch": False,
            "synthetic_identity": False,
        }
        df_signals = pd.DataFrame({
            "Signal": list(signals_data.keys()),
            "Triggered": [1 if v else 0 for v in signals_data.values()],
            "Color": ["red" if v else "green" for v in signals_data.values()],
        })
        fig_bar = px.bar(
            df_signals,
            x="Signal",
            y="Triggered",
            color="Color",
            color_discrete_map={"red": "#f87171", "green": "#34d399"},
            title="Fraud Signal Breakdown",
        )
        fig_bar.update_layout(showlegend=False, height=300, margin=dict(t=50, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # Flow summary table
        flow_rows = [
            {"Step": "Wallet / DID", "Status": "✅ Done" if st.session_state.did else "⬜ Pending"},
            {"Step": "KYC Check", "Status": ("✅ Passed" if (st.session_state.kyc_result or {}).get("passed") else "❌ Failed") if st.session_state.kyc_result else "⬜ Pending"},
            {"Step": "VC Issuance", "Status": "✅ Issued" if st.session_state.vc else "⬜ Pending"},
            {"Step": "ZKP Proof", "Status": "✅ Generated" if st.session_state.zkp else "⬜ Pending"},
            {"Step": "Bank Verification", "Status": ("✅ Approved" if (st.session_state.vc_verified and st.session_state.zkp_verified) else "❌ Rejected") if st.session_state.vc_verified is not None else "⬜ Pending"},
        ]
        st.table(pd.DataFrame(flow_rows))


if __name__ == "__main__":
    main()
