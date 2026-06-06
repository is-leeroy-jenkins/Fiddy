# Accessibility

This page describes the accessibility posture and manual validation checklist for the Fiddy
prototype.

Fiddy supports reviewer accessibility through Simple Mode, high-contrast mode, large-text mode,
keyboard-oriented workflow guidance, visible reviewer actions, and non-hover mismatch explanations.

Accessibility validation should be performed in the browser because Streamlit renders the final
interactive controls at runtime.

## Accessibility Scope

The Fiddy prototype should support:

* Simple reviewer workflow.
* High-contrast display mode.
* Large-text display mode.
* Keyboard navigation.
* Visible focus indicators.
* Keyboard activation of primary controls.
* Reviewer guidance that does not depend only on mouse hover.
* Download controls reachable by keyboard.
* Results that remain readable in high-contrast and large-text modes.

## Reviewer Workflow

The Simple Mode workflow should remain short and predictable:

```text
Upload application data and label artwork
        ↓
Run verification
        ↓
Review results and download outputs
```

Simple Mode should hide technical controls such as worker count and SLA tuning.

Advanced Mode may expose technical details for diagnostics, testing, and acceptance review.

## Accessibility Features

| Feature              | Purpose                                                           |
| -------------------- | ----------------------------------------------------------------- |
| Simple Mode          | Reduces screen complexity for routine review.                     |
| Advanced Mode        | Preserves diagnostic access for technical users.                  |
| High Contrast        | Improves readability for users who need stronger visual contrast. |
| Large Text           | Increases text and control size.                                  |
| Keyboard Guidance    | Explains how to move through the interface without a mouse.       |
| Reviewer Action Text | Makes mismatch guidance visible without requiring hover.          |
| Download Buttons     | Provides keyboard-reachable report export controls.               |

## Keyboard Controls

Users should be able to operate the primary workflow with standard keyboard controls.

| Key           | Expected Behavior                                    |
| ------------- | ---------------------------------------------------- |
| `Tab`         | Move forward through controls.                       |
| `Shift + Tab` | Move backward through controls.                      |
| `Enter`       | Activate focused buttons or selected controls.       |
| `Space`       | Activate focused buttons or toggles where supported. |

## Manual Accessibility Checklist

The checklist below should be validated in a browser before stakeholder demonstration.

| ID       | Check                                         | Expected Result                                                                                                     |
| -------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| A11Y-001 | High Contrast Mode Available                  | Controls and text remain readable with strong contrast.                                                             |
| A11Y-002 | Large Text Mode Available                     | Text and controls are larger without hiding required workflow controls.                                             |
| A11Y-003 | Keyboard Focus Visible                        | A visible focus outline appears on active controls.                                                                 |
| A11Y-004 | Upload Controls Reachable by Keyboard         | Manifest and artwork upload controls can be reached without a mouse.                                                |
| A11Y-005 | Run Verification Button Reachable by Keyboard | The Run Verification button can be reached without a mouse.                                                         |
| A11Y-006 | Run Verification Button Activates by Keyboard | Verification starts by pressing Enter or Space when the button is focused.                                          |
| A11Y-007 | Backward Keyboard Navigation Works            | Shift + Tab moves focus backward through prior controls.                                                            |
| A11Y-008 | Simple Mode Uses Short Workflow               | The reviewer can complete upload, run, review/download.                                                             |
| A11Y-009 | Simple Mode Hides Technical Controls          | Worker count and SLA tuning controls are not visible in Simple Mode.                                                |
| A11Y-010 | Result Selector Reachable by Keyboard         | The result selector can be reached without a mouse.                                                                 |
| A11Y-011 | Mismatch Guidance Does Not Require Hover      | Explanation and reviewer action text are visible without mouse-only hover.                                          |
| A11Y-012 | Comparison Table Readable                     | Application value, extracted value, status, severity, confidence, explanation, and reviewer action remain readable. |
| A11Y-013 | Download Buttons Reachable by Keyboard        | Download controls can be reached without a mouse.                                                                   |
| A11Y-014 | Download Buttons Activate by Keyboard         | Download controls activate with Enter or Space where supported by the browser.                                      |

## Validation Status Values

Use the following values when recording manual accessibility results:

| Status           | Meaning                                                             |
| ---------------- | ------------------------------------------------------------------- |
| `Pass`           | The item was tested and worked as expected.                         |
| `Fail`           | The item was tested and did not work as expected.                   |
| `Not Tested`     | The item has not yet been tested.                                   |
| `Not Applicable` | The item does not apply to the current workflow or browser context. |

## Accessibility Evidence

Fiddy includes a reusable checklist model in:

```text
src/accessibility_checklist.py
```

That module can generate checklist records suitable for display, documentation, or export.

The checklist supports:

* Item identifiers.
* Categories.
* Test names.
* Test procedures.
* Expected results.
* Status values.
* Tester notes.
* Evaluation timestamps.

## Recommended Browser Validation

Perform accessibility validation in the same browser and deployment mode expected for demonstration.

Recommended validation environments:

* Local Streamlit run.
* Local Docker container.
* Azure-hosted container.

At minimum, validate:

1. Normal display mode.
2. High Contrast mode.
3. Large Text mode.
4. Simple Mode.
5. Advanced Mode.
6. Keyboard-only navigation.
7. Result review.
8. Report download controls.

## Simple Mode Expectations

Simple Mode should show only the controls necessary for routine review.

Expected Simple Mode behavior:

* Manifest upload is visible.
* Label artwork upload is visible.
* Run Verification is visible.
* Clear Results is visible.
* Results and downloads are visible after processing.
* Worker controls are hidden.
* SLA tuning controls are hidden.
* Advanced OCR diagnostics are hidden.
* Methodology and technical safeguards are hidden unless explicitly expanded or shown in Advanced
  Mode.

## Advanced Mode Expectations

Advanced Mode may show:

* Manifest preview.
* Uploaded-file preview.
* Match diagnostics.
* Worker controls.
* SLA seconds.
* OCR diagnostics.
* Image-quality diagnostics.
* Rule details.
* Performance timing.
* Downloadable outputs.

## Known Limitations

Accessibility depends partly on Streamlit and browser-rendered controls. Fiddy can improve styling,
guidance, layout, visible text, and workflow design, but keyboard behavior should still be validated
in the target browser.

Mouse-hover-only content should not be the only way to understand a mismatch. Fiddy should show
mismatch explanations and reviewer actions in visible table columns or detail panels.

## Pre-Demonstration Accessibility Checklist

Before demonstration:

* Enable Simple Mode and complete a review.
* Enable High Contrast and inspect upload, results, and downloads.
* Enable Large Text and inspect upload, results, and downloads.
* Navigate the main workflow using Tab and Shift + Tab.
* Activate Run Verification using keyboard controls.
* Confirm mismatch explanation and reviewer action are visible.
* Confirm download controls can be reached by keyboard.
* Confirm the page remains readable after results are generated.
