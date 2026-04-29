import nacl from "tweetnacl";
import naclUtil from "tweetnacl-util";

const WALLET_KEY = "fintech_wallet";

export function createWallet() {
  const keyPair = nacl.sign.keyPair();
  const did = `did:example:${naclUtil.encodeBase64(keyPair.publicKey).slice(0, 16)}`;
  const wallet = {
    did,
    publicKey: naclUtil.encodeBase64(keyPair.publicKey),
    secretKey: naclUtil.encodeBase64(keyPair.secretKey),
    vcs: [],
    proofs: []
  };
  localStorage.setItem(WALLET_KEY, JSON.stringify(wallet));
  return wallet;
}

export function getWallet() {
  const raw = localStorage.getItem(WALLET_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function saveWallet(wallet) {
  localStorage.setItem(WALLET_KEY, JSON.stringify(wallet));
}
