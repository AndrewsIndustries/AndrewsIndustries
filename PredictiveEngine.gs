/**
 * PredictiveEngine.gs
 * Logic for calculating stock performance forecasts and risk ratings.
 */

function calculateAlphaForecast(price, sma50, sma200, high52, low52, beta) {
  if (typeof price !== 'number' || typeof sma50 !== 'number') return { score: 50, forecast: "Neutral", risk: "Low" };

  let score = 50;
  let outlook = "Neutral Outlook";
  
  // 1. Momentum Analysis (SMA Stacking)
  if (price > sma50 && sma50 > sma200) {
    score += 25;
    outlook = "Bullish - Momentum Expansion";
  } else if (price < sma50 && sma50 < sma200) {
    score -= 25;
    outlook = "Bearish - Structural Decline";
  }

  // 2. Mean Reversion Target
  // If significantly below 52w high, calculate a recovery target (50% retracement)
  let target = price;
  if (high52 > price) {
    target = price + ((high52 - price) * 0.382); // Fibonacci 38.2% retracement target
  }

  // 3. Risk Rating based on Beta
  let riskLevel = "Medium";
  if (typeof beta === 'number') {
    if (beta > 1.4) riskLevel = "High Volatility";
    else if (beta < 0.8) riskLevel = "Stable/Low Risk";
    
    // Adjust score based on risk vs trend
    if (beta > 1 && score > 50) score += 5; // Aggressive growth
  }

  // 4. Overextension Check
  if (price > high52 * 0.98) {
    outlook = "Overextended - Potential Pullback";
    score -= 10;
  }

  return {
    sentiment: Math.min(100, Math.max(0, score)),
    forecast: outlook,
    target: target.toFixed(2),
    risk: riskLevel
  };
}