pragma circom 2.1.6;

include "circomlib/circuits/comparators.circom";

// Proves age >= 18 without revealing the exact age.
component main = AgeCheck();

component AgeCheck() {
    signal input age;
    signal output isAdult;

    component ge = GreaterEqThan(8);
    ge.in[0] <== age;
    ge.in[1] <== 18;

    isAdult <== ge.out;
}
