import nacl from "tweetnacl";
import naclUtil from "tweetnacl-util";

const ISSUER_DID = process.env.ISSUER_DID || "did:example:issuer";
const ISSUER_SEED = process.env.ISSUER_SEED || "issuer-demo-seed-00000000000000000000000000000000";

function seedToKeyPair(seed) {
  const seedBytes = naclUtil.decodeUTF8(seed.padEnd(32, "0").slice(0, 32));
  return nacl.sign.keyPair.fromSeed(seedBytes);
}

const issuerKeys = seedToKeyPair(ISSUER_SEED);

export function getIssuerInfo() {
  return {
    did: ISSUER_DID,
    publicKey: naclUtil.encodeBase64(issuerKeys.publicKey)
  };
}

/**
 * Canonicalize a JS object for signing by doing a deterministic JSON
 * serialisation (sorted keys, no extra whitespace).  This ensures the
 * same bytes are produced on both the signing side and the verify side
 * regardless of the property-insertion order of the V8 runtime.
 */
function canonicalize(obj) {
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) {
    return JSON.stringify(obj);
  }
  const keys = Object.keys(obj).sort();
  const parts = keys.map((k) => `${JSON.stringify(k)}:${canonicalize(obj[k])}`);
  return `{${parts.join(",")}}`;
}

export function signCredential(payload) {
  const canonical = canonicalize(payload);
  const message = naclUtil.decodeUTF8(canonical);
  const signature = nacl.sign.detached(message, issuerKeys.secretKey);
  return naclUtil.encodeBase64(signature);
}

export function verifyCredential(payload, signatureBase64) {
  const canonical = canonicalize(payload);
  const message = naclUtil.decodeUTF8(canonical);
  const signature = naclUtil.decodeBase64(signatureBase64);
  return nacl.sign.detached.verify(message, signature, issuerKeys.publicKey);
}
