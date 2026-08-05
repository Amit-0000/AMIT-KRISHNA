# ASVspoof2019 LA Dataset Report

Source: Kaggle `awsaf49/asvpoof-2019-dataset` (official ASVspoof2019 LA partition, as documented in `docs/02_dataset.md`).

## Integrity summary

- Total utterances across all protocol files: **121461**
- Missing files (listed in protocol, not found on disk): **0**
- Present but unreadable/corrupted (FLAC header failed to parse): **0**
- Duplicate file paths within the manifest: **0**

## train

- Total utterances: **25380**
- Bonafide: **2580** (10.2%)
- Spoof: **22800** (89.8%)
- Missing: **0**  |  Unreadable: **0**
- Sample rate(s) observed: {16000: 25380}
- Duration (s): min=0.652, max=13.188, mean=3.426, median=3.202, std=1.419
- Attack-type breakdown: {'A01': np.int64(3800), 'A02': np.int64(3800), 'A03': np.int64(3800), 'A04': np.int64(3800), 'A05': np.int64(3800), 'A06': np.int64(3800)}

## dev

- Total utterances: **24844**
- Bonafide: **2548** (10.3%)
- Spoof: **22296** (89.7%)
- Missing: **0**  |  Unreadable: **0**
- Sample rate(s) observed: {16000: 24844}
- Duration (s): min=0.695, max=11.594, mean=3.478, median=3.280, std=1.458
- Attack-type breakdown: {'A01': np.int64(3716), 'A02': np.int64(3716), 'A03': np.int64(3716), 'A04': np.int64(3716), 'A05': np.int64(3716), 'A06': np.int64(3716)}

## eval

- Total utterances: **71237**
- Bonafide: **7355** (10.3%)
- Spoof: **63882** (89.7%)
- Missing: **0**  |  Unreadable: **0**
- Sample rate(s) observed: {16000: 71237}
- Duration (s): min=0.470, max=13.026, mean=3.108, median=2.818, std=1.481
- Attack-type breakdown: {'A07': np.int64(4914), 'A08': np.int64(4914), 'A09': np.int64(4914), 'A10': np.int64(4914), 'A11': np.int64(4914), 'A12': np.int64(4914), 'A13': np.int64(4914), 'A14': np.int64(4914), 'A15': np.int64(4914), 'A16': np.int64(4914), 'A17': np.int64(4914), 'A18': np.int64(4914), 'A19': np.int64(4914)}

## Folder structure (verified on disk)

```
data/
├── ASVspoof2019_LA_cm_protocols/
│   ├── ASVspoof2019.LA.cm.train.trn.txt
│   ├── ASVspoof2019.LA.cm.dev.trl.txt
│   └── ASVspoof2019.LA.cm.eval.trl.txt
├── ASVspoof2019_LA_train/flac/   (25,380 files)
├── ASVspoof2019_LA_dev/flac/     (24,844 files)
└── ASVspoof2019_LA_eval/flac/    (71,237 files)
```

Matches the official layout documented in `docs/02_dataset.md` §10 exactly (the Kaggle mirror wrapped this under an extra `LA/LA/` prefix and included an unused `PA/` — physical access — partition; both were reconciled/left untouched respectively during extraction, see final report).
