# Evaluation Plan

## 1. Why Eval exists
This project must prove that AI classification is useful, not merely plausible-looking.

## 2. Gold set
Create a random sample of 100 Issues.

Human fields:
- issue_type
- category
- surface
- platform
- severity

Store:
- human label
- AI label
- reviewer note
- disagreement type

## 3. Metrics

### Category
- accuracy
- per-class precision/recall if sample size allows
- confusion matrix

### Surface / Platform
- accuracy
- unknown-rate

### Severity
Use Human-AI agreement rather than pretending an objective ground truth exists.
Also inspect critical disagreements.

## 4. Error taxonomy
Classify errors:
- parser failure
- ambiguous issue
- taxonomy mismatch
- insufficient context
- model reasoning error
- mixed/multi-topic issue

## 5. Iteration
Never tune against all 100 and then report the same 100 as unbiased validation.
Preferred:
- 60 development examples
- 40 holdout examples

If time is limited, disclose that the evaluation is an internal validation set rather than a formal benchmark.

## 6. Efficiency baseline
Manually process the same fixed batch before using Signal.

Record:
- start/end time
- items completed
- categories produced
- pain points found

Then run Signal and record:
- pipeline runtime
- human review time
- agreement
- correction count

Do not pre-fill “90% faster” or any other claim.

## 7. Portfolio reporting
Report:
- sample size
- metric definition
- actual result
- known limitations
- exact date/version of analysis pipeline
