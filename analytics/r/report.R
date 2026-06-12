# HypeX — Statistical analysis of the hype market (base R, no external packages)
#
#   1. ARIMA forecast of the HypeX market index (order chosen by AIC grid search)
#   2. GARCH(1,1) conditional volatility, fit by maximum likelihood from scratch
#   3. Engle-Granger cointegration test for a candidate pairs-trade
#
# Run from repo root:  Rscript analytics/r/report.R

ex <- "analytics/data/exports"; if (!dir.exists(ex)) ex <- "../data/exports"
fig <- "analytics/reports/figures"; if (!dir.exists(fig)) fig <- "../reports/figures"
rep_dir <- dirname(fig)

mi <- read.csv(file.path(ex, "market_index.csv"))
mi <- mi[mi$track == "synthetic", ]
mi <- mi[order(mi$date), ]
idx <- mi$index_level
cat(sprintf("HypeX index: %d days, level %.1f -> %.1f\n", length(idx), idx[1], tail(idx, 1)))

## 1. ARIMA --------------------------------------------------------------
best <- NULL; best_aic <- Inf; ord <- c(0, 0, 0)
for (p in 0:3) for (d in 0:1) for (q in 0:3) {
  fit <- tryCatch(arima(idx, order = c(p, d, q)), error = function(e) NULL)
  if (!is.null(fit) && is.finite(fit$aic) && fit$aic < best_aic) {
    best_aic <- fit$aic; best <- fit; ord <- c(p, d, q)
  }
}
H <- 30
fc <- predict(best, n.ahead = H)
cat(sprintf("Best ARIMA(%d,%d,%d)  AIC=%.1f  forecast[+30d]=%.1f\n",
            ord[1], ord[2], ord[3], best_aic, tail(fc$pred, 1)))

png(file.path(fig, "arima_forecast.png"), width = 1000, height = 500, res = 110)
hn <- 180; xs <- (length(idx) - hn + 1):length(idx); fx <- (length(idx) + 1):(length(idx) + H)
plot(xs, idx[xs], type = "l", xlim = c(xs[1], length(idx) + H),
     ylim = range(idx[xs], fc$pred + 2 * fc$se, fc$pred - 2 * fc$se),
     xlab = "day", ylab = "index level",
     main = sprintf("HypeX index — ARIMA(%d,%d,%d) 30-day forecast", ord[1], ord[2], ord[3]))
polygon(c(fx, rev(fx)), c(fc$pred + 1.96 * fc$se, rev(fc$pred - 1.96 * fc$se)),
        col = rgb(1, 0, 0, 0.12), border = NA)
lines(fx, fc$pred, col = "blue", lwd = 2)
abline(v = length(idx), lty = 3, col = "gray")
dev.off()

## 2. GARCH(1,1) by MLE --------------------------------------------------
r <- diff(log(idx)) * 100  # daily log-returns in %
garch_nll <- function(par, r) {
  o <- par[1]; a <- par[2]; b <- par[3]
  if (o <= 0 || a < 0 || b < 0 || a + b >= 1) return(1e10)
  n <- length(r); s2 <- numeric(n); s2[1] <- var(r)
  for (t in 2:n) s2[t] <- o + a * r[t - 1]^2 + b * s2[t - 1]
  0.5 * sum(log(2 * pi) + log(s2) + r^2 / s2)
}
opt <- optim(c(var(r) * 0.1, 0.08, 0.90), garch_nll, r = r,
             method = "Nelder-Mead", control = list(maxit = 3000))
o <- opt$par[1]; a <- opt$par[2]; b <- opt$par[3]
n <- length(r); s2 <- numeric(n); s2[1] <- var(r)
for (t in 2:n) s2[t] <- o + a * r[t - 1]^2 + b * s2[t - 1]
cat(sprintf("GARCH(1,1): omega=%.4f alpha=%.3f beta=%.3f persistence(a+b)=%.3f\n", o, a, b, a + b))

png(file.path(fig, "garch_vol.png"), width = 1000, height = 430, res = 110)
plot(sqrt(s2 * 365), type = "l", col = "darkred", xlab = "day", ylab = "annualized vol (%)",
     main = sprintf("HypeX index — GARCH(1,1) conditional volatility (persistence %.2f)", a + b))
dev.off()

## 3. Engle-Granger cointegration ---------------------------------------
adf_t <- function(y, lags = 1) {
  y <- as.numeric(y); dy <- diff(y); m <- length(dy)
  df <- data.frame(dy = dy, ylag = y[1:m], trend = 1:m)
  if (lags > 0) for (i in 1:lags) df[[paste0("dl", i)]] <- c(rep(NA, i), dy[1:(m - i)])
  df <- df[complete.cases(df), ]
  summary(lm(dy ~ ., data = df))$coefficients["ylag", "t value"]
}
pr <- read.csv(file.path(ex, "prices_all.csv"))
pr <- pr[pr$track == "synthetic", ]
w <- reshape(pr[, c("date", "canonical_id", "price")], idvar = "date",
             timevar = "canonical_id", direction = "wide")
w <- w[order(w$date), ]; pm <- as.matrix(w[, -1])
# pick the most-correlated pair (best pairs-trade candidate)
cc <- cor(pm); diag(cc) <- 0
ij <- which(cc == max(cc), arr.ind = TRUE)[1, ]
a_id <- sub("price.", "", colnames(pm)[ij[1]]); b_id <- sub("price.", "", colnames(pm)[ij[2]])
ya <- pm[, ij[1]]; yb <- pm[, ij[2]]
spread <- residuals(lm(ya ~ yb))
adf_spread <- adf_t(spread, lags = 1)
coint <- adf_spread < -3.4
cat(sprintf("Most-correlated pair: %s ~ %s (corr=%.2f)  ADF(spread)=%.2f  cointegrated=%s\n",
            a_id, b_id, max(cc), adf_spread, coint))

## findings --------------------------------------------------------------
writeLines(c(
  "# R statistical findings",
  "",
  sprintf("- **ARIMA** order (by AIC): (%d,%d,%d), AIC %.1f; 30-day index forecast %.1f",
          ord[1], ord[2], ord[3], best_aic, tail(fc$pred, 1)),
  sprintf("- **GARCH(1,1)**: omega=%.4f, alpha=%.3f, beta=%.3f, persistence(alpha+beta)=%.3f",
          o, a, b, a + b),
  sprintf("- **Cointegration** (Engle-Granger, %s vs %s, corr %.2f): ADF(spread)=%.2f -> %s",
          a_id, b_id, max(cc), adf_spread, ifelse(coint, "cointegrated (tradeable pair)",
                                                  "not cointegrated (no stable pair)")),
  ""
), file.path(rep_dir, "r_findings.md"))
cat("Wrote arima_forecast.png, garch_vol.png, r_findings.md\n")
