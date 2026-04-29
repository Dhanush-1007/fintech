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

export function signCredential(payload) {
  const message = naclUtil.decodeUTF8(JSON.stringify(payload));
  const signature = nacl.sign.detached(message, issuerKeys.secretKey);
  return naclUtil.encodeBase64(signature);
}

export function verifyCredential(payload, signatureBase64) {
  const message = naclUtil.decodeUTF8(JSON.stringify(payload));
  const signature = naclUtil.decodeBase64(signatureBase64);
  return nacl.sign.detached.verify(message, signature, issuerKeys.publicKey);
}
