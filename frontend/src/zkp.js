export function buildMockProof({ isAdult }) {
  return {
    proof: {
      pi_a: ["1", "2"],
      pi_b: [["3", "4"], ["5", "6"]],
      pi_c: ["7", "8"]
    },
    publicSignals: [isAdult ? "1" : "0"]
  };
}
