NEXT STEPS — VoiceGuard
========================
Everything below requires accounts or credentials you don't have set up yet.
Complete these in order when you're ready to deploy.

────────────────────────────────────────────────────────────────────────────────
STEP 1 — Create a GitHub account (if you don't have one)
────────────────────────────────────────────────────────────────────────────────
  Go to: https://github.com/signup
  Use any username. Remember it — you'll need it in Step 2 and Step 5.

────────────────────────────────────────────────────────────────────────────────
STEP 2 — Fork the original repo and add it as your remote
────────────────────────────────────────────────────────────────────────────────
  a) In your browser, go to:
       https://github.com/imsoumya18/audio_deepfake_detector
  b) Click the "Fork" button (top-right). GitHub creates:
       https://github.com/YOUR_GITHUB_USERNAME/audio_deepfake_detector
  c) Back in your terminal, inside the voiceguard/ folder:

       cd "/Users/kanish/AMIT KRISHNA/voiceguard"
       git remote add origin https://github.com/YOUR_GITHUB_USERNAME/audio_deepfake_detector.git
       git remote -v   # should show origin pointing to your fork

────────────────────────────────────────────────────────────────────────────────
STEP 3 — Create a HuggingFace account and upload the model checkpoint
────────────────────────────────────────────────────────────────────────────────
  a) Go to: https://huggingface.co/join  — create a free account.
  b) Install the HF CLI (already installed in .venv):

       source .venv/bin/activate
       huggingface-cli login
       # Paste a WRITE token from: https://huggingface.co/settings/tokens

  c) Create your model repo:

       huggingface-cli repo create YOUR_HF_USERNAME/voiceguard-model --type model

  d) Download the original checkpoint and upload it to your repo:

       python -c "
       from huggingface_hub import hf_hub_download, HfApi
       import shutil, pathlib
       src = hf_hub_download('imsoumya18/audio-deepfake-detector', 'lcnn_best.pt')
       shutil.copy(src, 'lcnn_best.pt')
       api = HfApi()
       api.upload_file(
           path_or_fileobj='lcnn_best.pt',
           path_in_repo='lcnn_best.pt',
           repo_id='YOUR_HF_USERNAME/voiceguard-model',
           repo_type='model',
       )
       print('Done')
       "

  e) In app.py AND demo/app.py, change line 22:
       _HF_REPO = "imsoumya18/audio-deepfake-detector"
     to:
       _HF_REPO = "YOUR_HF_USERNAME/voiceguard-model"

────────────────────────────────────────────────────────────────────────────────
STEP 4 — Create your HuggingFace Space
────────────────────────────────────────────────────────────────────────────────
  a) Go to: https://huggingface.co/new-space
  b) Space name: voiceguard
  c) SDK: Gradio
  d) Visibility: Public (or Private)
  e) Note the repo_id shown — it will be: YOUR_HF_USERNAME/voiceguard

────────────────────────────────────────────────────────────────────────────────
STEP 5 — Update CI/CD to point to your Space
────────────────────────────────────────────────────────────────────────────────
  In .github/workflows/sync_to_hf.yml, replace the TODO line:
    repo_id="TODO_YOUR_HF_USERNAME/voiceguard",
  with:
    repo_id="YOUR_HF_USERNAME/voiceguard",

  Then add your HF_TOKEN as a GitHub Actions secret:
    GitHub repo → Settings → Secrets and variables → Actions → New repository secret
    Name:  HF_TOKEN
    Value: your HuggingFace WRITE token (from https://huggingface.co/settings/tokens)

────────────────────────────────────────────────────────────────────────────────
STEP 6 — Push to GitHub (triggers auto-deploy to HF Spaces)
────────────────────────────────────────────────────────────────────────────────
  BEFORE PUSHING — verify this one line in sync_to_hf.yml:
    repo_id="YOUR_HF_USERNAME/voiceguard"   ← must NOT say imsoumya18

  Then push:
    git push -u origin main

  GitHub Actions will auto-deploy your Space within ~2 minutes.
  Watch the deploy at: https://github.com/YOUR_GITHUB_USERNAME/audio_deepfake_detector/actions

────────────────────────────────────────────────────────────────────────────────
STEP 7 — (Optional) Custom domain
────────────────────────────────────────────────────────────────────────────────
  HuggingFace Spaces Pro plan ($9/mo) supports custom domains.
  HF Space → Settings → Custom Domains → add yourdomain.com
  Set a CNAME record at your DNS provider pointing to hf.space.

────────────────────────────────────────────────────────────────────────────────
WHAT'S ALREADY DONE (no action needed)
────────────────────────────────────────────────────────────────────────────────
  ✓ Repo cloned locally to:  /Users/kanish/AMIT KRISHNA/voiceguard/
  ✓ Virtual env at:          .venv/  (activate: source .venv/bin/activate)
  ✓ Dependencies installed:  torch 2.9.1, gradio 5.29.0, all ML libs
  ✓ Frontend rebranded:      app.py, demo/app.py — VoiceGuard Apple Pro dark
  ✓ README front-matter:     title=VoiceGuard, emoji=🛡️, colorFrom/To=gray
  ✓ CI/CD:                   sync_to_hf.yml updated with TODO placeholder
  ✓ LICENSE:                 MIT with dual copyright (you + original author)
  ✓ Remote removed:          Cannot accidentally push to original author's repo
  ✓ All backend code:        Untouched (src/, api/, configs/, Dockerfile)
