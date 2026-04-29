import React, { useEffect, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { apiClient } from "./api.js";
import { buildMockProof } from "./zkp.js";
import { createWallet, getWallet, saveWallet } from "./wallet.js";

export default function App() {
  const [wallet, setWallet] = useState(null);
  const [kyc, setKyc] = useState(null);
  const [vc, setVc] = useState(null);
  const [zkp, setZkp] = useState(null);
  const [verification, setVerification] = useState(null);
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState("");

  useEffect(() => {
    const existing = getWallet();
    if (existing) {
      setWallet(existing);
    }
  }, []);

  // ── Helpers ──────────────────────────────────
  function clearError() {
    setError(null);
  }

  async function run(label, fn) {
    clearError();
    setLoading(label);
    try {
      await fn();
    } catch (e) {
      setError(e.message || "An unknown error occurred");
    } finally {
      setLoading("");
    }
  }

  // ── Wallet ────────────────────────────────────
  function handleCreateWallet() {
    const created = createWallet();
    setWallet(created);
    // Reset downstream state when a new wallet is created
    setKyc(null);
    setVc(null);
    setZkp(null);
    setVerification(null);
    setGraph(null);
  }

  // ── KYC ──────────────────────────────────────
  async function handleStartKyc() {
    if (!wallet) return setError("Create a wallet first");
    await run("kyc-start", async () => {
      const response = await apiClient.startKyc();
      setKyc({
        ...response,
        // Mock liveness data — in production these come from device sensors
        livenessScore: 0.86,
        passedDeepfake: true,
        deviceAttestation: true
      });
    });
  }

  async function handleSubmitKyc() {
    if (!kyc || !wallet) return;
    await run("kyc-submit", async () => {
      const response = await apiClient.verifyKyc({
        sessionId: kyc.sessionId,
        did: wallet.did,
        livenessScore: kyc.livenessScore,
        passedDeepfake: kyc.passedDeepfake,
        deviceAttestation: kyc.deviceAttestation
      });
      setKyc((prev) => ({ ...prev, result: response }));
    });
  }

  // ── Verifiable Credential ─────────────────────
  async function handleIssueVc() {
    if (!wallet) return setError("Create a wallet first");
    if (!kyc?.result?.passed) return setError("KYC must pass before issuing a VC");

    await run("vc-issue", async () => {
      const claims = {
        name: "Verified User",
        dob: "2002-01-01",
        kycStatus: "verified",
        incomeBand: ">10L"
      };
      const response = await apiClient.issueVc({ did: wallet.did, claims });
      const issuedVc = response.vc;
      setVc(issuedVc);
      const updated = { ...wallet, vcs: [...wallet.vcs, issuedVc] };
      saveWallet(updated);
      setWallet(updated);
    });
  }

  async function handleVerifyVc() {
    if (!vc) return setError("Issue a VC first");
    await run("vc-verify", async () => {
      const response = await apiClient.verifyVc({ vc });
      setVerification((prev) => ({
        ...prev,
        vcValid: response.valid,
        subjectDid: response.subjectDid,
        issuerDid: response.issuerDid,
        vcReason: response.reason
      }));
    });
  }

  // ── ZKP ───────────────────────────────────────
  async function handleGenerateProof() {
    if (!wallet) return setError("Create a wallet first");
    await run("zkp-gen", async () => {
      const proof = buildMockProof({ isAdult: true });
      setZkp(proof);
      const updated = { ...wallet, proofs: [...wallet.proofs, proof] };
      saveWallet(updated);
      setWallet(updated);
    });
  }

  async function handleVerifyProof() {
    if (!wallet) return setError("Create a wallet first");
    if (!zkp) return setError("Generate a ZKP proof first");
    await run("zkp-verify", async () => {
      const response = await apiClient.verifyZkp({
        did: wallet.did,
        proof: zkp.proof,
        publicSignals: zkp.publicSignals
      });
      setVerification((prev) => ({
        ...prev,
        zkpValid: response.valid,
        zkpReason: response.reason
      }));
    });
  }

  // ── Graph / Fraud ─────────────────────────────
  async function handleGraphCheck() {
    if (!wallet) return setError("Create a wallet first");
    await run("graph-check", async () => {
      const response = await apiClient.graphCheck({ did: wallet.did });
      setGraph(response);
    });
  }

  // ── Derived state ─────────────────────────────
  const kycPassed = kyc?.result?.passed === true;

  return (
    <div className="app">
      <section className="hero">
        <h1>Portable Identity Wallet</h1>
        <p className="muted">
          Full mock flow: Wallet → KYC → VC issuance → ZKP proof → Bank verification
        </p>
        {error && (
          <p className="error-banner" role="alert">
            ⚠️ {error}
          </p>
        )}
      </section>

      <div className="grid">
        {/* ── 1. Wallet ── */}
        <section className="card">
          <h3>1 · Wallet</h3>
          {wallet ? (
            <div>
              <p className="muted did-label" title={wallet.did}>
                DID: <span className="mono">{wallet.did.slice(0, 30)}…</span>
              </p>
              <p className="muted">VCs stored: <strong>{wallet.vcs.length}</strong></p>
              <p className="muted">Proofs stored: <strong>{wallet.proofs.length}</strong></p>
              <button className="button secondary small" onClick={handleCreateWallet}>
                Reset Wallet
              </button>
            </div>
          ) : (
            <button id="btn-create-wallet" className="button" onClick={handleCreateWallet}>
              Create Wallet
            </button>
          )}
        </section>

        {/* ── 2. KYC ── */}
        <section className="card">
          <h3>2 · KYC</h3>
          {!kyc ? (
            <button
              id="btn-start-kyc"
              className="button"
              disabled={!wallet || loading === "kyc-start"}
              onClick={handleStartKyc}
            >
              {loading === "kyc-start" ? "Starting…" : "Start KYC"}
            </button>
          ) : (
            <div>
              <p className="muted">
                Session: <span className="mono">{kyc.sessionId.slice(0, 18)}…</span>
              </p>
              <p className="muted">Prompt: {kyc.challenge.prompts[0]}</p>
              <p className="muted score-row">
                Liveness: <span className="badge ok">{kyc.livenessScore}</span>
                Deepfake: <span className="badge ok">{String(kyc.passedDeepfake)}</span>
                Device: <span className="badge ok">{String(kyc.deviceAttestation)}</span>
              </p>
              {!kyc.result ? (
                <button
                  id="btn-submit-kyc"
                  className="button"
                  disabled={loading === "kyc-submit"}
                  onClick={handleSubmitKyc}
                >
                  {loading === "kyc-submit" ? "Submitting…" : "Submit Liveness"}
                </button>
              ) : (
                <p className={`badge large ${kyc.result.passed ? "ok" : "fail"}`}>
                  KYC: {kyc.result.kycStatus.toUpperCase()}
                </p>
              )}
            </div>
          )}
        </section>

        {/* ── 3. VC Issuance ── */}
        <section className="card">
          <h3>3 · VC Issuance</h3>
          {!kycPassed && (
            <p className="muted">Complete KYC first to unlock VC issuance.</p>
          )}
          <button
            id="btn-issue-vc"
            className="button"
            disabled={!kycPassed || loading === "vc-issue"}
            onClick={handleIssueVc}
          >
            {loading === "vc-issue" ? "Issuing…" : "Issue VC"}
          </button>
          {vc && (
            <>
              <p className="badge ok small">✓ VC issued</p>
              <textarea readOnly value={JSON.stringify(vc, null, 2)} />
            </>
          )}
        </section>

        {/* ── 4. ZKP Proof ── */}
        <section className="card">
          <h3>4 · ZKP Proof</h3>
          <button
            id="btn-gen-proof"
            className="button"
            disabled={!wallet || loading === "zkp-gen"}
            onClick={handleGenerateProof}
          >
            {loading === "zkp-gen" ? "Generating…" : "Generate Mock Proof"}
          </button>
          {zkp && (
            <>
              <p className="badge ok small">✓ Proof generated</p>
              <textarea readOnly value={JSON.stringify(zkp, null, 2)} />
            </>
          )}
        </section>

        {/* ── 5. Bank Verification ── */}
        <section className="card">
          <h3>5 · Bank Verification</h3>
          <div className="kpi">
            <button
              id="btn-verify-vc"
              className="button"
              disabled={!vc || loading === "vc-verify"}
              onClick={handleVerifyVc}
            >
              {loading === "vc-verify" ? "Verifying…" : "Verify VC"}
            </button>
            <button
              id="btn-verify-zkp"
              className="button secondary"
              disabled={!zkp || loading === "zkp-verify"}
              onClick={handleVerifyProof}
            >
              {loading === "zkp-verify" ? "Verifying…" : "Verify ZKP"}
            </button>
            <button
              id="btn-graph-check"
              className="button"
              disabled={!wallet || loading === "graph-check"}
              onClick={handleGraphCheck}
            >
              {loading === "graph-check" ? "Checking…" : "Fraud Check"}
            </button>
          </div>

          {verification && (
            <div className="verify-results">
              {verification.vcValid !== undefined && (
                <div className="result-row">
                  <span>VC Signature</span>
                  <span className={`badge ${verification.vcValid ? "ok" : "fail"}`}>
                    {verification.vcValid ? "✓ Valid" : "✗ Invalid"}
                  </span>
                  {verification.vcReason && (
                    <span className="muted small">{verification.vcReason}</span>
                  )}
                </div>
              )}
              {verification.subjectDid && (
                <div className="result-row">
                  <span>Subject DID</span>
                  <span className="mono small">{verification.subjectDid}</span>
                </div>
              )}
              {verification.zkpValid !== undefined && (
                <div className="result-row">
                  <span>ZKP Age Proof</span>
                  <span className={`badge ${verification.zkpValid ? "ok" : "fail"}`}>
                    {verification.zkpValid ? "✓ Valid" : "✗ Invalid"}
                  </span>
                  {verification.zkpReason && (
                    <span className="muted small">{verification.zkpReason}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {graph && (
            <div className="verify-results">
              <div className="result-row">
                <span>Fraud Risk</span>
                <span className={`badge ${graph.safe ? "ok" : "fail"}`}>
                  {(graph.riskScore * 100).toFixed(0)}%
                </span>
              </div>
              <div className="result-row">
                <span>Flags</span>
                <span className="muted">{graph.flags.join(", ") || "none"}</span>
              </div>
            </div>
          )}
        </section>

        {/* ── 6. QR Share ── */}
        <section className="card">
          <h3>6 · QR Share</h3>
          {vc ? (
            <>
              <QRCodeCanvas value={JSON.stringify({ vc, zkp })} size={180} />
              <p className="muted small">Scan to share VC + proof</p>
            </>
          ) : (
            <p className="muted">Issue a VC to generate a shareable QR code.</p>
          )}
        </section>
      </div>
    </div>
  );
}
