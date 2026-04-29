# ZKP Demo

This folder contains a simple Circom circuit to prove age >= 18.

## Setup

Download a trusted powers of tau file and place it in `ptau/` as `powersOfTau28_hez_final_10.ptau`.

## Commands

```
npm install
npm run compile
npm run setup
npm run contribute
npm run vkey
npm run witness
npm run prove
npm run verify
```

After generating `proof.json` and `public.json`, you can send them to the backend `/api/zkp/verify` endpoint.
