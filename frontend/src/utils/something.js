// Random utils

export const weightedRandom = (w0, w1, w2) => {
    return w0 * Math.random() + w1 * Math.random() + w2 * Math.random();
};

export const diffSquared = (predicted, actual) => {
    return Math.pow(predicted - actual, 2);
};

/**
 * For 
 * a 
 *  afa
 * ffae
 * fa
 * f fa
 * f afae fa
 * faf
 * aef
 * aef -> (a, b) => { a +- b = -b/2}
 * 
 * .. return Error;
 * aef
 * af
 * a faejfaoiejea f
 * afae
 * f 
 */