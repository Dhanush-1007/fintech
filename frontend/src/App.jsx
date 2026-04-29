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
  const [notes, setNotes] = useState("{");

  useEffect(() => {
    const existing = getWallet();
    if (existing) {
      setWallet(existing);
    }
  }, []);

  function handleCreateWallet() {
    const created = createWallet();
    setWallet(created);
  }

  async function handleStartKyc() {
    setError(null);
    const response = await apiClient.startKyc();
    setKyc({ ...response, livenessScore: 0.86, passedDeepfake: true, deviceAttestation: true });
  }

  async function handleSubmitKyc() {
    if (!kyc || !wallet) return;
    const response = await apiClient.verifyKyc({
      sessionId: kyc.sessionId,
      did: wallet.did,
      livenessScore: kyc.livenessScore,
      passedDeepfake: kyc.passedDeepfake,
      deviceAttestation: kyc.deviceAttestation
    });
    setKyc({ ...kyc, result: response });
  }

  async function handleIssueVc() {
    if (!wallet) return;
    const claims = {
      name: "Verified User",
      dob: "2002-01-01",
      kycStatus: "verified",
      incomeBand: ">10L"
    };
    const response = await apiClient.issueVc({ did: wallet.did, claims });
    setVc(response.vc);
    const updated = { ...wallet, vcs: [...wallet.vcs, response.vc] };
    saveWallet(updated);
    setWallet(updated);
  }

  async function handleVerifyVc() {
    if (!vc) return;
    const response = await apiClient.verifyVc({ vc });
    setVerification({ vcValid: response.valid });
  }

  async function handleGenerateProof() {
    const proof = buildMockProof({ isAdult: true });
    setZkp(proof);
    const updated = { ...wallet, proofs: [...wallet.proofs, proof] };
    saveWallet(updated);
    setWallet(updated);
  }

  async function handleVerifyProof() {
    if (!wallet || !zkp) return;
    const response = await apiClient.verifyZkp({
      did: wallet.did,
      proof: zkp.proof,
      publicSignals: zkp.publicSignals
    });
    setVerification((prev) => ({ ...prev, zkpValid: response.valid }));
  }

  async function handleGraphCheck() {
    if (!wallet) return;
    const response = await apiClient.graphCheck({ did: wallet.did });
    setGraph(response);
  }

  return (
    <div className="app">
      <section className="hero">
        <h1>Portable Identity Wallet</h1>
        <p className="muted">
          Full mock flow: wallet -> KYC -> VC -> ZKP -> bank verification
        </p>
        {error && <p className="muted">{error}</p>}
      </section>

      <div className="grid">
        <section className="card">
          <h3>Wallet</h3>
          {wallet ? (
            <div>
              <p className="muted">DID: {wallet.did}</p>
              <p className="muted">VCs: {wallet.vcs.length}</p>
              <p className="muted">Proofs: {wallet.proofs.length}</p>
            </div>
          ) : (
            <button className="button" onClick={handleCreateWallet}>
              Create Wallet
            </button>
          )}
        </section>

        <section className="card">
          <h3>KYC</h3>
          {!kyc ? (
            <button className="button" onClick={handleStartKyc}>
              Start KYC
            </button>
          ) : (
            <div>
              <p className="muted">Session: {kyc.sessionId}</p>
              <p className="muted">Prompt: {kyc.challenge.prompts[0]}</p>
              <button className="button secondary" onClick={handleSubmitKyc}>
                Submit Mock Liveness
              </button>
              {kyc.result && <p className="muted">Status: {kyc.result.kycStatus}</p>}
            </div>
          )}
        </section>

        <section className="card">
          <h3>VC Issuance</h3>
          <button className="button" onClick={handleIssueVc}>
            Issue VC
          </button>
          {vc && (
            <textarea readOnly value={JSON.stringify(vc, null, 2)} />
          )}
        </section>

        <section className="card">
          <h3>ZKP Proof</h3>
          <button className="button" onClick={handleGenerateProof}>
            Generate Mock Proof
          </button>
          {zkp && (
            <textarea readOnly value={JSON.stringify(zkp, null, 2)} />
          )}
        </section>

        <section className="card">
          <h3>Bank Verification</h3>
          <div className="kpi">
            <button className="button" onClick={handleVerifyVc}>Verify VC</button>
            <button className="button secondary" onClick={handleVerifyProof}>Verify ZKP</button>
            <button className="button" onClick={handleGraphCheck}>Graph Check</button>
          </div>
          {verification && (
            <p className="muted">
              VC valid: {String(verification.vcValid)} | ZKP valid: {String(verification.zkpValid)}
            </p>
          )}
          {graph && (
            <p className="muted">
              Risk: {graph.riskScore} | Flags: {graph.flags.join(", ") || "none"}
            </p>
          )}
        </section>

        <section className="card">
          <h3>QR Share</h3>
          {vc ? (
            <QRCodeCanvas value={JSON.stringify({ vc, zkp })} size={180} />
          ) : (
            <p className="muted">Issue VC to generate QR</p>
          )}
        </section>
      </div>
    </div>
  );
}
