# SS Transcribe-Translate Browser Bridge

Manifest V3 Chrome/Edge extension.

Transcript extraction:
- YouTube visible transcript segments are extracted from the page DOM.
- Other sites can send selected page text.
- Data is sent to the local desktop bridge at 127.0.0.1:8766.
- Universal site compatibility is not claimed.

Tab audio:
- User-triggered tab capture uses Chrome's tabCapture API and an offscreen document.
- Captured audio is routed back to the speakers so capture does not silently mute the tab.
- The recording handoff into the desktop pipeline is a separate implementation step and is not falsely claimed complete.

Load the directory as an unpacked extension in Chrome/Edge and configure the bridge URL/token in extension options.