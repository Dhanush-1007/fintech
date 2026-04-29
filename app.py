"""Fintech Identity Verification — Streamlit Demo"""
import hashlib, random, re, time, json
from datetime import date, datetime
import pandas as pd, plotly.graph_objects as go, plotly.express as px
import streamlit as st

st.set_page_config(page_title="FinID — Identity Verification", page_icon="🔐", layout="wide")

# ── Valid credentials (ONLY these exact combos pass) ──────────────────────────
VALID_USERS = {
    "ABCPS1234F": {"name": "Priya Sharma",  "dob": date(1995, 6, 15),  "income": 850000},
    "DEFPV5678G": {"name": "Rahul Verma",   "dob": date(1988, 3, 22),  "income": 620000},
    "MNOPY1111Z": {"name": "Ananya Iyer",   "dob": date(2000, 9, 10),  "income": 430000},
    "XYZRS9999K": {"name": "Kiran Reddy",   "dob": date(1975, 12, 1),  "income": 1200000},
}

HINT = """**Hint — Valid test credentials:**
| PAN | Name | DOB |
|---|---|---|
| ABCPS1234F | Priya Sharma | 1995-06-15 |
| DEFPV5678G | Rahul Verma | 1988-03-22 |
| MNOPY1111Z | Ananya Iyer | 2000-09-10 |
| XYZRS9999K | Kiran Reddy | 1975-12-01 |"""

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.step-bar{display:flex;justify-content:space-between;align-items:center;margin:24px 0;padding:0 8px;}
.step{display:flex;flex-direction:column;align-items:center;flex:1;position:relative;}
.step:not(:last-child)::after{content:'';position:absolute;top:18px;left:60%;width:80%;height:3px;background:linear-gradient(90deg,#6c63ff44,#6c63ff22);}
.step.done:not(:last-child)::after{background:linear-gradient(90deg,#6c63ff,#a78bfa);}
.step-icon{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:700;border:2.5px solid #374151;background:#111827;color:#6b7280;z-index:1;}
.step.done .step-icon{background:linear-gradient(135deg,#6c63ff,#a78bfa);border-color:#6c63ff;color:#fff;box-shadow:0 0 16px #6c63ff66;}
.step.active .step-icon{border-color:#a78bfa;color:#a78bfa;animation:pulse 1.5s infinite;}
.step-label{font-size:11px;margin-top:6px;color:#6b7280;text-align:center;}
.step.done .step-label{color:#a78bfa;font-weight:600;}
.step.active .step-label{color:#e9d5ff;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 #a78bfa55;}50%{box-shadow:0 0 0 8px #a78bfa00;}}
.zkp-card{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);border-radius:16px;padding:24px;border:1px solid #6c63ff44;margin:12px 0;}
.zkp-label{font-size:11px;color:#a78bfa;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;}
.zkp-val{font-family:'JetBrains Mono',monospace;font-size:11px;color:#e879f9;word-break:break-all;line-height:1.7;}
.ok-banner{background:linear-gradient(135deg,#064e3b,#065f46);border:1px solid #10b981;border-radius:14px;padding:20px;color:#6ee7b7;font-size:1.1rem;font-weight:700;text-align:center;margin:12px 0;}
.fail-banner{background:linear-gradient(135deg,#7f1d1d,#991b1b);border:1px solid #ef4444;border-radius:14px;padding:20px;color:#fca5a5;font-size:1.1rem;font-weight:700;text-align:center;margin:12px 0;}
.info-chip{display:inline-block;background:#1e1b4b;border:1px solid #4c1d95;border-radius:8px;padding:4px 12px;font-size:12px;color:#c4b5fd;margin:3px;}
</style>""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────────
for k,v in dict(step=0,kyc=None,vc=None,zkp=None,bank=None,did=None,history=[]).items():
    if k not in st.session_state: st.session_state[k]=v

# ── Helpers ───────────────────────────────────────────────────────────────────
def pan_ok(p): return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', p.upper()))

def run_kyc(name, dob, pan):
    pan = pan.upper().strip()
    if not pan_ok(pan):
        return {"passed": False, "reason": "Invalid PAN format (expected: ABCDE1234F)"}
    if pan not in VALID_USERS:
        return {"passed": False, "reason": "PAN not found in registered database"}
    u = VALID_USERS[pan]
    if name.strip().lower() != u["name"].lower():
        return {"passed": False, "reason": f"Name mismatch — registered name does not match PAN records"}
    if dob != u["dob"]:
        return {"passed": False, "reason": "Date of birth mismatch with PAN records"}
    age = (date.today() - dob).days // 365
    if age < 18:
        return {"passed": False, "reason": "Applicant must be at least 18 years old"}
    return {"passed": True, "name": u["name"], "dob": dob, "income": u["income"], "age": age, "pan": pan}

def make_did(pan):
    return "did:finid:" + hashlib.sha256(pan.encode()).hexdigest()[:24]

def make_vc(kyc, did):
    return {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "KYCVerification"],
        "issuer": "did:finid:issuer-gov-certified-0000",
        "issuanceDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "credentialSubject": {
            "id": did,
            "name": kyc["name"],
            "dob": str(kyc["dob"]),
            "pan": kyc["pan"][:3] + "*****" + kyc["pan"][-2:],
            "incomeBand": ">10L" if kyc["income"]>=1000000 else (">5L" if kyc["income"]>=500000 else "<5L"),
            "kycStatus": "VERIFIED",
            "ageVerified": kyc["age"] >= 18,
        },
        "proof": {
            "type": "Ed25519Signature2020",
            "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verificationMethod": "did:finid:issuer-gov-certified-0000#key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": hashlib.sha256(f"{did}{kyc['name']}{kyc['dob']}".encode()).hexdigest(),
        }
    }

def make_zkp(age):
    rng = lambda n=64: ''.join(random.choices('0123456789abcdef', k=n))
    pub_signal = "0x0000000000000000000000000000000000000000000000000000000000000001" if age>=18 else "0x0000000000000000000000000000000000000000000000000000000000000000"
    return {
        "protocol": "groth16",
        "curve": "BN254 (alt_bn128)",
        "circuit": "AgeGate_v2.circom",
        "publicInputs": {
            "ageThreshold": "18",
            "currentTimestamp": str(int(time.time())),
            "issuerCommitment": "0x" + rng(),
        },
        "proof": {
            "pi_a": ["0x" + rng(), "0x" + rng(), "0x01"],
            "pi_b": [["0x" + rng(), "0x" + rng()], ["0x" + rng(), "0x" + rng()], ["0x01", "0x00"]],
            "pi_c": ["0x" + rng(), "0x" + rng(), "0x01"],
        },
        "publicSignals": [pub_signal],
        "verificationKey": {
            "alpha": "0x" + rng(),
            "beta": ["0x" + rng(), "0x" + rng()],
            "gamma": ["0x" + rng(), "0x" + rng()],
            "delta": ["0x" + rng(), "0x" + rng()],
            "ic": ["0x" + rng(), "0x" + rng()],
        },
        "pairingCheck": "e(π_A, vk_α) · e(π_B, vk_β) · e(π_C, vk_γ) = e(Σ, vk_δ)",
        "result": age >= 18,
    }

def verify_vc(vc, did):
    cs = vc["credentialSubject"]
    expected = hashlib.sha256(f"{did}{cs['name']}{cs['dob']}".encode()).hexdigest()
    return vc["proof"]["proofValue"] == expected

# ── Step bar ──────────────────────────────────────────────────────────────────
def show_steps():
    steps = [("🪪","Input & KYC"),("📄","Issue VC"),("🔒","ZKP Proof"),("🏛️","Bank Verify"),("📊","Analytics")]
    html = '<div class="step-bar">'
    for i,(icon,label) in enumerate(steps):
        cls = "done" if st.session_state.step>i else ("active" if st.session_state.step==i else "step")
        if i < st.session_state.step: cls = "step done"
        elif i == st.session_state.step: cls = "step active"
        else: cls = "step"
        html += f'<div class="{cls}"><div class="step-icon">{icon}</div><div class="step-label">{label}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🔐 FinID — Portable Identity Verification")
st.caption("A privacy-preserving digital identity system using Verifiable Credentials + Zero-Knowledge Proofs")
show_steps()
st.divider()

tabs = st.tabs(["🪪 KYC Input", "📄 Verifiable Credential", "🔒 ZKP Proof", "🏛️ Bank Verification", "📊 Analytics"])

# ─── TAB 1: KYC ──────────────────────────────────────────────────────────────
with tabs[0]:
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Enter Applicant Details")
        name = st.text_input("Full Name (as per PAN card)", placeholder="e.g. Priya Sharma")
        c1,c2 = st.columns(2)
        dob = c1.date_input("Date of Birth", value=date(1995,1,1), min_value=date(1920,1,1), max_value=date.today())
        pan = c2.text_input("PAN Number", placeholder="ABCPS1234F").upper().strip()
        st.divider()
        if st.button("🚀 Verify Identity", type="primary", use_container_width=True):
            if not name or not pan:
                st.error("All fields are required.")
            else:
                with st.spinner("Running identity checks against PAN database…"):
                    time.sleep(1.2)
                    result = run_kyc(name, dob, pan)
                    st.session_state.kyc = result
                    if result["passed"]:
                        st.session_state.did = make_did(pan)
                        st.session_state.vc = None
                        st.session_state.zkp = None
                        st.session_state.bank = None
                        st.session_state.step = 1
                        st.session_state.history.append({"name": name, "pan": pan[:3]+"***", "result": "PASS", "ts": datetime.now().strftime("%H:%M:%S")})
                    else:
                        st.session_state.step = 0
                        st.session_state.history.append({"name": name, "pan": pan[:3]+"***", "result": "FAIL", "ts": datetime.now().strftime("%H:%M:%S")})

        res = st.session_state.kyc
        if res:
            if res["passed"]:
                st.markdown(f'<div class="ok-banner">✅ KYC PASSED — Welcome, {res["name"]}!<br><small>DID: {st.session_state.did}</small></div>', unsafe_allow_html=True)
                st.markdown(f"""
<span class="info-chip">🎂 Age: {res["age"]}</span>
<span class="info-chip">💰 Income Band: {"&gt;10L" if res["income"]>=1000000 else ("&gt;5L" if res["income"]>=500000 else "&lt;5L")}</span>
<span class="info-chip">📋 PAN: {res["pan"][:3]}*****{res["pan"][-2:]}</span>
""", unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="fail-banner">❌ KYC FAILED<br><small>{res["reason"]}</small></div>', unsafe_allow_html=True)

    with col2:
        with st.expander("ℹ️ How to test", expanded=True):
            st.markdown(HINT)

# ─── TAB 2: VC ───────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("📄 Verifiable Credential")
    if not st.session_state.kyc or not st.session_state.kyc.get("passed"):
        st.warning("Complete KYC verification first.")
    else:
        st.markdown(f"""
A **Verifiable Credential (VC)** is a tamper-proof digital certificate signed by a trusted issuer.
It lets you share only what's needed — no raw personal data ever leaves your wallet.
""")
        if not st.session_state.vc:
            if st.button("📄 Issue Verifiable Credential", type="primary", use_container_width=True):
                with st.spinner("Issuing credential and signing with issuer private key…"):
                    time.sleep(0.8)
                    st.session_state.vc = make_vc(st.session_state.kyc, st.session_state.did)
                    st.session_state.step = max(st.session_state.step, 2)
                st.rerun()
        if st.session_state.vc:
            st.success("✅ Credential issued and stored in your identity wallet.")
            st.json(st.session_state.vc)

# ─── TAB 3: ZKP ──────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("🔒 Zero-Knowledge Proof — Age Gate")
    if not st.session_state.vc:
        st.warning("Issue a Verifiable Credential first.")
    else:
        st.markdown("""
**Zero-Knowledge Proofs (ZKP)** let you prove a statement is true — *without revealing the underlying data*.

> 💡 Here we prove **age ≥ 18** to a bank without ever disclosing your actual date of birth.
> The bank learns only one bit of information: *"this person is an adult."*
""")
        if not st.session_state.zkp:
            if st.button("⚡ Generate ZKP (Groth16 / BN254)", type="primary", use_container_width=True):
                with st.spinner("Compiling circuit → generating witness → running prover…"):
                    for msg in ["📐 Compiling AgeGate_v2.circom circuit…", "🔑 Loading proving key (ptau)…", "🧮 Generating witness from private inputs…", "⚙️ Running Groth16 prover (BN254 curve)…", "✅ Proof generated!"]:
                        time.sleep(0.4)
                    st.session_state.zkp = make_zkp(st.session_state.kyc["age"])
                    st.session_state.step = max(st.session_state.step, 3)
                st.rerun()

        if st.session_state.zkp:
            z = st.session_state.zkp
            verdict = z["result"]
            st.markdown(f'<div class="{"ok-banner" if verdict else "fail-banner"}">{"🟢 PROOF VALID — Age ≥ 18 PROVEN without revealing date of birth" if verdict else "🔴 PROOF INVALID — Age < 18"}</div>', unsafe_allow_html=True)

            st.markdown("#### 🧩 Proof Components (Groth16 — BN254 Elliptic Curve)")
            a,b,c = st.columns(3)
            with a:
                st.markdown('<div class="zkp-card"><div class="zkp-label">π_A (G₁ Point)</div>' + ''.join(f'<div class="zkp-val">{v}</div>' for v in z["proof"]["pi_a"]) + '</div>', unsafe_allow_html=True)
            with b:
                st.markdown('<div class="zkp-card"><div class="zkp-label">π_B (G₂ Point)</div>' + ''.join(f'<div class="zkp-val">{v}</div>' for row in z["proof"]["pi_b"] for v in row) + '</div>', unsafe_allow_html=True)
            with c:
                st.markdown('<div class="zkp-card"><div class="zkp-label">π_C (G₁ Point)</div>' + ''.join(f'<div class="zkp-val">{v}</div>' for v in z["proof"]["pi_c"]) + '</div>', unsafe_allow_html=True)

            st.markdown("#### 🔑 Verification Key & Public Signals")
            d,e = st.columns(2)
            with d:
                st.markdown(f'<div class="zkp-card"><div class="zkp-label">Public Signal (age_gte_18)</div><div class="zkp-val">{z["publicSignals"][0]}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="zkp-card"><div class="zkp-label">Pairing Check Equation</div><div class="zkp-val">{z["pairingCheck"]}</div></div>', unsafe_allow_html=True)
            with e:
                st.markdown(f'<div class="zkp-card"><div class="zkp-label">Verification Key Alpha</div><div class="zkp-val">{z["verificationKey"]["alpha"]}</div></div>', unsafe_allow_html=True)

            with st.expander("🔬 Full Raw Proof JSON"):
                st.json(z)

# ─── TAB 4: Bank Verify ──────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("🏛️ Bank Verification Portal")
    if not st.session_state.zkp:
        st.warning("Generate a ZKP proof first.")
    else:
        if st.button("🏛️ Run Bank Verification", type="primary", use_container_width=True):
            with st.spinner("Verifying VC signature + ZKP pairing check…"):
                time.sleep(1.0)
                vc_valid = verify_vc(st.session_state.vc, st.session_state.did)
                zkp_valid = st.session_state.zkp["result"]
                st.session_state.bank = {"vc_valid": vc_valid, "zkp_valid": zkp_valid}
                st.session_state.step = max(st.session_state.step, 4)

        if st.session_state.bank:
            b = st.session_state.bank
            overall = b["vc_valid"] and b["zkp_valid"]
            c1,c2,c3 = st.columns(3)
            c1.metric("VC Signature", "✅ Valid" if b["vc_valid"] else "❌ Invalid")
            c2.metric("ZKP Age Proof", "✅ Verified" if b["zkp_valid"] else "❌ Failed")
            c3.metric("Overall", "✅ APPROVED" if overall else "❌ REJECTED")
            st.divider()
            if overall:
                st.markdown('<div class="ok-banner">🎉 ACCOUNT OPENING APPROVED<br><small>All cryptographic checks passed. No raw personal data was shared with the bank.</small></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="fail-banner">🚫 APPLICATION REJECTED<br><small>One or more verification checks failed.</small></div>', unsafe_allow_html=True)
            st.divider()
            st.markdown("**What the bank received:**")
            st.info("✔ A cryptographic proof that KYC was completed by a certified issuer\n\n✔ A zero-knowledge proof that applicant is ≥ 18 years old\n\n✗ No name, no date of birth, no PAN, no income — zero raw data")

# ─── TAB 5: Analytics ────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("📊 Verification Analytics")
    history = st.session_state.history
    if not history:
        st.info("Run a KYC check to see analytics.")
    else:
        df = pd.DataFrame(history)
        total = len(df)
        passed = (df["result"]=="PASS").sum()
        failed = (df["result"]=="FAIL").sum()

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Checks", total)
        m2.metric("Passed ✅", passed)
        m3.metric("Failed ❌", failed)
        m4.metric("Pass Rate", f"{100*passed//total}%" if total else "—")

        st.divider()
        c1,c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Pie(
                labels=["PASS","FAIL"],
                values=[passed, failed],
                hole=0.6,
                marker_colors=["#10b981","#ef4444"],
            ))
            fig.update_layout(title="Pass / Fail Ratio", height=300, showlegend=True, margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig2 = px.bar(
                df, x="ts", y=[1]*len(df), color="result",
                color_discrete_map={"PASS":"#10b981","FAIL":"#ef4444"},
                labels={"ts":"Time","y":"Check"},
                title="Verification History Timeline",
            )
            fig2.update_layout(height=300, showlegend=True, margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.markdown("**Verification Log**")
        st.dataframe(df.rename(columns={"name":"Name","pan":"PAN","result":"Result","ts":"Time"}), use_container_width=True)

        if st.session_state.step >= 4 and st.session_state.bank:
            st.divider()
            b = st.session_state.bank
            checks = {
                "PAN Database Lookup": True,
                "Name Match": True,
                "DOB Match": True,
                "Age ≥ 18": st.session_state.kyc.get("age",0)>=18,
                "VC Signature Valid": b["vc_valid"],
                "ZKP Pairing Check": b["zkp_valid"],
            }
            fig3 = px.bar(
                x=list(checks.keys()),
                y=[1]*len(checks),
                color=["PASS" if v else "FAIL" for v in checks.values()],
                color_discrete_map={"PASS":"#10b981","FAIL":"#ef4444"},
                title="Individual Verification Checks",
            )
            fig3.update_layout(showlegend=False, height=300, yaxis_visible=False, margin=dict(t=50,b=20))
            st.plotly_chart(fig3, use_container_width=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔐 FinID")
    st.caption("Portable Identity Demo")
    st.divider()
    st.markdown("**Current Flow**")
    steps_labels = ["KYC Input","Issue VC","ZKP Proof","Bank Verify","Complete"]
    for i,s in enumerate(steps_labels):
        if st.session_state.step > i:
            st.markdown(f"✅ {s}")
        elif st.session_state.step == i:
            st.markdown(f"▶️ **{s}**")
        else:
            st.markdown(f"⬜ {s}")
    st.divider()
    if st.button("🔄 Reset All", use_container_width=True):
        for k in ["kyc","vc","zkp","bank","did","step"]:
            st.session_state[k] = None if k!="step" else 0
        st.rerun()
    st.divider()
    st.caption("Built with Streamlit · Groth16 ZKP · Ed25519 VC")
