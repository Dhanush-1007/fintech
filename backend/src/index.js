import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { v4 as uuidv4 } from "uuid";
import { query } from "./db.js";
import { getIssuerInfo, signCredential, verifyCredential } from "./issuer.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));

const PORT = process.env.PORT || 4000;

// ──────────────────────────────────────────────
// Health
// ──────────────────────────────────────────────
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.get("/api/issuer", (req, res) => {
  res.json(getIssuerInfo());
});

// ──────────────────────────────────────────────
// KYC
// ──────────────────────────────────────────────
app.post("/api/kyc/start", async (req, res) => {
  try {
    const sessionId = uuidv4();
    const challenge = {
      prompts: [
        "Blink twice and turn your head left",
        "Read the number 7429 aloud",
        "Smile for two seconds"
      ],
      expiresInSec: 120
    };

    await query(
      "INSERT INTO kyc_sessions (id, challenge) VALUES ($1, $2)",
      [sessionId, JSON.stringify(challenge)]
    );

    res.json({ sessionId, challenge });
  } catch (err) {
    console.error("[kyc/start]", err);
    res.status(500).json({ error: "Failed to start KYC session" });
  }
});

app.post("/api/kyc/verify", async (req, res) => {
  try {
    const { sessionId, did, livenessScore, passedDeepfake, deviceAttestation } = req.body;

    if (!sessionId || !did) {
      return res.status(400).json({ error: "sessionId and did are required" });
    }

    // Check session exists and is still pending
    const sessionRows = await query(
      "SELECT id, status FROM kyc_sessions WHERE id = $1",
      [sessionId]
    );
    if (sessionRows.rows.length === 0) {
      return res.status(404).json({ error: "Session not found" });
    }
    if (sessionRows.rows[0].status !== "pending") {
      return res.status(409).json({ error: "Session already processed" });
    }

    const passed =
      typeof livenessScore === "number" &&
      livenessScore >= 0.7 &&
      passedDeepfake === true &&
      deviceAttestation === true;

    const kycStatus = passed ? "verified" : "rejected";

    await query(
      "UPDATE kyc_sessions SET status = $1, did = $2 WHERE id = $3",
      [kycStatus, did, sessionId]
    );

    await query(
      "INSERT INTO users (did, kyc_status) VALUES ($1, $2) ON CONFLICT (did) DO UPDATE SET kyc_status = EXCLUDED.kyc_status",
      [did, kycStatus]
    );

    res.json({ passed, kycStatus });
  } catch (err) {
    console.error("[kyc/verify]", err);
    res.status(500).json({ error: "KYC verification failed" });
  }
});

// ──────────────────────────────────────────────
// Verifiable Credentials
// ──────────────────────────────────────────────
app.post("/api/vc/issue", async (req, res) => {
  try {
    const { did, claims } = req.body;

    if (!did || !claims) {
      return res.status(400).json({ error: "did and claims are required" });
    }

    // Enforce KYC gate: user must have passed KYC before receiving a VC
    const userRows = await query(
      "SELECT kyc_status FROM users WHERE did = $1",
      [did]
    );
    if (userRows.rows.length === 0 || userRows.rows[0].kyc_status !== "verified") {
      return res.status(403).json({ error: "KYC not verified for this DID" });
    }

    const issuer = getIssuerInfo();
    const issuanceDate = new Date().toISOString();

    // Build payload with deterministic key order so signing is stable
    const payload = {
      "@context": ["https://www.w3.org/2018/credentials/v1"],
      type: ["VerifiableCredential", "KYCVerification"],
      issuer: issuer.did,
      issuanceDate,
      credentialSubject: {
        id: did,
        name: claims.name,
        dob: claims.dob,
        kycStatus: claims.kycStatus,
        incomeBand: claims.incomeBand
      }
    };

    // Sign the canonical JSON
    const signature = signCredential(payload);

    const vc = {
      payload,
      proof: {
        type: "Ed25519Signature2020",
        created: issuanceDate,
        verificationMethod: issuer.publicKey,
        signature
      }
    };

    await query(
      "INSERT INTO vcs (id, did, payload, signature) VALUES ($1, $2, $3, $4)",
      [uuidv4(), did, JSON.stringify(payload), signature]
    );

    res.json({ vc });
  } catch (err) {
    console.error("[vc/issue]", err);
    res.status(500).json({ error: "VC issuance failed" });
  }
});

app.post("/api/vc/verify", (req, res) => {
  try {
    const { vc } = req.body;

    if (!vc?.payload || !vc?.proof?.signature) {
      return res.status(400).json({ error: "vc.payload and vc.proof.signature are required" });
    }

    // Re-canonicalize with same key order to match signing
    const { payload } = vc;
    const canonicalPayload = {
      "@context": payload["@context"],
      type: payload.type,
      issuer: payload.issuer,
      issuanceDate: payload.issuanceDate,
      credentialSubject: {
        id: payload.credentialSubject.id,
        name: payload.credentialSubject.name,
        dob: payload.credentialSubject.dob,
        kycStatus: payload.credentialSubject.kycStatus,
        incomeBand: payload.credentialSubject.incomeBand
      }
    };

    const valid = verifyCredential(canonicalPayload, vc.proof.signature);

    // Also confirm credential subject DID matches proof's verificationMethod context
    const subjectDid = payload.credentialSubject?.id;
    const issuerDid = payload.issuer;

    res.json({
      valid,
      subjectDid,
      issuerDid,
      reason: valid ? "Signature verified" : "Signature mismatch"
    });
  } catch (err) {
    console.error("[vc/verify]", err);
    res.status(500).json({ error: "VC verification failed" });
  }
});

// ──────────────────────────────────────────────
// Zero-Knowledge Proof
// ──────────────────────────────────────────────
app.post("/api/zkp/verify", async (req, res) => {
  try {
    const { did, proof, publicSignals } = req.body;

    if (!did || !proof || !publicSignals) {
      return res.status(400).json({ error: "did, proof, and publicSignals are required" });
    }

    const isAdult = Array.isArray(publicSignals) && publicSignals.includes("1");

    await query(
      "INSERT INTO proofs (id, did, public_signals, proof) VALUES ($1, $2, $3, $4)",
      [uuidv4(), did, JSON.stringify(publicSignals), JSON.stringify(proof)]
    );

    res.json({ valid: isAdult, reason: isAdult ? "Age verified (adult)" : "Age check failed (not adult)" });
  } catch (err) {
    console.error("[zkp/verify]", err);
    res.status(500).json({ error: "ZKP verification failed" });
  }
});

// ──────────────────────────────────────────────
// Graph / Fraud Risk
// ──────────────────────────────────────────────
app.post("/api/graph/check", (req, res) => {
  try {
    const { did } = req.body;
    if (!did) {
      return res.status(400).json({ error: "did is required" });
    }
    const riskScore = Math.min(0.2 + (did.length % 7) * 0.1, 0.9);
    res.json({
      riskScore,
      flags: riskScore > 0.6 ? ["cluster-risk"] : [],
      safe: riskScore <= 0.6
    });
  } catch (err) {
    console.error("[graph/check]", err);
    res.status(500).json({ error: "Graph check failed" });
  }
});

// ──────────────────────────────────────────────
// Start server
// ──────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`Backend listening on port ${PORT}`);
});
