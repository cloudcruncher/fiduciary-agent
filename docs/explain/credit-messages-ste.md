# Credit messages: original and ASD-STE100 rewrite

Source: `fiduciary/analysis/credit_affordability.py` (tier text) and `fiduciary/cli.py` (`cmd_credit` labels).
Rules applied: one idea per sentence, active voice, one word for one meaning, no jargon without a definition.

## Tier descriptions

### Tier 1 (score 85 to 100)
- **Original:** Exceptional underwriting profile. Minimal leverage, strong cash-flow surplus, clean credit hygiene. Eligible for the most competitive mortgage rates and high-credit limit facilities.
- **STE:** Your finances are very strong. You owe little. You have money left each month. You pay on time. Lenders will offer you their best rates and high limits.

### Tier 2 (score 70 to 84)
- **Original:** Solid credit profile. High probability of approval with standard high-street lenders (Barclays, NatWest, Santander). Minor optimizations available.
- **STE:** Your finances are good. Most high-street banks will probably approve you. You can still improve a few things.

### Tier 3 (score 50 to 69)
- **Original:** Moderate risk factors detected (e.g. active BNPL or elevated debt service). An automated mortgage underwriter may request manual wage slips or debt clearance.
- **STE:** A lender can see some risk. For example, you use buy-now-pay-later, or your debt payments are high. The lender can ask for your payslips. The lender can ask you to pay off debt first.

### Tier 4 (score below 50)
- **Original:** Subprime or distressed indicators detected (overdraft dependency, returned items, or high leverage). Significant risk of automated credit rejection.
- **STE:** A lender can see serious risk. You rely on your overdraft, a payment failed, or you owe a lot. A lender will probably refuse your application.

## `./f credit` labels

| Original | STE |
|---|---|
| Borrowing Readiness (Underwriter View) | Can you borrow? How a lender sees you |
| Uncommitted monthly income | Money left each month after bills and debt |
| Debt-to-income | Share of income that goes to debt |
| Fixed needs (housing, bills, essentials) | Fixed costs (home, bills, food) |
| Contractual debt / BNPL | Debt payments, including buy-now-pay-later |
| Underwriter Risk Flags | Warning signs a lender looks for |
| Overdraft reliance: Yes | You use your overdraft every month: Yes |
| Electoral roll: NOT registered | Voter register: you are not on it. Register to vote. Lenders use it to check who you are. |
| Stress Tests | What if something goes wrong? |
| Survival months | Months you can last on essentials only |

## Findings

- The original uses six words that need a definition for most readers: underwriter, leverage, hygiene, facilities, subprime, DTI. Each STE version removes them or explains them.
- The STE versions are about the same length. They use more, shorter sentences.
- One loss: "underwriter" is the term lenders and mortgage brokers use. Keep it once in a help or glossary text so users can match it with what a broker tells them.
- Not applied to code. This file is a proposal. Applying it means editing the strings in two files.
