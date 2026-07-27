# VoiceGuard — Product Architecture Document

**Version:** 1.0  
**Date:** 2026-07-25  
**Classification:** Internal — Product & Engineering Reference  
**Status:** Approved for Engineering Handoff

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision](#2-product-vision)
3. [Target Users & Personas](#3-target-users--personas)
4. [User Journey](#4-user-journey)
5. [Complete Sitemap](#5-complete-sitemap)
6. [Screen Specifications](#6-screen-specifications)
7. [Navigation Architecture](#7-navigation-architecture)
8. [Feature Hierarchy](#8-feature-hierarchy)
9. [Application Modules](#9-application-modules)
10. [Component Inventory](#10-component-inventory)
11. [Design System Guidelines](#11-design-system-guidelines)
12. [User Flows](#12-user-flows)
13. [Error Handling Strategy](#13-error-handling-strategy)
14. [Empty States](#14-empty-states)
15. [Loading States](#15-loading-states)
16. [Success States](#16-success-states)
17. [Non-Functional Requirements](#17-non-functional-requirements)
18. [Product Roadmap](#18-product-roadmap)
19. [Final Architectural Recommendations](#19-final-architectural-recommendations)

---

## 1. Executive Summary

VoiceGuard is a free, enterprise-quality audio deepfake detection platform
that makes AI-powered voice authentication technology accessible to everyone
— from a journalist verifying a source recording to a cybersecurity team
screening inbound voice calls.

The core technical engine is a Light CNN (LCNN) model trained on the ASVspoof
2019 benchmark achieving 7.07% Equal Error Rate, outperforming the published
academic baseline. The model produces not just a verdict but a Grad-CAM
heatmap showing exactly which frequency regions drove the decision — a level
of explainability that most commercial tools do not offer.

This document defines the complete product architecture: every screen, every
user flow, every component, and every design decision. It serves as the single
source of truth for all engineering, design, and product work that follows.

**North Star Metric:** Number of scans completed per week.  
**Business Model:** Free. Monetization is out of scope for v1.  
**Launch Target:** A product that journalists, HR teams, and cybersecurity
professionals would trust and recommend — not a demo.

---

## 2. Product Vision

### Vision Statement

> "To make voice authenticity verification as fast and accessible as a
> Google search — available to anyone, trusted by professionals."

### Mission

Democratize access to audio deepfake detection technology that was previously
available only to well-funded research labs and enterprise security vendors.
Every person with a suspicious audio file should be able to get an honest,
explained answer in under 30 seconds, for free.

### Goals

**G1 — Accessibility**  
Any user — regardless of technical background — can complete an analysis
within 90 seconds of landing on the site for the first time.

**G2 — Trust**  
The platform communicates its limitations honestly. It never overstates
confidence. It explains what the model is detecting and where it may fail.
Professionals trust it because it is transparent.

**G3 — Speed**  
From file upload to result display: under 10 seconds on standard hardware.
The UI never leaves a user waiting without feedback.

**G4 — Explainability**  
Every result includes a plain-language explanation, a visual heatmap, and
raw technical scores. Casual users get the summary. Professionals can drill
into the details.

**G5 — Extensibility**  
The architecture supports future expansion: batch processing, API access,
team accounts, and new model versions — without requiring a UI redesign.

### Core Value Proposition

VoiceGuard answers the question "Is this voice real?" in three layers:

  LAYER 1 — Verdict      : Human or AI-Generated, with confidence percentage
  LAYER 2 — Explanation  : Plain-language description of what the model found
  LAYER 3 — Evidence     : Grad-CAM heatmap, raw scores, frequency analysis

No other free tool provides all three layers together.

### Future Expansion Opportunities

- Batch file processing (upload 100 files, get a CSV report)
- Browser extension (right-click any audio element on the web)
- API with key management (for developers integrating into their products)
- Team workspaces (shared scan history and report templates)
- Real-time stream analysis (for live call monitoring)
- Mobile app (iOS / Android native)
- Webhook integrations (Slack, email, SIEM platforms)

---

## 3. Target Users & Personas

### Persona 1 — Casual User / General Public

**Who:** Anyone who receives a suspicious voice message, hears a clip online,
or wants to verify a recorded call.

**Goals:** Get a quick, clear answer. Understand what it means. No jargon.

**Frustrations:** Complex tools, jargon-heavy interfaces, results with no
explanation, having to create an account just to try the product.

**VoiceGuard expectation:** Drop a file, get a verdict in plain English,
understand the confidence level. Should feel as simple as Google Translate.

**Key flow:** Landing → Try without account → Upload → Instant result.

---

### Persona 2 — Student / Researcher

**Who:** University students studying ML, NLP, or cybersecurity. Academic
researchers benchmarking deepfake detection tools.

**Goals:** Understand how the detection works. See the technical details.
Reference this tool in research or coursework.

**Frustrations:** Tools that hide their methodology. No access to raw scores.
No citation information.

**VoiceGuard expectation:** Access to raw softmax scores, Grad-CAM heatmaps
with technical annotation, information about the model architecture, EER
benchmark results. History that can be exported for analysis.

**Key flow:** Sign up → Run multiple scans → Export results as CSV/JSON.

---

### Persona 3 — Journalist / Fact Checker

**Who:** Investigative journalists at news organizations. Fact-checkers
verifying viral audio clips. Editors making publication decisions.

**Goals:** Quickly determine whether a leaked or viral audio clip is authentic.
Get something printable — a report they can reference in their story or
submit to an editor.

**Frustrations:** Tools with no accountability trail. No explanation of what
was found. No way to export findings. Generic verdicts with no nuance.

**VoiceGuard expectation:** A timestamped, exportable report with the file
metadata, verdict, confidence score, and Grad-CAM visualization. Something
that documents the analysis for editorial review. Honesty about model
limitations (they will ask "what could this miss?").

**Key flow:** Sign up → Upload → View result → Download PDF report.

---

### Persona 4 — Recruiter / HR Professional

**Who:** Corporate recruiters screening candidates for roles that involve
voice interaction. HR teams investigating grievances involving recorded audio.

**Goals:** Verify that a submitted voice sample, interview recording, or
reported incident audio is genuine. Fast turnaround. Defensible output.

**Frustrations:** Needing IT approval for new enterprise tools. Uploading
sensitive personnel audio to unknown services. No audit trail.

**VoiceGuard expectation:** Clear privacy messaging. Explicit statement that
audio is not stored beyond processing. Simple interface requiring no training.
Report they can attach to an HR file. Potentially: a "verified by VoiceGuard"
badge for documentation.

**Key flow:** Sign up → Upload recording → View result → Export PDF.

---

### Persona 5 — Content Creator

**Who:** YouTubers, podcasters, musicians who want to verify their own voice
samples were not cloned. Digital rights management.

**Goals:** Confirm that audio circulating online attributed to them was
actually recorded by them. Protect their voice identity.

**Frustrations:** No tools designed for their use case. Most tools focus on
detecting fakes, not self-verification.

**VoiceGuard expectation:** Can verify their own recordings as bonafide.
Can detect cloned versions of their voice. Shareable result link to share
on social media.

**Key flow:** Upload → Get bonafide verdict → Share link publicly.

---

### Persona 6 — Cybersecurity Analyst

**Who:** Security operations team member. Threat intelligence analyst.
Incident responder investigating a vishing attack.

**Goals:** Analyze suspicious voice recordings from phishing calls. Batch
process multiple files. Integrate findings into incident reports.

**Frustrations:** Tools with no technical depth. No API access. Results that
cannot be integrated into SIEM workflows.

**VoiceGuard expectation:** Raw technical scores accessible. Batch upload
capability (v2). Export to JSON for SIEM integration. Model version and
confidence thresholds documented. Understands what "7.07% EER" means.

**Key flow:** API access (v2) or bulk upload → Batch results → JSON export.

---

### Persona 7 — Law Enforcement / Digital Forensics

**Who:** Police digital forensics unit. Evidence authentication specialists.
Legal defense and prosecution teams.

**Goals:** Authenticate voice recordings submitted as evidence. Generate a
defensible report that can be submitted to court.

**Frustrations:** Tools with no audit trail. No methodology documentation.
Opaque AI decisions with no explainability.

**VoiceGuard expectation:** Detailed report with model version, analysis
methodology, confidence scores, and Grad-CAM evidence. Timestamp of analysis.
SHA-256 hash of the analyzed file (proves the file was not altered post-
analysis). Clear limitation disclosures.

**Key flow:** Sign up → Upload → Full technical report with file hash.

---

### Persona 8 — Product Developer / API Consumer

**Who:** Developer building a product that needs voice authentication or
content moderation.

**Goals:** Programmatic access. Predictable API. Good documentation.
Reasonable rate limits.

**VoiceGuard expectation:** REST API with API key. OpenAPI specification.
SDK or cURL examples. Status page for uptime. Developer-focused documentation.

**Key flow:** API Docs page → Generate API key → Integrate in 30 minutes.

---

## 4. User Journey

### Journey A — First-Time Guest (Casual User)

```
[1] Discovers VoiceGuard via social, search, or referral
      ↓
[2] Lands on Landing Page — sees headline, understands product instantly
      ↓
[3] Clicks "Try it free — no account needed"
      ↓
[4] Redirected to New Scan page with guest session
      ↓
[5] Uploads file or records audio via microphone
      ↓
[6] Sees Processing state with progress indicator (~3–8 seconds)
      ↓
[7] Receives Result page: Verdict + Confidence + Grad-CAM
      ↓
[8] Reads plain-language explanation below the verdict
      ↓
[9] Sees call-to-action: "Save this result — create a free account"
      ↓
[10] Chooses: Sign Up (saves result) or Leave
      ↓
[If Sign Up] → Email verification → Onboarding → Dashboard
              → Migrated guest scan appears in History
```

### Journey B — Returning Registered User

```
[1] Returns to VoiceGuard directly or via bookmark
      ↓
[2] Lands on Login page (or is auto-logged-in via session)
      ↓
[3] Arrives at Dashboard — sees scan count, recent activity
      ↓
[4] Clicks "New Scan" (primary CTA in dashboard)
      ↓
[5] Uploads or records audio
      ↓
[6] Sees Processing state
      ↓
[7] Receives full Result with history auto-saved
      ↓
[8] Downloads PDF report (if needed)
      ↓
[9] Returns to Dashboard or navigates to History
      ↓
[10] Views a previous scan from History → Scan Detail page
      ↓
[11] Shares scan result link or re-downloads report
```

### Journey C — Professional (Journalist / Analyst)

```
[1] Signs up with work email
      ↓
[2] Completes onboarding — selects "Professional" usage context
      ↓
[3] Dashboard shows advanced metrics panel (unlocked by context)
      ↓
[4] Uploads multiple files in succession
      ↓
[5] Views each result with full technical breakdown
      ↓
[6] Exports individual PDF reports per scan
      ↓
[7] Returns to History page — uses search and date filter
      ↓
[8] Finds a past scan → Views detail → Re-downloads report
      ↓
[9] Submits feedback if result seems incorrect
      ↓
[10] Receives model improvement notification (v2 release)
```

---

## 5. Complete Sitemap

```
VoiceGuard
│
├── PUBLIC (unauthenticated)
│   ├── S01  Landing Page
│   ├── S02  Sign Up
│   ├── S03  Login
│   ├── S04  Email Verification
│   ├── S05  Forgot Password
│   ├── S20  Shared Scan Result (public permalink)
│   ├── S21  404 — Not Found
│   └── S22  Service Error / Maintenance
│
└── APP (authenticated + guest session)
    ├── S06  Onboarding Wizard (first-run only)
    ├── S07  Dashboard
    ├── S08  New Scan — Upload / Record
    ├── S09  Scan Processing
    ├── S10  Scan Result
    ├── S11  History — All Scans
    ├── S12  Scan Detail (archived)
    ├── S13  Notifications
    ├── S14  Help Center
    ├── S15  Help Article
    ├── S16  Feedback / Report
    ├── S17  Profile
    ├── S18  Account Settings
    └── S19  Appearance & Preferences
```

Total: 22 screens. Each justified by a distinct user need.

---

## 6. Screen Specifications

---

### S01 — Landing Page

**Purpose:** Convert visitors into users. Communicate the product value
proposition within 5 seconds. Provide a frictionless entry to try the product.

**Who uses it:** Everyone — first-time visitors, returning users who are
not logged in, users who received a shared link.

**Navigation Entry Points:**
- Direct URL / homepage
- Google / social media search
- Shared link click (redirects here for non-users)
- Referral links

**Navigation Exit Points:**
- S02 Sign Up (primary CTA)
- S03 Login (secondary CTA)
- S08 New Scan (Try without account — tertiary CTA)

**Primary Actions:**
- "Get Started Free" → S02 Sign Up
- "Try without an account" → S08 New Scan (guest mode)

**Secondary Actions:**
- Login → S03
- Scroll to How It Works section
- Scroll to Use Cases section

**Important UI Components:**
- Hero section: headline, sub-headline, CTA buttons, hero visual (animated
  waveform or spectrogram visualization — purely decorative)
- "How It Works" — 3-step diagram: Upload → AI Analysis → Verdict
- Use Cases carousel: Journalists / HR / Cybersecurity / Researchers
- Stats bar: "X scans completed" · "7.07% EER" · "Free forever"
- Technology trust section: model name, benchmark comparison, methodology link
- Testimonials or "Trusted by" section (placeholder in v1, real in v2)
- Footer: About, Privacy Policy, Terms of Service, Help Center, API Docs

**Required Data:** Public, no authentication. Live scan counter (optional,
shows platform activity).

**Design Notes:**
- Above the fold must answer: What is this? Who is it for? Can I try it now?
- The hero visual should show a real output screenshot (verdict + Grad-CAM)
  rather than an abstract graphic — demonstrates value immediately
- Dark mode is default; light mode respects system preference
- Mobile: single column, CTA buttons stacked, hero image below the fold

---

### S02 — Sign Up

**Purpose:** Account creation. Lowest possible friction while collecting
only the minimum data needed.

**Who uses it:** New visitors converting from landing page or after a guest scan.

**Navigation Entry Points:**
- S01 Landing Page CTA
- S08 New Scan (post-scan CTA for guests)
- S03 Login page "Don't have an account" link

**Navigation Exit Points:**
- S04 Email Verification (after successful form submission)
- S03 Login (if user already has account)
- S08 New Scan (back to guest)

**Primary Actions:**
- Submit registration form
- Continue with Google / GitHub OAuth

**Secondary Actions:**
- Link to S03 Login
- View Privacy Policy / Terms of Service

**Important UI Components:**
- Email input + Password input + Confirm Password
- Show/hide password toggles
- Password strength meter
- OAuth buttons (Google, GitHub — for v1 at minimum Google)
- Terms of Service consent checkbox
- Inline validation on every field (no submit-and-pray)
- Progress indicator: "Create account → Verify email → Start using VoiceGuard"

**Required Data:** email, password. Name is optional at registration —
collected during onboarding instead (lower friction).

**Validation Rules:**
- Email: valid format, not already registered
- Password: minimum 8 characters, 1 uppercase, 1 number
- Confirm password: exact match
- All inline, immediate — no waiting until submit

---

### S03 — Login

**Purpose:** Authenticate existing users. Secondary entry for guest-to-
account conversion.

**Who uses it:** Any returning user.

**Navigation Entry Points:**
- S01 Landing Page header
- Deep links from email (notifications, reports)
- Session expiry redirects
- S02 Sign Up "Already have an account" link

**Navigation Exit Points:**
- S07 Dashboard (successful login)
- S05 Forgot Password
- S02 Sign Up

**Primary Actions:**
- Email + password login
- OAuth login (Google / GitHub)
- "Remember me" toggle

**Secondary Actions:**
- Forgot Password → S05
- Create account → S02

**Important UI Components:**
- Email + Password inputs
- OAuth buttons
- "Remember me" checkbox
- Forgot password link
- Inline validation

**Design Notes:**
- Auto-focus on email field
- Show helpful error states: "Incorrect password" vs "Account not found"
- Detect and offer OAuth if email was originally registered via OAuth

---

### S04 — Email Verification

**Purpose:** Verify email ownership before granting full account access.

**Who uses it:** New registrants who registered via email/password.

**Navigation Entry Points:**
- Automatically shown after S02 Sign Up form submission

**Navigation Exit Points:**
- S06 Onboarding (after successful verification)
- Resend email (same page, success toast)

**Primary Actions:**
- Enter 6-digit verification code (sent to email)
- Resend code (rate-limited to 1/minute)

**Secondary Actions:**
- Change email address (returns to S02)

**Important UI Components:**
- 6-digit OTP input (split into 6 boxes, auto-advance on digit entry)
- "Check your email" illustration
- Countdown timer for resend (60 seconds)
- Plain text fallback link in email for accessibility

**Design Notes:**
- Auto-paste from clipboard on mobile (detects OTP SMS/email)
- If user clicks the magic link in the email instead of typing code,
  verification completes and redirects directly to S06 Onboarding

---

### S05 — Forgot Password

**Purpose:** Account recovery via email.

**Who uses it:** Users who forgot their password.

**Navigation Entry Points:**
- S03 Login page "Forgot password" link
- Direct link from password reset email

**Navigation Exit Points:**
- S03 Login (after password reset success)
- S02 Sign Up (if user does not have account)

**Primary Actions:**
- Submit email for reset link
- Submit new password (second step, accessed from email link)

**Important UI Components:**
- Step 1: Email input + submit button + confirmation message
- Step 2: New password + confirm password + submit (accessed via email link)
- Success state with redirect countdown

---

### S06 — Onboarding Wizard

**Purpose:** First-run experience. Personalize the product to the user's
context without friction. Collect usage context (persona) to customize
dashboard defaults.

**Who uses it:** Every new registered user, exactly once.

**Navigation Entry Points:**
- S04 Email Verification (auto-redirect after verification)
- S03 Login for newly verified accounts

**Navigation Exit Points:**
- S07 Dashboard (after completing or skipping onboarding)

**Primary Actions:**
- Progress through 3 wizard steps
- Skip onboarding (link available at all steps)

**Wizard Steps:**

  Step 1 — Welcome
    "Welcome to VoiceGuard. Let's get you set up."
    Display name field (optional — just first name)
    Large "Let's go →" CTA

  Step 2 — How will you use VoiceGuard?
    Single-select cards:
      • Personal / Curiosity
      • Journalist / Fact-checking
      • HR / Recruiting
      • Cybersecurity / Research
      • Content Creator
      • Developer
    This selection surfaces relevant dashboard features and help content.
    Skip option available.

  Step 3 — First scan invitation
    "Your account is ready. Want to run your first scan now?"
    Large primary CTA: "Start my first scan →" → S08
    Secondary: "Explore the dashboard first" → S07

**Important UI Components:**
- Step indicator (dots or numbered steps at top)
- Progress percentage or "Step X of 3"
- Skip link always visible
- Animated transitions between steps (not jarring — subtle slide)
- Each step fits on one screen — no scrolling

**Design Notes:**
- Completion of step 2 silently stores usage_context in the user profile.
  This drives which help articles are prioritized and which dashboard
  panels are shown by default.
- Never force completion. "Skip" is always available.

---

### S07 — Dashboard

**Purpose:** The authenticated home. Provides a meaningful overview of
the user's scan activity, quick access to start a new scan, and easy
navigation to history and notifications. The Dashboard is the anchor —
every other app screen can return here.

**Who uses it:** All authenticated users on every session.

**Navigation Entry Points:**
- Any screen via logo click
- Any screen via "Dashboard" sidebar link
- Post-login redirect

**Navigation Exit Points:**
- S08 New Scan (primary CTA)
- S11 History (activity feed, "View all" link)
- S12 Scan Detail (clicking any scan in recent activity)
- S13 Notifications

**Primary Actions:**
- Start New Scan → S08
- View recent scan result → S12

**Secondary Actions:**
- View all scans → S11
- Clear all / Delete scan (from recent activity items)

**Important UI Components:**

  Hero CTA Card (full-width at top)
    "Analyze an audio file"
    Upload dropzone + Microphone record button embedded directly
    — This is the #1 action; make it impossible to miss

  Stats Row (3 cards)
    Total Scans | Human Detected | AI Detected
    (Numbers are honest engagement metrics, not vanity)

  Recent Scans (last 5, list format)
    Each row: file name · verdict badge · confidence · timestamp · actions
    "View all →" link at bottom

  Scan Breakdown Chart (if ≥5 scans)
    Simple donut or bar: Human vs AI ratio over time
    Empty state below 5 scans: replaced with "Run 5 scans to see your
    history trends"

  Quick Tip Card
    Rotates every session. Personalized to onboarding context.
    Example: "Did you know? Neural codec attacks are harder to detect.
    Here's what the model can and cannot detect."

**Required Data:**
- User scan history (count, recent 5)
- Aggregated stats (human/AI counts)
- User name (for greeting)

**Design Notes:**
- Dashboard must be meaningful on first visit (empty state) and on the
  100th visit (real data). Both states designed explicitly.
- The embedded upload zone at the top of the dashboard is intentional —
  the primary action should not require navigation. Users should never
  need to click "New Scan" if they just want to drag-and-drop a file.

---

### S08 — New Scan — Upload / Record

**Purpose:** The primary product action. Accept an audio file or live
recording and submit it for analysis.

**Who uses it:** All users. The most-used screen in the application.

**Navigation Entry Points:**
- S07 Dashboard primary CTA
- S07 Dashboard embedded upload zone
- Sidebar "New Scan" link
- S06 Onboarding step 3 CTA
- Global "+" quick action button (top navigation)

**Navigation Exit Points:**
- S09 Scan Processing (on submit)
- S07 Dashboard (cancel)

**Primary Actions:**
- Drop file onto dropzone (drag and drop)
- Click dropzone to open file picker
- Click "Record from microphone" to switch to record mode
- Submit for analysis

**Secondary Actions:**
- Clear selected file
- Switch between Upload and Record tabs
- Preview audio before submitting (inline audio player)

**Important UI Components:**

  Mode Toggle: Upload | Record
    Tab-style toggle at top

  Upload Mode:
    Large dropzone (dashed border)
      Icon + "Drop your audio file here"
      "or click to browse"
      Supported formats list: WAV, FLAC, MP3, M4A, OGG, AIFF
      Max file size: 10 MB
    Selected file preview card:
      File name · file size · detected format · duration
      Inline audio player (play / pause / scrub)
      "Remove" button (×)
    Primary CTA: "Analyze" (disabled until file selected)

  Record Mode:
    Microphone permission prompt (first time)
    Record button (large, circular, pulsing red when active)
    Live waveform visualizer (animated during recording)
    Timer: 00:00 / 04:00 max (matches model's 4-second window)
    Stop button
    Playback of recording before submit
    Re-record option
    Primary CTA: "Analyze Recording" (enabled after recording)

  Format / Limitation Notice (collapsed by default, expandable):
    "The model analyzes the first 4 seconds of audio."
    "Files under 0.5 seconds may produce unreliable results."
    "Telephone-bandwidth audio (8kHz) may affect accuracy."

**Required Data:**
- Supported MIME types / extensions list
- File size limit (10MB)
- Recording duration limit (4 seconds, soft — longer allowed, truncated)

**Design Notes:**
- Upload and Record should feel like two modes of the same action,
  not two separate features. Use a smooth tab transition.
- The file preview with the inline audio player is critical — users
  must be able to verify they uploaded the correct file before submitting.
- The "Analyze" button is the only exit from this screen (besides cancel).
  It should be large, prominent, and visually active.
- Microphone permission errors should be handled gracefully: explain
  how to grant permission with browser-specific instructions.

---

### S09 — Scan Processing

**Purpose:** Provide meaningful feedback during the AI analysis. Never
leave the user staring at a blank screen.

**Who uses it:** All users immediately after submitting a scan.

**Navigation Entry Points:**
- S08 New Scan (automatic redirect on submit)

**Navigation Exit Points:**
- S10 Scan Result (automatic on completion)
- S08 New Scan (cancel — with confirmation if > 2 seconds in)

**Primary Actions:**
- Wait (no user action required)
- Cancel analysis (secondary)

**Important UI Components:**

  Processing Card (centered, single focus)
    File name + format + duration (what is being analyzed)
    Animated spectrogram preview (blurred, loading shimmer effect)
    — Not the real spectrogram; a loading animation that looks like one
    — Sets correct expectation for what the result will look like

    Progress indicator: 3 animated steps
      Step 1: "Loading audio..." (0–20%)
      Step 2: "Extracting acoustic features..." (20–70%)
      Step 3: "Running AI analysis..." (70–100%)

    Time estimate: "Usually takes 3–8 seconds"

    Animated pulsing ring or waveform animation

  Cancel button (subtle, bottom of card)
    Confirmation dialog: "Cancel this analysis? Your file will be removed."

**Design Notes:**
- The 3 processing steps give the user a mental model of what the AI
  is doing. This increases perceived trust even if the steps are
  approximate visual representations of the actual pipeline.
- If processing takes longer than 15 seconds: show "Taking longer than
  usual..." message with support link.
- On completion, auto-navigate to S10. No extra click required.
- If user navigates away and returns: show "Your analysis is ready" banner.

---

### S10 — Scan Result

**Purpose:** The most important screen in the product. Deliver a clear,
explainable, actionable verdict. This is the moment VoiceGuard either
earns or loses user trust.

**Who uses it:** All users after every scan.

**Navigation Entry Points:**
- S09 Scan Processing (automatic on completion)
- S11 History (viewing a recent scan)
- S12 Scan Detail for newly completed scans

**Navigation Exit Points:**
- S08 New Scan ("Analyze another file")
- S11 History ("View all scans")
- S16 Feedback ("Report incorrect result")
- Shared link (social/copy)
- PDF download (opens download dialogue)

**Primary Actions:**
- Analyze another file → S08
- Download PDF report
- Copy shareable link

**Secondary Actions:**
- Report incorrect result → S16
- Save to history (for guests: creates account CTA)
- View technical details (expandable section)
- Share on Twitter/LinkedIn (social proof sharing)

**Layout Structure (vertical scroll, single column, max-width 760px):**

  ── SECTION 1: Verdict ──────────────────────────────────────────────

  Verdict Card (full-width, bold)
    HUMAN VOICE        (green, #30D158)
    AI-GENERATED VOICE (red, #FF453A)
    UNCERTAIN          (amber, #FF9F0A — for confidence 50–65%)

    Confidence percentage: e.g., "97.3% confidence"
    Confidence bar: horizontal gradient bar, filled to confidence %

    Plain-language summary (1–2 sentences):
      HUMAN:    "The acoustic patterns in this recording are consistent
                with natural human speech. No synthesis artifacts were
                detected in the frequency range the model analyzes."
      AI:       "This audio shows strong indicators of AI synthesis.
                The model detected characteristic patterns in the high-
                frequency range (4–8 kHz) commonly produced by neural
                vocoders."
      UNCERTAIN:"The model detected some patterns that could indicate AI
                synthesis, but confidence is below the reliable threshold.
                Treat this result with caution."

  ── SECTION 2: Confidence Breakdown ────────────────────────────────

  Two-bar breakdown card:
    Human probability:  [██████░░░░] 97.3%
    AI probability:     [░░░░░░████]  2.7%
    (Probabilities always sum to 100%)

  Model confidence note:
    "Confidence above 85%: High reliability"
    "Confidence 65–85%: Moderate reliability — consider additional review"
    "Confidence below 65%: Low reliability — do not rely on this result alone"

  ── SECTION 3: Analysis Visualization ──────────────────────────────

  Two-panel spectrogram card (the Grad-CAM visualization)
    Left: Acoustic Fingerprint (mel-spectrogram, greyscale)
    Right: Model Attention (Grad-CAM overlay on spectrogram)

    Each panel:
      Title
      Axis labels (Time / Frequency)
      Color legend for the attention map

    Plain-language caption below the visualization:
      "The highlighted regions show which frequency ranges influenced
      the AI's decision. Strong activation at 4–8 kHz (high frequencies)
      is characteristic of vocoder synthesis artifacts."

  Audio player (inline, minimal)
    Play / Pause · Scrub bar · Duration
    Synchronized highlight: the waveform position moves as audio plays
    (Note: spectrogram sync is v2 feature)

  ── SECTION 4: Limitations Notice ──────────────────────────────────

  Expandable "About This Result" card (collapsed by default)
    Model: LCNN — Light CNN trained on ASVspoof 2019 LA benchmark
    Overall EER: 7.07% (lower is better; 0% = perfect)
    Known Weakness: "Neural codec attacks (e.g., VALL-E style) are
    harder to detect. If the audio was generated by a modern end-to-end
    codec system, this model may not detect it reliably."
    Analyzed: [filename] · [duration] · [sample rate detected] · [date/time]
    File SHA-256: [hash] (for evidence chain-of-custody)

  ── SECTION 5: Actions ─────────────────────────────────────────────

  Primary:   [Analyze Another File]
  Secondary: [Download PDF Report]  [Copy Share Link]
  Tertiary:  [Report Incorrect Result]

**Required Data:**
- verdict: "bonafide" | "spoof"
- confidence: float 0–1
- scores: {bonafide: float, spoof: float}
- gradcam_image: base64 or URL
- mel_image: base64 or URL
- file_metadata: {name, size, duration, sample_rate, sha256}
- scan_id: UUID (for sharing and history)
- timestamp

**Design Notes:**
- The verdict card is the first thing the user sees. It must be
  immediately legible — no ambiguity about the color coding or label.
- The confidence bar should animate into place (fill from 0) — this
  creates a moment of anticipation that emphasizes the result.
- The Limitations Notice is always present. Trust is built by honesty.
  Hiding the model's weaknesses would undermine credibility with the
  professional users who matter most.
- The SHA-256 hash is critical for forensic/legal use cases. Compute it
  client-side before upload to ensure the original file is hashed.

---

### S11 — History — All Scans

**Purpose:** Browse, search, and manage all past scans. Serves both casual
users checking a few scans and professional users managing hundreds.

**Who uses it:** All authenticated users. Guests see a preview with a
"Create account to save results" CTA.

**Navigation Entry Points:**
- S07 Dashboard "View all" link
- Sidebar "History" link

**Navigation Exit Points:**
- S12 Scan Detail (clicking any row)
- S08 New Scan (primary CTA)
- S10 Result (if clicking a scan from the current session)

**Primary Actions:**
- Click any scan row → S12 Scan Detail
- Search scans by filename
- Filter by verdict, date range

**Secondary Actions:**
- Delete scan (single) with confirmation
- Select multiple → Bulk delete
- Export selected scans as CSV
- New Scan CTA (persistent in header)

**Important UI Components:**

  Search + Filter Bar (sticky)
    Search input: "Search by filename..."
    Filter chips: All · Human · AI-Generated · Uncertain
    Date range picker: Last 7 days / 30 days / All time / Custom
    Sort: Newest first / Oldest first / Confidence

  Scan Table / List
    Each row:
      File icon (by format) | Filename | Verdict badge | Confidence %
      Duration | Date | Actions (view, delete)
    Hoverable rows
    Selectable rows (checkbox appears on hover)
    Pagination: 20 per page with page numbers and "Show more"

  Bulk Action Bar (visible when rows selected)
    "X scans selected" | Delete selected | Export selected | Deselect all

**Design Notes:**
- Mobile: table collapses to card list (filename, verdict, date)
- Empty state: see Section 14

---

### S12 — Scan Detail (Archived Report)

**Purpose:** View the complete result of any past scan. Identical in
structure to S10 Scan Result but accessed from history. All information
is preserved exactly as it was at scan time.

**Who uses it:** All authenticated users reviewing past work.

**Navigation Entry Points:**
- S11 History (row click)
- Direct deep link / shared URL
- S07 Dashboard recent activity (row click)

**Navigation Exit Points:**
- S11 History (breadcrumb)
- S08 New Scan
- S16 Feedback
- PDF download

**Primary Actions:**
- Download PDF report
- Copy share link
- Delete scan (with confirmation)

**Secondary Actions:**
- Report incorrect result → S16
- Re-analyze (re-submits same file — requires file to still be cached;
  v2 feature if files are not permanently stored)

**Layout:**
- Identical to S10 Scan Result with additions:
  - Breadcrumb: Dashboard > History > [filename]
  - Scan metadata card at top: Analyzed [date] · Scan ID [UUID]
  - Delete button in header (with confirmation modal)

**Design Notes:**
- This screen is the basis for the shareable link. The public view
  (S20 Shared Scan Result) shows the same layout without the authenticated
  actions (delete, re-analyze).

---

### S13 — Notifications

**Purpose:** Surface system alerts, model update announcements, scan
completions (for async processing), and product news.

**Who uses it:** All authenticated users.

**Navigation Entry Points:**
- Notification bell icon in top navigation
- Deep link from notification emails

**Navigation Exit Points:**
- S12 Scan Detail (clicking a scan notification)
- S07 Dashboard
- Any relevant target page

**Primary Actions:**
- Mark all as read
- Click notification to navigate to relevant page

**Secondary Actions:**
- Delete individual notification
- Notification preferences → S18 Account Settings

**Important UI Components:**
- Notification list: grouped by date (Today, Yesterday, Older)
- Each item: icon · title · description · timestamp · read/unread state
- Unread indicator: blue dot
- Empty state: "You're all caught up" illustration

**Notification Types:**
  INFO     — Model version update available
  SUCCESS  — "Your scan is ready" (for future async processing)
  WARNING  — "Result has low confidence — review recommended"
  SYSTEM   — Maintenance announcements, privacy policy updates

---

### S14 — Help Center

**Purpose:** Self-service knowledge base. Reduces support burden and
builds user confidence.

**Who uses it:** All users. Personalized content by onboarding context.

**Navigation Entry Points:**
- Sidebar "Help" link
- "?" icon in top navigation
- Error pages (contextual help links)
- Empty states (contextual help links)

**Navigation Exit Points:**
- S15 Help Article (clicking any article)
- S16 Feedback (if user can't find answer)
- S07 Dashboard

**Primary Actions:**
- Search knowledge base
- Browse article categories
- Click to read an article

**Secondary Actions:**
- "Didn't find your answer?" → S16 Feedback

**Content Categories:**
  Getting Started
    - What is VoiceGuard?
    - How do I upload a file?
    - What formats are supported?
    - How do I record audio?
    - How do I read the result?

  Understanding Results
    - What does the confidence score mean?
    - What is Grad-CAM?
    - Why is my result "Uncertain"?
    - Can I trust a 99% confidence result?
    - What is EER and why does it matter?

  Model Limitations
    - What types of AI audio can this detect?
    - What are neural codec attacks?
    - Known failure cases (A17 / neural codecs)
    - Why am I getting unexpected results?

  Privacy & Security
    - Is my audio stored?
    - Who can see my results?
    - How are results shared?

  Account & Settings
    - How do I change my email?
    - How do I delete my account?
    - How do I export my data?

  For Professionals
    - Using VoiceGuard for forensic analysis
    - Exporting evidence-grade reports
    - Understanding the SHA-256 file hash
    - API access (coming soon)

**Design Notes:**
- Article cards should show read time estimates
- Search should work in real-time with highlighted matches
- Featured articles based on the user's onboarding context
- Link to S16 Feedback is always present ("Can't find what you need?")

---

### S15 — Help Article

**Purpose:** Individual knowledge base article. Answering a specific user question in depth.

**Who uses it:** Users seeking answers to specific questions.

**Navigation Entry Points:**
- S14 Help Center article click
- Search results
- Contextual links in error states and tooltips

**Navigation Exit Points:**
- S14 Help Center (breadcrumb)
- Related articles
- S16 Feedback ("Was this helpful? No → Give feedback")

**Important UI Components:**
- Article title + read time estimate
- Last updated date
- Article body (markdown rendered)
- "Was this helpful?" binary feedback (thumbs up/down)
- Related articles (2–3 recommended)
- "Still need help? Contact us" → S16 Feedback link
- Table of contents (for long articles, sticky sidebar on desktop)

---

### S16 — Feedback / Report

**Purpose:** Allow users to report incorrect results, suggest improvements,
or submit general feedback. This is critical for ML model improvement.

**Who uses it:** Any user who believes a result is wrong or wants to provide
input.

**Navigation Entry Points:**
- S10 Scan Result "Report incorrect result" link
- S12 Scan Detail same link
- S14 Help Center "Can't find your answer?"
- Footer link

**Navigation Exit Points:**
- Thank-you state (same page)
- S07 Dashboard
- S11 History

**Primary Actions:**
- Submit feedback form

**Important UI Components:**
  Feedback Type selector:
    • Incorrect result (verdict was wrong)
    • Missing feature / suggestion
    • Bug report
    • Other

  If "Incorrect result":
    Auto-populates with the scan context:
      Scan ID (read-only) | Filename | Model verdict | User believes: Human / AI
    Description field: "What makes you believe the result is incorrect?"
    Optional: additional context about the recording's origin

  If other types:
    Description field (required, 10–1000 chars)
    Email override field (if user wants follow-up)

  Submission CTA: "Submit Feedback"

**Important Design Note:**
Incorrect result reports are the primary mechanism for building a
human-labeled correction dataset. The scan_id, model verdict, and
user-reported ground truth should be stored in a feedback table. This
is the foundation of model improvement in v2. This feedback pathway
is one of the most strategically important features in the product.

---

### S17 — Profile

**Purpose:** Public-facing user identity. In v1, minimal — name and
avatar only. In v2, may include public scan stats for users who opt in.

**Who uses it:** The user managing their own profile.

**Navigation Entry Points:**
- User menu (avatar click) → "Profile"
- S18 Account Settings sidebar link

**Navigation Exit Points:**
- S18 Account Settings
- S07 Dashboard

**Important UI Components:**
- Avatar (uploadable in v2; initials-based placeholder in v1)
- Display name + username
- Member since date
- Scan statistics (if user opted to share)
- Link to S18 Account Settings

---

### S18 — Account Settings

**Purpose:** Manage account information, privacy controls, notification
preferences, and data management.

**Who uses it:** All authenticated users.

**Navigation Entry Points:**
- User menu "Settings"
- S17 Profile "Edit" button

**Navigation Exit Points:**
- S07 Dashboard
- Logout (clears session → S01 Landing or S03 Login)

**Sections:**

  Profile
    Display name · Email (change requires re-verification)
    Password change (shows current password + new password + confirm)
    Avatar upload (v2)

  Notifications
    Email notifications: scan complete / model updates / product news
    In-app notifications: same categories with per-type toggles
    Notification frequency: real-time / daily digest / weekly digest

  Privacy & Data
    "Audio files are never permanently stored after analysis."
    (This is a promise made in the UI — architectural constraint)
    Export my data (JSON download of all scan metadata, no audio)
    Delete all scan history (with confirmation: "This cannot be undone")
    Delete account (soft delete → 30-day recovery window)

  Usage Context (from onboarding)
    Edit: re-shows the persona selection from S06 Onboarding
    This affects dashboard layout and help article prioritization

---

### S19 — Appearance & Preferences

**Purpose:** Personalize the visual experience and workflow preferences.

**Who uses it:** Power users who want to customize their experience.

**Navigation Entry Points:**
- S18 Account Settings sidebar sub-section
- Top navigation theme toggle (quick toggle for dark/light)

**Navigation Exit Points:**
- S18 Account Settings
- S07 Dashboard

**Settings:**
  Theme: System Default · Light · Dark
  Language: English (v1 only; v2 adds localization)
  Result display:
    Show Grad-CAM visualization: On / Off
    Default expanded: Technical Details: On / Off
    Waveform player: Compact / Full
  Dashboard:
    Show quick stats: On / Off
    Default chart: Bar / Donut / Hidden

---

### S20 — Shared Scan Result (Public Permalink)

**Purpose:** Allow users to share a scan result with anyone — regardless
of whether they have a VoiceGuard account. This is a viral growth vector
and a trust demonstration.

**Who uses it:** Anyone who receives a shared link.

**Navigation Entry Points:**
- Shared URL from S10 or S12 "Copy link"
- Social media posts

**Navigation Exit Points:**
- S01 Landing Page "Get started free" CTA
- S02 Sign Up CTA

**Layout:**
- Identical to S10/S12 result display
- Header: "VoiceGuard Analysis" with branding
- All sections: verdict, confidence, Grad-CAM, metadata, limitations
- No authenticated actions (no delete, no re-analyze)
- Persistent bottom bar: "Analyze your own audio — Free, no account needed"
  → S08 New Scan (guest mode)

**Privacy Controls:**
- Links are unlisted (UUID in URL, not guessable)
- User can make scan private (link stops working) from S12
- Scans default to shareable but not publicly indexed
- Shared links expire after 90 days unless renewed

---

### S21 — 404 Not Found

**Purpose:** Recover gracefully when a user navigates to a non-existent
page or an expired shared link.

**Navigation Exit Points:**
- S07 Dashboard
- S08 New Scan
- S14 Help Center

**Important UI Components:**
- Clear headline: "Page not found"
- Sub-copy: "This link may have expired or the page was moved."
- Two CTA options: "Go to Dashboard" and "Analyze a file"
- VoiceGuard branding (minimal header/footer)

---

### S22 — Service Error / Maintenance

**Purpose:** Handle server errors and planned maintenance gracefully.

**Triggers:**
- 500 errors from the API
- 503 Service Unavailable
- Planned maintenance window (shows countdown if known)

**Important UI Components:**
- Clear messaging: "Something went wrong on our end"
- Retry button (for 500 errors)
- Maintenance message + estimated restoration time (for planned downtime)
- Status page link (future: status.voiceguard.com)

---

## 7. Navigation Architecture

### 7.1 Public Navigation (Unauthenticated)

```
[Logo]          [About]  [How It Works]  [Try Free →]  [Login]
```

- Transparent on landing page hero, solid on scroll
- Mobile: hamburger menu with same links in drawer
- "Try Free →" is the always-visible primary CTA
- Maximum 4 nav items (not cluttered)

### 7.2 Application Shell Navigation (Authenticated)

**Top Bar (height: 56px, sticky)**

```
[≡ Sidebar toggle]  [Logo]  [Global Search]  [+New Scan]  [🔔]  [Avatar ▾]
```

- Sidebar toggle: visible on all breakpoints (collapses to icon-only)
- Global Search: opens a command palette (⌘K / Ctrl+K) — v2 feature
- "+New Scan": always present, primary action shortcut, accent color
- Notification bell: badge shows unread count
- Avatar: opens user menu dropdown

**Sidebar (width: 240px desktop, icon-only at 64px on collapse)**

```
Dashboard
New Scan      ← accent color indicator
─────────────
History
─────────────
Help
─────────────
[Avatar]
[Display Name]
[email]
Settings ↗
Logout
```

- Active state: left border highlight + background tint
- Hover state: subtle background on all items
- Collapse: icon-only with tooltip on hover
- On mobile: full-width drawer overlay, triggered by hamburger

**Bottom Tab Bar (mobile, max 5 items)**

```
[⌂ Home]  [+ Scan]  [📋 History]  [🔔]  [👤 Profile]
```

- "Scan" tab uses accent color to emphasize primary action
- Notifications shows badge count
- Active state: filled icon + label

### 7.3 Breadcrumbs

Present on: S12 Scan Detail, S15 Help Article, S19 Appearance Settings.

Format: `Dashboard > History > filename_truncated.wav`

Not present on: Dashboard, New Scan, History root, Settings root
(These are top-level destinations, breadcrumbs add no value there.)

### 7.4 User Menu (Avatar Dropdown)

```
[Avatar] [Display Name]
[email@example.com]
─────────────────────
Profile
Settings
Appearance
─────────────────────
Help Center
Feedback
─────────────────────
Sign Out
```

### 7.5 Quick Actions

- Global "+" button in top bar always opens S08 New Scan
- Keyboard shortcut: N or ⌘K → "New Scan" (v2)
- From S11 History: right-click row → context menu (View, Delete, Copy link)

### 7.6 Footer (Public pages only)

```
[Logo]  [Tagline]

Product        Resources       Legal
Dashboard      Help Center     Privacy Policy
New Scan       Documentation   Terms of Service
History        Changelog       Cookie Policy
               API (coming)

[GitHub]  [Twitter]  [LinkedIn]

© 2026 VoiceGuard  ·  Built with care ·  Status
```

Footer is not shown inside the authenticated app shell (sidebar + top bar
take that role). Footer appears on: S01, S02, S03, S20 (shared results),
S21, S22.

---

## 8. Feature Hierarchy

### Core Features (Must have at launch)

These features define VoiceGuard. Without them, there is no product.

1. **File Upload for Analysis** — Accepts WAV, FLAC, MP3, M4A, OGG, AIFF
2. **Live Microphone Recording** — Record directly from browser, then analyze
3. **Binary Verdict** — Human or AI-Generated with confidence percentage
4. **Grad-CAM Visualization** — Frequency heatmap explaining the decision
5. **Confidence Breakdown** — Per-class probability scores
6. **Limitations Disclosure** — Honest, always-present model caveats
7. **Scan History** — Persistent record of all past analyses
8. **PDF Report Export** — Downloadable, formatted report for sharing/filing
9. **Shareable Link** — Public permalink to any result (unlisted URL)
10. **Account System** — Sign up, login, email verification, OAuth

**Why:** Each of these is load-bearing. Remove any one and a key persona
loses their primary reason to use the product.

### Secondary Features (Should have within 60 days of launch)

These features increase retention and professional utility.

11. **Search and Filter History** — Find scans by filename, verdict, date
12. **Bulk Delete** — History management for power users
13. **Feedback / Report Incorrect Result** — ML improvement pipeline
14. **Help Center** — Self-service support, reduces friction
15. **Notification System** — Model updates, async scan complete
16. **Onboarding Wizard** — Personalization and reduced time-to-value
17. **File SHA-256 Hash** — Evidence chain-of-custody for forensic users
18. **Appearance Settings** — Dark / light / system theme toggle
19. **Export Scan Data as JSON** — For researcher/developer use

**Why:** These features serve retention and professional users. Absence
doesn't break the core loop but meaningfully reduces depth of use.

### Power User Features (Should have within 90 days of launch)

These features serve professionals and researchers.

20. **Batch File Processing** — Upload and analyze multiple files at once
21. **CSV Export of History** — For analytical workflows
22. **Technical Mode** — Toggle to show raw model output, layer activations
23. **Scan Annotations** — Add notes to scan results (for journalists)
24. **Confidence Threshold Settings** — Set personal thresholds for
    "uncertain" classification

### Future Features (v2 / v3 roadmap)

25. **REST API with Key Management** — Programmatic access
26. **Team Workspaces** — Shared history, shared reports, role-based access
27. **Browser Extension** — Right-click any audio on the web
28. **Webhook Notifications** — Push results to Slack, email, SIEM
29. **Real-time Stream Analysis** — For live call monitoring
30. **Model Version Comparison** — See how different model versions score
    the same audio
31. **Mobile App** — iOS and Android native
32. **AASIST Model Integration** — Better neural codec detection
33. **Explainability Report** — Multi-page document with training context,
    benchmark comparisons, and per-attack EER tables for professional reports

---

## 9. Application Modules

The application is divided into independent modules. Each module owns its
routes, components, and data interactions. Modules communicate through
well-defined interfaces only.

### Module 1 — Auth

Screens: S02 Sign Up, S03 Login, S04 Email Verification, S05 Forgot Password

Responsibilities:
- Session management (JWT or session cookies)
- OAuth provider integration (Google, GitHub)
- Email verification flow
- Password reset flow
- Guest session management (temporary scan context before sign-up)
- Rate limiting on auth endpoints (brute force protection)

State: currentUser, isAuthenticated, sessionToken, isGuest

---

### Module 2 — Onboarding

Screens: S06 Onboarding Wizard

Responsibilities:
- First-run detection (hasCompletedOnboarding flag)
- Usage context collection and storage
- Guest scan migration (when a guest creates an account, migrate their
  anonymous scan into their new account)

Dependencies: Auth (must be authenticated)

---

### Module 3 — Detection

Screens: S08 New Scan, S09 Scan Processing, S10 Scan Result

Responsibilities:
- File validation (type, size, duration)
- Microphone recording API (MediaRecorder)
- File upload to processing endpoint
- Polling or WebSocket for processing status
- Result rendering (verdict, confidence, Grad-CAM, audio player)
- Result caching (current session)
- PDF report generation
- Shareable link generation

This is the highest-value, most-used module. It owns the core product loop.

State: uploadedFile, processingStatus, scanResult, gradcamData

---

### Module 4 — History

Screens: S11 History, S12 Scan Detail

Responsibilities:
- Paginated scan list with server-side filtering and search
- Single scan detail retrieval
- Bulk selection state
- Delete (single + bulk) with optimistic UI
- CSV export

State: scans[], filters, pagination, selectedScanIds[], currentScan

---

### Module 5 — Notifications

Screens: S13 Notifications, notification bell badge

Responsibilities:
- Unread count badge (real-time via WebSocket or polling)
- Notification list with read/unread state
- Mark all read
- Notification preferences (owned by Settings module, consumed here)

---

### Module 6 — Help

Screens: S14 Help Center, S15 Help Article

Responsibilities:
- Article fetching and rendering (Markdown)
- Search (client-side in v1, server-side in v2)
- "Was this helpful?" rating submission
- Contextual article recommendation based on user state

---

### Module 7 — Feedback

Screens: S16 Feedback / Report

Responsibilities:
- Form submission to feedback endpoint
- Pre-population from scan context
- Rate limiting on submissions

---

### Module 8 — Settings

Screens: S17 Profile, S18 Account Settings, S19 Appearance & Preferences

Responsibilities:
- User profile management
- Email change with re-verification
- Password change
- Notification preferences
- Theme preference (persisted to localStorage and synced to user record)
- Account deletion (soft delete)
- Data export

---

### Module 9 — Public / Marketing

Screens: S01 Landing, S20 Shared Scan Result, S21 404, S22 Error

Responsibilities:
- Public content rendering (no auth required)
- Shared result retrieval by scan UUID
- Privacy control on shared links (owner can revoke)
- Error page routing

---

## 10. Component Inventory

Every component is reusable, independently testable, and follows the
design system. Components are listed by category.

### Navigation Components

| Component         | Used In                              | Description                         |
|-------------------|--------------------------------------|-------------------------------------|
| TopBar            | All app screens                      | Logo, search, +new, bell, avatar    |
| Sidebar           | All app screens (desktop)            | Nav links, user mini-profile        |
| BottomTabBar      | All app screens (mobile)             | 5 primary nav items                 |
| BreadcrumbTrail   | S12, S15, S19                        | Hierarchical location indicator     |
| UserMenu          | TopBar dropdown                      | Profile, settings, logout           |
| PublicNavbar      | S01, S20, S21, S22                   | Marketing nav with CTAs             |
| PublicFooter      | S01, S20, S21, S22                   | Links, copyright                    |

### Input & Upload Components

| Component         | Used In            | Description                                   |
|-------------------|--------------------|-----------------------------------------------|
| FileDropzone      | S08 New Scan       | Drag-and-drop upload zone                     |
| MicrophoneRecorder| S08 New Scan       | Record/stop/playback controls with waveform   |
| AudioPreviewPlayer| S08, S10, S12      | Minimal audio player: play/pause/scrub        |
| FilePreviewCard   | S08 New Scan       | Shows selected file: name, size, format, duration |
| SearchInput       | S11 History, S14 Help | Search with clear button and state         |
| DateRangePicker   | S11 History        | Filter by date                                |
| FilterChip        | S11 History        | Single selectable filter tag                  |
| FilterChipGroup   | S11 History        | Row of FilterChips with single-select logic   |
| FormField         | S02, S03, S05, S18 | Input + label + inline error message          |
| PasswordInput     | S02, S03, S05, S18 | FormField variant with show/hide toggle       |
| PasswordStrength  | S02 Sign Up        | Animated strength meter (weak/fair/strong)    |
| OTPInput          | S04 Verification   | 6-digit split input with auto-advance         |
| SelectCard        | S06 Onboarding     | Large clickable card for single-select        |

### Display & Data Components

| Component         | Used In            | Description                                   |
|-------------------|--------------------|-----------------------------------------------|
| VerdictCard       | S10, S12, S20      | Large verdict with color, label, confidence   |
| ConfidenceBar     | S10, S12, S20      | Animated horizontal fill bar                  |
| ScoreBreakdown    | S10, S12, S20      | Human% / AI% two-bar layout                   |
| GradCAMPanel      | S10, S12, S20      | Side-by-side spectrogram + heatmap             |
| LimitationsCard   | S10, S12, S20      | Expandable model info and caveats              |
| ScanRow           | S07 Dashboard, S11 | List row for a scan: name, verdict, date, actions |
| ScanCard          | S07 Dashboard      | Card variant of ScanRow for recent activity   |
| StatCard          | S07 Dashboard      | Single metric: label + number + trend         |
| ActivityChart     | S07 Dashboard      | Simple donut or bar chart for scan history    |
| NotificationItem  | S13 Notifications  | Single notification: icon, title, body, time  |
| HelpArticleCard   | S14 Help Center    | Article preview: title, category, read time   |
| ProcessingCard    | S09 Processing     | Animation + progress steps for scan in-flight |

### Feedback & Status Components

| Component         | Used In            | Description                                   |
|-------------------|--------------------|-----------------------------------------------|
| Badge             | Throughout         | Verdict / status small label pill             |
| StatusDot         | ScanRow, S13       | Small colored dot for read/unread, status     |
| ProgressSteps     | S09, S04, S06      | Sequential step indicator                     |
| Toast             | Throughout         | Transient notification (success, error, info) |
| ToastStack        | Global             | Manages queue of Toast components             |
| Alert             | S10, S13           | Inline banner: warning, info, error           |
| ConfirmDialog     | Delete actions     | Modal confirmation: "Are you sure?"           |
| Modal             | Throughout         | Generic modal container with overlay          |
| Tooltip           | Throughout         | Hover label for icons and truncated text      |
| EmptyState        | S07, S11, S13      | Illustration + headline + CTA for empty data  |
| LoadingSpinner    | Throughout         | Circular spinner for inline loading           |
| SkeletonLoader    | S11, S07, S13      | Content-shape placeholder during load         |
| ErrorBoundary     | Module level       | Catches JS errors, shows fallback UI          |

### Layout Components

| Component         | Description                                                    |
|-------------------|----------------------------------------------------------------|
| AppShell          | Full-page layout: TopBar + Sidebar + main content area         |
| PageHeader        | Page title + breadcrumb + right-aligned page actions           |
| Section           | Content section with optional title and divider                |
| TwoColumnGrid     | 50/50 grid (Grad-CAM panels, result layout)                    |
| Card              | Surface container with border, padding, border-radius          |
| Divider           | Horizontal rule following design system spacing                |
| Spacer            | Explicit vertical spacing unit                                 |

---

## 11. Design System Guidelines

### 11.1 Typography

**Font Stack:**

| Role              | Font                    | Fallback                             |
|-------------------|-------------------------|--------------------------------------|
| UI / Body         | Inter                   | system-ui, -apple-system, sans-serif |
| Display / Hero    | Inter Tight             | Inter, system-ui                    |
| Data / Technical  | JetBrains Mono          | SF Mono, Fira Code, monospace       |

**Type Scale:**

| Token      | Size   | Weight | Line Height | Usage                           |
|------------|--------|--------|-------------|-------------------------------|
| display-xl | 52px   | 600    | 1.04        | Landing page hero headline    |
| display-lg | 36px   | 600    | 1.1         | Section headlines              |
| heading-xl | 28px   | 600    | 1.2         | Page titles                   |
| heading-lg | 22px   | 600    | 1.3         | Card titles, verdict label    |
| heading-md | 18px   | 600    | 1.3         | Sub-headings                  |
| body-lg    | 16px   | 400    | 1.6         | Primary body text             |
| body-md    | 14px   | 400    | 1.5         | Secondary body, labels        |
| body-sm    | 12px   | 400    | 1.5         | Meta text, timestamps         |
| label      | 11px   | 500    | 1.4         | Input labels (UPPERCASE)      |
| mono-lg    | 20px   | 500    | 1.3         | Confidence number display     |
| mono-md    | 15px   | 500    | 1.4         | Technical scores              |
| mono-sm    | 13px   | 400    | 1.4         | File hash, IDs                |

### 11.2 Color System

**Dark Mode (Primary / Default)**

| Token           | Hex       | Usage                              |
|-----------------|-----------|------------------------------------|
| bg              | #0A0A0A   | Page background                    |
| surface         | #111111   | Cards, panels                      |
| surface-2       | #161616   | Nested surfaces, inputs            |
| surface-3       | #1C1C1E   | Hover states on surface            |
| border          | #1F1F1F   | Default borders                    |
| border-hover    | #2E2E2E   | Hover borders                      |
| text            | #F5F5F7   | Primary text                       |
| text-secondary  | #AEAEB2   | Secondary text                     |
| muted           | #86868B   | Placeholder text, captions         |
| success         | #30D158   | Human/bonafide verdict, success    |
| success-dim     | #1A3D22   | Success tint background            |
| alert           | #FF453A   | AI/spoof verdict, error            |
| alert-dim       | #3D1A1A   | Error tint background              |
| warning         | #FF9F0A   | Uncertain verdict, warning         |
| warning-dim     | #3D2700   | Warning tint background            |
| accent          | #4F8EF7   | Links, active states, accent CTA   |
| accent-dim      | #1A2D4A   | Accent tint background             |
| overlay         | rgba(0,0,0,0.7) | Modal backdrops               |

**Light Mode**

| Token           | Hex       | Usage                              |
|-----------------|-----------|------------------------------------|
| bg              | #FAFAFA   | Page background                    |
| surface         | #FFFFFF   | Cards, panels                      |
| surface-2       | #F5F5F7   | Nested surfaces, inputs            |
| surface-3       | #EBEBED   | Hover states                       |
| border          | #E5E5EA   | Default borders                    |
| border-hover    | #C7C7CC   | Hover borders                      |
| text            | #1C1C1E   | Primary text                       |
| text-secondary  | #3A3A3C   | Secondary text                     |
| muted           | #6E6E73   | Placeholder, captions              |
| (success, alert, warning, accent — same hues, adjusted lightness)     |

**Semantic Color Rules:**
- NEVER use raw hex values in components. Always use design tokens.
- success is exclusively for Human verdicts. Do not use for other success states.
- alert is exclusively for AI verdicts. Use a separate `error` token for
  system errors. (Reason: mixing "AI detected" red with "form error" red
  creates confusing semantic overlap.)
- warning (amber) for uncertain results and cautionary notices only.

### 11.3 Spacing

Base unit: 4px. All spacing is a multiple of 4.

```
space-1:   4px   — tight internal padding
space-2:   8px   — icon-to-label, form element spacing
space-3:  12px   — compact element gaps
space-4:  16px   — standard card padding
space-5:  20px   — content sections
space-6:  24px   — standard section spacing
space-8:  32px   — card-to-card gaps
space-12: 48px   — major section breaks
space-16: 64px   — hero section padding
space-24: 96px   — page-level vertical padding
```

### 11.4 Border Radius

```
radius-xs:  4px   — badges, chips, small elements
radius-sm:  6px   — inputs, form elements, tags
radius-md:  8px   — buttons, small cards
radius-lg: 10px   — standard cards
radius-xl: 12px   — modals, large panels
radius-2xl:16px   — hero cards, feature cards
radius-full: 9999px — pill badges, avatars
```

### 11.5 Elevation / Shadow

Dark mode: Elevation communicated through border contrast, not drop shadows.
Light mode: Subtle drop shadows for depth.

```
shadow-sm:  0 1px 2px rgba(0,0,0,0.05)   — subtle card lift
shadow-md:  0 4px 12px rgba(0,0,0,0.08)  — popover, dropdown
shadow-lg:  0 8px 32px rgba(0,0,0,0.12)  — modal
shadow-xl:  0 16px 64px rgba(0,0,0,0.16) — spotlight feature
```

### 11.6 Motion / Animation

**Philosophy:** Animation communicates state, not decoration. Every animation
has a reason. Animations do not delay information delivery.

```
duration-fast:    100ms  — press/click feedback (button active state)
duration-normal:  200ms  — hover transitions, color changes
duration-enter:   300ms  — elements entering the screen
duration-reveal:  600ms  — result reveal animations (verdict card fill)
duration-slow:    800ms  — page-level transitions
```

**Easing:**
```
ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)   — standard transitions
ease-out:    cubic-bezier(0.16, 1, 0.3, 1)   — elements entering
ease-in:     cubic-bezier(0.4, 0, 1, 1)      — elements leaving
spring:      cubic-bezier(0.34, 1.56, 0.64, 1) — playful interactions
```

**Key Animations:**
1. Verdict card: confidence bar fills from 0 to final value over 600ms
2. Result section: staggered reveal — verdict → scores → Grad-CAM
   (each delayed by 80ms from previous)
3. Processing steps: sequential highlight as steps complete
4. Toast: slides in from right, auto-dismisses with fade
5. Modal: scale-in (0.95 → 1.0) + fade simultaneously

### 11.7 Buttons

```
Variant    | Background      | Text   | Border          | Usage
-----------|-----------------|--------|-----------------|----------------------------
primary    | text (#F5F5F7)  | bg     | none            | Single primary action
danger     | alert (#FF453A) | white  | none            | Destructive actions
secondary  | transparent     | muted  | border          | Secondary actions
ghost      | transparent     | muted  | none            | Tertiary / icon buttons
accent     | accent (#4F8EF7)| white  | none            | Links CTA, account accent
```

Sizes: lg (16px text, 12/28px padding), md (14px text, 10/20px), sm (12px text, 8/16px)

States for all: default / hover (opacity 0.85) / active (scale 0.97) /
disabled (opacity 0.4, cursor not-allowed) / loading (spinner replaces label)

### 11.8 Form Elements

- All inputs: height 40px (md), 48px (lg), surface-2 background, border,
  6px radius
- Focus state: accent-colored border (2px), subtle accent glow in dark mode
- Error state: alert-colored border + error icon + error message below
- Success state (post-validation): success-colored border + check icon
- Labels: 11px uppercase letter-spaced, displayed above input always
- Placeholder text: muted color
- Required fields: asterisk (*) in muted color after label, not before

### 11.9 Cards

Standard card: background surface, 1px border, 10px radius, 24px padding.

Variants:
- Default: surface background
- Elevated: surface + shadow-sm (light mode only)
- Interactive (hoverable): border-hover on hover, subtle background shift
- Verdict card: custom — large, color-coded, no standard border
- Danger zone: alert-dim background for destructive action sections

### 11.10 Badges / Chips

Verdict badges (used in history rows):
- HUMAN: success text + success-dim background
- AI-GENERATED: alert text + alert-dim background
- UNCERTAIN: warning text + warning-dim background

Status badges:
- INFO / NEW: accent text + accent-dim background

Sizes: sm (10px text, 2px/8px padding) / md (12px text, 4px/10px padding)

Always use radius-full for pill shape.

### 11.11 Accessibility Guidelines

- Minimum color contrast ratio: 4.5:1 for body text, 3:1 for large text
  (WCAG AA compliance at minimum; target AAA for primary verdict display)
- All interactive elements: visible focus state (2px outline, 2px offset,
  accent color)
- Keyboard navigation: Tab through all interactive elements in logical order
- Screen reader: all images have alt text; Grad-CAM has text description
  as alternative; confidence bars have aria-valuenow/min/max attributes
- Motion: respect prefers-reduced-motion; all animations can be disabled
- Icons: never used alone without label or tooltip
- Touch targets: minimum 44×44px on mobile for all interactive elements
- Error messages: associated with inputs via aria-describedby
- Loading states: aria-live="polite" for status announcements

### 11.12 Responsive Breakpoints

```
xs:  0–599px    — mobile portrait
sm:  600–899px  — mobile landscape / small tablet
md:  900–1199px — tablet
lg:  1200–1535px — desktop
xl:  1536px+    — wide desktop
```

**Responsive rules:**
- Sidebar collapses to BottomTabBar at md and below
- TwoColumnGrid stacks to single column at sm and below
- Result page sections stack at sm and below
- Dashboard stats row: 3 columns → 2 columns → 1 column
- History table: full table → compact table → card list

---

## 12. User Flows

### Flow 1 — Upload File and View Result (Guest)

```
S01 Landing
  ↓ Click "Try without account"
S08 New Scan (guest session initiated)
  ↓ Drag file onto dropzone
  ↓ File appears in preview card
  ↓ Audio player shows in preview
  ↓ User clicks play to verify file
  ↓ User clicks "Analyze"
S09 Processing
  ↓ Progress steps animate through 3 stages
  ↓ Auto-redirect on completion
S10 Result
  ↓ Confidence bar animates into place
  ↓ User reads verdict + plain-language explanation
  ↓ User opens Grad-CAM panel
  ↓ User reads limitations (expands card)
  ↓ User sees "Save this result — create a free account" CTA
  [A] User signs up → S02 Sign Up → [scan migrated to account] → S07 Dashboard
  [B] User downloads PDF (works as guest)
  [C] User copies share link (works as guest)
  [D] User leaves
```

### Flow 2 — Microphone Recording (Authenticated)

```
S07 Dashboard
  ↓ Click "New Scan"
S08 New Scan
  ↓ Click "Record" tab
  ↓ Browser shows microphone permission prompt
  [Permission denied]
    ↓ Error card: "Microphone access denied"
    ↓ Browser-specific instructions to grant permission
    ↓ "Try uploading a file instead" fallback CTA
  [Permission granted]
    ↓ Record button activates (pulsing red)
    ↓ Live waveform visualizer animates
    ↓ Timer counts up (00:00 → 04:00 max)
    ↓ User speaks / plays audio
    ↓ User clicks stop (or timer reaches 04:00)
    ↓ Recording plays back for review
    ↓ User can Re-record or Accept
    ↓ User clicks "Analyze Recording"
S09 Processing → S10 Result (same as Flow 1)
```

### Flow 3 — View a Specific Past Scan

```
S07 Dashboard
  ↓ User sees recent activity section
  ↓ User clicks a specific scan row
S12 Scan Detail
  ↓ Full result displayed (identical to S10)
  ↓ User reads result
  [A] User downloads PDF
  [B] User copies share link
  [C] User clicks "Report incorrect result"
      ↓ S16 Feedback (form pre-populated with scan context)
      ↓ Submit → Thank you state → S07 Dashboard
  [D] User clicks breadcrumb "History" → S11
  [E] User clicks "Delete scan" → Confirm dialog → Scan deleted → S11
```

### Flow 4 — Search and Filter History

```
S11 History
  ↓ User types filename in search input
  ↓ Results filter in real-time (client-side)
  ↓ User applies "AI-Generated" filter chip
  ↓ Results refine further
  ↓ User changes date range to "Last 30 days"
  ↓ User clicks a result row → S12 Scan Detail
  [Back] → S11 with filters preserved (back-navigation should restore state)
```

### Flow 5 — Download PDF Report

```
S10 Result OR S12 Scan Detail
  ↓ User clicks "Download PDF Report"
  ↓ Loading spinner on button (report generates in background)
  ↓ PDF generates (~1–2 seconds)
  ↓ Browser download dialogue opens
  ↓ File saved as: voiceguard_[filename]_[date].pdf
  ↓ Success toast: "Report downloaded"

PDF Report Contents:
  Page 1: VoiceGuard header + Verdict + Confidence + Date + Scan ID
  Page 2: Grad-CAM visualization (full-width) with annotation
  Page 3: Technical details: raw scores, file metadata, SHA-256, model version
  Page 4: Limitations disclaimer + methodology note
  Footer: "Analyzed by VoiceGuard · Model: LCNN v1 · EER: 7.07%"
```

### Flow 6 — Share a Result

```
S10 Result OR S12 Scan Detail
  ↓ User clicks "Copy Share Link"
  ↓ Button changes to "Copied!" for 2 seconds
  ↓ URL copied to clipboard: voiceguard.app/r/[uuid]
  ↓ Toast: "Link copied to clipboard"

Recipient opens link:
S20 Shared Scan Result
  ↓ Full result displayed (no authenticated actions)
  ↓ Persistent CTA: "Analyze your own audio — Free, no account needed"
  ↓ If recipient clicks: → S08 New Scan (guest)
```

### Flow 7 — Report Incorrect Result

```
S10 Result OR S12 Scan Detail
  ↓ User clicks "Report incorrect result"
S16 Feedback
  ↓ Form auto-populated:
    Scan ID: [UUID] (read-only)
    File: [filename]
    Model said: HUMAN | AI-GENERATED (read-only)
    I believe this is: [Human] [AI-Generated] (user selection)
    Why?: [text area]
  ↓ User fills out form
  ↓ User clicks "Submit Feedback"
  ↓ Inline thank-you message replaces form:
    "Thank you for helping improve VoiceGuard.
     This report has been recorded and will inform model updates."
  ↓ User navigates back (dashboard / history links)
```

### Flow 8 — Delete Account

```
S18 Account Settings
  ↓ User scrolls to "Danger Zone" section
  ↓ User clicks "Delete My Account"
  ↓ Confirmation modal:
    "Delete your account? This action cannot be undone."
    "All your scan history will be permanently deleted in 30 days."
    "Type DELETE to confirm:"
    [Text input]
    [Cancel]  [Delete Account]
  ↓ User types "DELETE" exactly
  ↓ Delete button activates
  ↓ User clicks Delete Account
  ↓ Soft delete initiated (30-day recovery window)
  ↓ Toast: "Your account will be deleted in 30 days. Check your email."
  ↓ Session cleared → S01 Landing Page
```

---

## 13. Error Handling Strategy

Every error falls into one of three layers:

**Layer 1 — Inline (field/component level):** Error appears next to the
element that caused it. No page disruption.

**Layer 2 — Toast (transient, app level):** Brief notification that auto-
dismisses. Used for non-blocking errors where context is clear.

**Layer 3 — Page-level / Modal:** Full error state when recovery requires
user action or context is lost.

---

### Upload / Detection Errors

| Error Type           | Message                                                 | UX Behavior                |
|----------------------|--------------------------------------------------------|----------------------------|
| File too large       | "File exceeds 10MB limit. Try a shorter clip."         | Inline, below dropzone     |
| Unsupported format   | "Format not supported. Use WAV, FLAC, MP3, or AIFF."  | Inline, below dropzone     |
| Audio too short      | "Audio must be at least 0.5 seconds."                  | Inline, below dropzone     |
| Empty file           | "This file appears to be empty or corrupted."          | Inline, below dropzone     |
| Processing failed    | "Analysis failed. Please try again."                   | Error card on S09, retry CTA |
| Processing timeout   | "This is taking longer than usual. [Retry] [Cancel]"   | Error state on S09         |
| Network error        | "Connection lost during analysis. [Retry]"             | Error card on S09          |
| Model failure        | "The AI model encountered an error. [Report this]"     | Error card, link to S16    |

**Rule:** Never say "Error 500" or expose technical details to users.
Always provide a plain-language description + at least one recovery action.

---

### Authentication Errors

| Error Type           | Message                                                 | UX Behavior                |
|----------------------|--------------------------------------------------------|----------------------------|
| Wrong password       | "Incorrect email or password."                         | Inline under password field|
| Account not found    | "Incorrect email or password." (same — no enumeration) | Inline under email field   |
| Email already taken  | "An account with this email already exists. [Login]"   | Inline under email field   |
| Weak password        | Progressive: "Add a number" / "Add uppercase"          | Inline, password meter     |
| Expired OTP code     | "Code expired. [Resend code]"                          | Inline under OTP input     |
| Invalid OTP code     | "Incorrect code. [X attempts remaining]"               | Inline under OTP input     |
| Session expired      | Toast: "Session expired. Please log in again."         | Toast + redirect to S03    |
| OAuth failure        | "Sign-in with Google failed. [Try another way]"        | Inline alert above form    |

---

### Microphone / Recording Errors

| Error Type           | Message                                                 | UX Behavior                |
|----------------------|--------------------------------------------------------|----------------------------|
| Permission denied    | "Microphone access was denied. [Browser-specific steps]"| In-context card on S08    |
| No microphone found  | "No microphone detected. Plug one in and try again."   | In-context card on S08     |
| Recording too short  | "Recording too short. Hold the button longer."         | Inline under record button |
| Recording failed     | "Recording stopped unexpectedly. Please try again."    | Toast, record button resets|

---

### Network & Server Errors

| Error Type           | Message                                                 | UX Behavior                |
|----------------------|--------------------------------------------------------|----------------------------|
| Offline              | Banner: "You appear to be offline. Reconnecting..."    | Top banner, non-dismissable|
| API 503              | "VoiceGuard is temporarily unavailable. [Status page]" | Full-page error (S22)      |
| API 429 (rate limit) | "Too many requests. Please wait a moment."             | Toast, button disabled 30s |
| Generic API error    | "Something went wrong. [Try again] [Report this]"      | Toast or inline card       |

---

### Validation Errors (Forms)

**Rule:** Validate on blur (when user leaves field), not on submit.
The only exception: password confirmation validates live after first input.

Show: red border + error icon + error message below field.
On correction: immediately clear error and show check icon.

---

### Empty / Missing Data States

Distinguished from errors: these are expected states, not failures.
See Section 14 (Empty States).

---

## 14. Empty States

Empty states are designed with: an illustration or icon, a descriptive
headline, a sub-line of context, and a clear CTA.

### Dashboard — No Scans Yet

```
[Waveform icon, faint]
"Start your first analysis"
"Upload an audio file or record your voice to detect AI-generated speech."
[Analyze Audio →]   [Learn How It Works →]
```

### History — No Scans

```
[Clock icon, faint]
"No scans yet"
"Your analysis history will appear here after your first scan."
[Start a Scan →]
```

### History — No Results for Current Filter/Search

```
[Search icon, faint]
"No matching scans"
"No scans match "filename.wav" in the last 30 days."
[Clear filters]   [Search all time]
```

### Notifications — All Read / None

```
[Bell icon, faint]
"You're all caught up"
"New alerts about your scans and model updates will appear here."
[Go to Dashboard →]
```

### History — Guest User Prompt

```
[Lock icon, faint]
"Your results aren't being saved"
"Create a free account to save your scan history and access reports
 from any device."
[Create Free Account →]   [Sign In →]
```

---

## 15. Loading States

**Rule:** Every operation that takes more than 100ms gets a loading state.
Every loading state communicates: what is happening + estimated duration.
Never use a spinner alone for operations that take over 3 seconds — use
progress steps or animated explanatory states instead.

### Page Load

First-paint: TopBar and Sidebar skeleton render immediately.
Content area: SkeletonLoader components match the shape of the final content.

Never show a full-page spinner. The shell renders first; content loads in.

### New Scan Submission → Processing

S08 → S09: "Analyze" button shows loading spinner for ~500ms while the file
uploads. Then transitions to S09 Processing (full-page loading state).

S09 Processing: 3-step animated indicator with estimated time (see S09 spec).
This is the most important loading state — it must feel alive and informative.

### PDF Report Generation

Button state: "Generating..." with spinner (1–2 seconds).
Do not navigate away. Generate inline and trigger download when ready.

### History List Loading

SkeletonLoader: 5 rows of the exact shape of ScanRow. Fade in when real
data arrives.

### Grad-CAM Image Loading

Image loads with a blur-up effect (blurred placeholder → sharp image).
Shows a spectrogram-shaped skeleton while loading.

### Settings Save

Inline: button shows "Saving..." → "Saved ✓" for 2 seconds → reverts to
"Save changes". No full-page load. No toast for auto-save settings (theme,
preferences) — only for explicitly submitted forms.

### Authentication

Login/Sign Up button: shows spinner during request.
The page does not navigate until confirmation is received.

### Notification Bell Badge

Real-time: badge number updates via WebSocket (v2) or polling (v1 fallback).
On poll failure: badge retains last known count; silent retry.

---

## 16. Success States

Success states confirm a completed action without over-celebrating.
They are brief, clear, and get out of the user's way.

### Successful Login

No toast. Direct navigation to S07 Dashboard.
The Dashboard itself is the confirmation — user is in the product.

### Successful Sign Up

Brief redirect transition to S04 Email Verification.
S04 shows the "Check your email" confirmation state — this IS the success state.

### Scan Complete

Auto-navigate from S09 Processing to S10 Result.
The Result page IS the success state — no separate confirmation needed.
The confidence bar animation (filling from 0) is the moment of reveal.

### PDF Downloaded

Toast (auto-dismiss 4s): "[filename] report downloaded."
Button briefly shows "Downloaded ✓" before resetting.

### Share Link Copied

Button changes: "Copy Link" → "Copied! ✓" (2 seconds) → reverts.
No toast (the button feedback is sufficient).

### Account Settings Saved

Inline: "Saved ✓" confirmation appears next to the save button for 2 seconds.

### Feedback Submitted

Form is replaced inline by:
"Thank you for your feedback. This helps improve VoiceGuard's accuracy."
[Go to Dashboard] button.

### Scan Deleted

Toast (auto-dismiss 4s): "Scan deleted."
Optional "Undo" link in the toast (5-second window before actual deletion
executes on the server — optimistic UI).

### Account Deletion Initiated

Toast + session clear:
"Account scheduled for deletion in 30 days. Check your email for confirmation."
Then redirect to S01 Landing Page.

---

## 17. Non-Functional Requirements

### Performance

| Metric                          | Target                        | Priority |
|---------------------------------|-------------------------------|----------|
| Time to First Contentful Paint  | < 1.5s (3G connection)        | Critical |
| Time to Interactive             | < 3.0s                        | Critical |
| Scan submission → Result render | < 10s (end-to-end)            | Critical |
| API response (inference only)   | < 5s p95                      | High     |
| PDF report generation           | < 3s                          | High     |
| History page load               | < 1.5s (50 records)           | High     |
| App shell render                | < 500ms after auth            | High     |
| Grad-CAM image load             | < 1s after result             | Medium   |

### Security

- Authentication: JWT tokens (HttpOnly cookies, not localStorage)
- Password: bcrypt hashing, minimum entropy enforced
- Sessions: configurable TTL, refresh token rotation
- HTTPS: enforced everywhere; HTTP redirects to HTTPS
- CORS: explicit allowlist; no wildcard origins
- Rate limiting: 10 scans/hour per guest IP; 50 scans/day per account
- File validation: magic bytes check before parsing; max 10MB
- Temp files: not stored permanently; deleted within 60 seconds of scan
- Scan results: stored as metadata (scores, verdict) not raw audio
- API keys: scrypt-hashed on server; only shown once at creation
- Input validation: all user input validated server-side
- Content Security Policy: strict policy; no inline scripts
- OAuth: PKCE flow; state parameter; no implicit flow

### Accessibility

- WCAG 2.1 AA compliance as baseline; target AAA for primary result display
- Screen reader: tested with NVDA (Windows), VoiceOver (macOS/iOS),
  TalkBack (Android)
- Keyboard: complete keyboard navigability; no mouse-only interactions
- Color: no information conveyed by color alone (verdict also communicated
  by text label and icon)
- Motion: prefers-reduced-motion respected; all animations suppressable
- Touch: minimum 44×44px targets; no hover-only interactions on mobile
- Focus management: after modal close, focus returns to trigger element
- Skip link: "Skip to main content" as first focusable element

### Scalability

- Stateless API server (horizontally scalable behind load balancer)
- Model inference: CPU-based; horizontally scalable by adding workers
- Database: designed for read-heavy workload (scan history queries)
- Storage: scan metadata in database; audio never persisted
- CDN: static assets (JS, CSS, fonts, images) served from CDN
- Caching: scan results cached for 24 hours (same UUID returns cached result)

### Reliability

- Uptime target: 99.5% monthly (measured at /health endpoint)
- Scan failure rate: < 1% of valid audio submissions
- Graceful degradation: if inference service is unavailable, API returns
  503 with estimated recovery time; Gradio UI shows maintenance state
- Database backups: daily automated backups, 30-day retention
- Error budget: tracked via incident post-mortems

### Maintainability

- Component library: all UI components in isolated component library
  (Storybook or equivalent), documented with usage examples
- Design tokens: single source of truth for all colors, spacing, typography
  — implemented in CSS custom properties; consumed by all components
- Module boundaries: no cross-module direct imports; communication via
  defined interfaces or shared state
- API contract: OpenAPI spec committed to repository; auto-generated
  from server annotations
- Code style: enforced via linting/formatting in CI; no manual enforcement

### Cross-Browser Compatibility

Supported:
- Chrome/Chromium 110+ (Windows, macOS, Linux, Android)
- Safari 15+ (macOS, iOS 15+)
- Firefox 115+ (Windows, macOS)
- Edge 110+ (Windows)

Not supported: Internet Explorer (any version).

Microphone recording uses the Web Audio API + MediaRecorder API.
Fallback: graceful degradation to "upload only" on browsers without
MediaRecorder support.

### Responsiveness

The application is fully usable on:
- Desktop: 1280px+ (optimal experience)
- Tablet: 768–1279px (adapted layout)
- Mobile: 375–767px (single column, bottom tab bar)

Minimum supported width: 360px (iPhone SE).

### Data Privacy

- Audio is NEVER stored permanently. Files are processed in memory and
  deleted within 60 seconds regardless of scan outcome.
- Scan metadata stored: verdict, confidence scores, file metadata (name,
  size, duration, format), SHA-256 hash, timestamp. No audio content.
- GDPR: users can export all their data (JSON download) and delete their
  account at any time via Settings.
- Data retention: scan metadata kept for the lifetime of the account;
  deleted 30 days after account deletion.
- Third-party analytics: if added, must be privacy-first (Plausible or
  Fathom, not Google Analytics). User IP anonymized.

---

## 18. Product Roadmap

### v1.0 — Foundation (Launch)

Must-have screens: S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12
Support screens: S13, S14, S16, S17, S18, S19, S20, S21, S22

Features: upload, record, detect, result + Grad-CAM, history, PDF export,
share link, account system, onboarding, help center, feedback

Goal: A product that earns trust. Every flow complete. No dead ends.

---

### v1.1 — Quality & Retention (30 days post-launch)

- Search and filter in History (S11)
- Bulk delete / CSV export
- Help Center full content (S14, S15)
- Notification preferences in Settings (S18)
- "Uncertain" confidence explanation improvements
- Performance optimizations (< 5s inference p95)
- Accessibility audit and fixes

---

### v1.2 — Professional Features (60 days post-launch)

- SHA-256 file hash on result page and PDF
- Scan annotations (add notes to results)
- Advanced PDF report (multi-page, methodology section)
- Dashboard scan breakdown chart (Activity Chart component)
- Appearance settings (S19) with theme selection
- Technical Mode toggle (raw softmax scores, layer info)

---

### v2.0 — Scale (6 months post-launch)

- API with key management (developer access)
- Batch file processing (upload up to 20 files)
- Team workspaces (shared history, shared reports)
- Webhook notifications (Slack, email)
- AASIST model integration (better neural codec detection)
- Model version selector (compare LCNN v1 vs AASIST)
- Browser extension (Chrome, Firefox)

---

### v3.0 — Platform (12 months post-launch)

- Mobile apps (iOS, Android)
- Real-time stream analysis API
- Enterprise SSO (SAML, SCIM)
- Audit logs for enterprise accounts
- Custom confidence thresholds per organization
- SLA-backed uptime for enterprise tier

---

## 19. Final Architectural Recommendations

### Recommendation 1 — Build the Result Page First

S10 Scan Result is the product. Every other screen exists to bring users
to this moment or to let them return to it. Design, prototype, and validate
S10 before building anything else. If the verdict card doesn't earn trust —
if the Grad-CAM explanation doesn't land — the entire product underperforms.

The sequence for engineering: S10 (result) → S08 (upload) → S09 (processing)
→ S07 (dashboard) → S11 (history). Auth last — build with mocked sessions
initially so UI work can proceed independently of backend.

### Recommendation 2 — The Limitations Notice Is Non-Negotiable

The model has known failure cases. A17 neural codec attacks have 36.8% EER —
barely better than random. This must be communicated clearly in the product.
Do not bury it in help documentation. Surface it on the result page itself,
always visible, one click to expand.

This is not a weakness of the product. It is a trust-building feature.
Journalists, forensic analysts, and cybersecurity professionals will find
this disclaimer and trust the tool MORE because of it, not less.
Products that hide their limitations lose professional users the moment
those users encounter an edge case.

### Recommendation 3 — Guest Mode is the Top-of-Funnel

Do not force account creation before the first scan. The guest mode (try
without account) is the highest-leverage growth mechanism. A user who has
seen a real result — who has their answer on screen — is 5–10× more likely
to create an account than a user who has only seen the landing page.

The post-result sign-up CTA ("Save this result — create a free account")
should prominently carry the scan context: "Your scan result will be
available in your history immediately after sign-up."

### Recommendation 4 — One Primary Action Per Screen

Every screen has exactly one primary action. The Upload screen's primary
action is "Analyze." The Result screen's primary action is "Analyze Another
File." The Dashboard's primary action is the embedded upload zone.

Do not dilute primary actions with secondary CTAs of equal visual weight.
Users need a clear path forward at every moment.

### Recommendation 5 — The Feedback Loop is the Product's Future

S16 Feedback / Report Incorrect Result is not a support feature — it is
the model improvement pipeline. Every report connects a scan_id, a model
verdict, and a user-reported ground truth. This is labeled correction data.
With sufficient volume (target: 100+ reports/month), it becomes the
training signal for v2 model updates.

Treat S16 as a first-class product feature, not an afterthought. Keep the
form short (3 fields maximum), pre-populate from scan context, and confirm
that the report was received with a meaningful thank-you message.

### Recommendation 6 — Confidence Communication Requires a Three-State Model

The product has three verdict states, not two:

  State 1: HUMAN (confidence ≥ 85%)       — Clear green, strong language
  State 2: AI-GENERATED (confidence ≥ 85%) — Clear red, strong language
  State 3: UNCERTAIN (confidence < 65%)   — Amber, explicitly cautionary

The 65–85% range is a "soft confident" zone that should use moderate
language ("likely human" / "likely AI") rather than definitive statements.
This maps honestly to the model's actual reliability curve.

Implementing only two states (human/AI) and displaying "99% confidence"
for a prediction that is actually in the model's blind spot is a liability.
The three-state model builds credibility with professional users.

### Recommendation 7 — Design for the Forensic Use Case from Day One

The SHA-256 hash, the scan timestamp, the model version, the EER benchmark
value, the per-attack limitations — all of this metadata should be present
in every PDF report from launch. It costs almost nothing to include and is
the difference between a report that a journalist or lawyer can cite versus
one that cannot be referenced professionally.

This data comes free from the existing backend (file hash computable
client-side, timestamp from server, model version as a constant). The only
cost is including it in the report layout.

### Recommendation 8 — Treat the Design System as Shared Infrastructure

Before writing a single application component, establish the design token
system (colors, spacing, typography, radius, shadows) as CSS custom
properties in a single file. Every component consumes tokens, never raw
values.

This single investment prevents: color drift, spacing inconsistency,
dark-mode maintenance headaches, and the need to update dozens of components
when the brand evolves. It is the architectural foundation of a scalable UI.

---

**Document Status:** Approved for Engineering Handoff  
**Next Action:** Engineering team reviews S08 (New Scan), S09 (Processing),
and S10 (Result) specifications and raises any technical constraints that
require design adjustment before implementation begins.

---

*VoiceGuard Product Architecture Document — v1.0 — 2026-07-25*  
*This document is the single source of truth for all product and UX decisions.*  
*All engineering agents implementing VoiceGuard features should reference this document.*
