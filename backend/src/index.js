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

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

app.get("/api/issuer", (req, res) => {
  res.json(getIssuerInfo());
});

app.post("/api/kyc/start", async (req, res) => {
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
    [sessionId, challenge]
  );

  res.json({ sessionId, challenge });
});

app.post("/api/kyc/verify", async (req, res) => {
  const { sessionId, did, livenessScore, passedDeepfake, deviceAttestation } = req.body;

  if (!sessionId || !did) {
    return res.status(400).json({ error: "sessionId and did are required" });
  }

  const passed = livenessScore >= 0.7 && passedDeepfake === true && deviceAttestation === true;

  await query("UPDATE kyc_sessions SET status = $1, did = $2 WHERE id = $3", [
    passed ? "verified" : "rejected",
    did,
    sessionId
  ]);

  await query(
    "INSERT INTO users (did, kyc_status) VALUES ($1, $2) ON CONFLICT (did) DO UPDATE SET kyc_status = EXCLUDED.kyc_status",
    [did, passed ? "verified" : "rejected"]
  );

  res.json({ passed, kycStatus: passed ? "verified" : "rejected" });
});

app.post("/api/vc/issue", async (req, res) => {
  const { did, claims } = req.body;

  if (!did || !claims) {
    return res.status(400).json({ error: "did and claims are required" });
  }

  const issuer = getIssuerInfo();
  const payload = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    type: ["VerifiableCredential", "KYCVerification"],
    issuer: issuer.did,
    issuanceDate: new Date().toISOString(),
    credentialSubject: {
      id: did,
      ...claims
    }
  };

  const signature = signCredential(payload);
  const vc = {
    payload,
    proof: {
      type: "Ed25519Signature2020",
      created: new Date().toISOString(),
      verificationMethod: issuer.publicKey,
      signature
    }
  };

  await query(
    "INSERT INTO vcs (id, did, payload, signature) VALUES ($1, $2, $3, $4)",
    [uuidv4(), did, payload, signature]
  );

  res.json({ vc });
});

app.post("/api/vc/verify", (req, res) => {
  const { vc } = req.body;
  if (!vc?.payload || !vc?.proof?.signature) {
    return res.status(400).json({ error: "vc payload and signature are required" });
  }

  const valid = verifyCredential(vc.payload, vc.proof.signature);
  res.json({ valid });
});

app.post("/api/zkp/verify", async (req, res) => {
  const { did, proof, publicSignals } = req.body;
  if (!did || !proof || !publicSignals) {
    return res.status(400).json({ error: "did, proof, and publicSignals are required" });
  }

  const isAdult = Array.isArray(publicSignals) && publicSignals.includes("1");

  await query(
    "INSERT INTO proofs (id, did, public_signals, proof) VALUES ($1, $2, $3, $4)",
    [uuidv4(), did, publicSignals, proof]
  );

  res.json({ valid: isAdult, reason: isAdult ? "ok" : "not-adult" });
});

app.post("/api/graph/check", (req, res) => {
  const { did } = req.body;
  const riskScore = did ? Math.min(0.2 + (did.length % 7) * 0.1, 0.9) : 0.8;

  res.json({ riskScore, flags: riskScore > 0.6 ? ["cluster-risk"] : [] });
});

app.listen(PORT, () => {
  console.log(`Backend listening on ${PORT}`);
});
