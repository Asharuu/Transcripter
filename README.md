# Transcripter 🎙️

A lightweight, modern Windows desktop application for real-time audio transcription. **Transcripter** captures **Windows System Audio (WASAPI Loopback)** and/or **Microphone** input independently, performs high-fidelity speech recognition via the Google Gemini API with Indonesian, English, and mixed-language ("Indoglish") support, merges continuous speaker turns across natural pauses, and allows interactive editing and Markdown/TXT export.

---

## 🌟 Key Features

- **Non-Intrusive Audio Capture**: Works with Google Meet, Zoom, Microsoft Teams, Discord, YouTube, or VLC without requiring plugins, bots, or meeting integrations.
- **Dual-Source Control**:
  - `System Audio (Loopback)`: Captures remote participants, lectures, webinars.
  - `Microphone`: Captures your voice.
  - `Both Simultaneously`: Full two-way meeting transcription.
- **Physical Hardware Channel Separation**: 
  - Local Microphone is attributed to **`Speaker 1 (You)`**.
  - System Audio Loopback is attributed to **`Speaker 2 (Remote)`**.
  - No AI confusion or voice crossover between local and remote speech.
- **Speaker Turn Aggregation**: A pause does **not** create a new speaker block! Multiple sentences by the same speaker are merged into a single turn block. Genuine speaker transitions automatically initialize a new block.
- **Bilingual & Code-Switching**: Transcribes Indonesian, English, and technical jargon naturally.
- **Conservative AI Post-Processing**: Polishes punctuation, sentence capitalization, and obvious typos without summarizing, paraphrasing, or altering spoken meaning.
- **Secure Windows Credential Locker (DPAPI)**: API keys are encrypted in the Windows Credential Manager using the user's OS login credentials via `keyring`. No plaintext keys are ever saved to disk or repository files.
- **Modern Dashboard UI**: Built with PySide6 (Qt 6), featuring dark mode, live VU meter, session duration timer, and click-to-edit transcript cards.
- **Clean Export**: Save transcripts directly to structured **Markdown (`.md`)** or **Plain Text (`.txt`)**.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Windows System Audio        │       │       Physical Microphone       │
│       (WASAPI Loopback)         │       │          (Local User)           │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
        [Resample to 16kHz]                       [Resample to 16kHz]
                 │                                         │
     [Adaptive VAD Segmenter]                  [Adaptive VAD Segmenter]
     (Pauses >= 1.5s & Min 5s)                 (Pauses >= 1.5s & Min 5s)
                 │                                         │
                 └───────────────────┬─────────────────────┘
                                     │
                    [Google Gemini 3.5 Flash Lite STT]
                                     │
                    [Conservative AI Post-Processor]
                                     │
                     [Stateful Speaker Turn Manager]
                                     │
                       [Modern PySide6 Dashboard]
```

---

## 🚀 Getting Started

### Prerequisites
- **Windows 10 or 11 (64-bit)**
- **Python 3.11 or 3.12**
- A free **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Asharuu/Transcripter.git
   cd Transcripter
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Launch the application**:
   ```powershell
   python src/main.py
   ```

---

## ⚙️ Configuration & API Key Setup

1. Open Transcripter and click **⚙ Settings** in the left sidebar.
2. Enter your Gemini API key in the **Gemini API Key** field.
3. Click **Test Connection** to verify your key.
4. Click **Save Settings**.
5. Your key is now securely encrypted in **Windows Credential Manager (DPAPI)** under `TranscripterApp`.

---

## 🧪 Running Tests

Run the complete automated test suite (credential security, turn aggregation, VAD segmentation, and WASAPI capture):

```powershell
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

To run the live audio capture diagnostic on your active Windows hardware:
```powershell
.venv\Scripts\python tests/test_live_pipeline.py
```

---

## 🔒 Privacy & Security

- **No Raw Audio Saved by Default**: Transcripter only retains the text transcript. Raw PCM audio buffers in memory are discarded immediately after processing.
- **Zero Committed Secrets**: `.gitignore` prevents `.env`, `*.log`, `temp_audio/`, and credential files from ever entering Git history.
- **Transparent Cloud Usage**: Transcripter sends audio chunks only to the Google GenAI endpoint configured by your own API key.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
