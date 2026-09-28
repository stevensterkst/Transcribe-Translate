async function sendTranscript(payload) {
  const { bridgeUrl = "http://127.0.0.1:8766", bridgeToken = "" } = await chrome.storage.local.get(["bridgeUrl", "bridgeToken"]);
  const headers = {"Content-Type": "application/json"};
  if (bridgeToken) headers["X-SS-Bridge-Token"] = bridgeToken;
  const response = await fetch(bridgeUrl.replace(/\/$/, "") + "/transcript", {
    method: "POST", headers, body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error("Bridge returned HTTP " + response.status);
  return response.json();
}
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "SEND_TRANSCRIPT") return;
  sendTranscript(message.payload).then(result => sendResponse({ok:true,result})).catch(error => sendResponse({ok:false,error:String(error)}));
  return true;
});
async function ensureOffscreen() {
  const contexts = await chrome.runtime.getContexts({});
  if (!contexts.some(c => c.contextType === "OFFSCREEN_DOCUMENT")) {
    await chrome.offscreen.createDocument({url:"offscreen.html",reasons:["USER_MEDIA"],justification:"Record user-requested browser tab audio for local transcription."});
  }
}
chrome.runtime.onMessage.addListener(async message => {
  if (message?.type !== "START_TAB_CAPTURE") return;
  const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
  if (!tab?.id) return;
  await ensureOffscreen();
  const streamId = await chrome.tabCapture.getMediaStreamId({targetTabId:tab.id});
  chrome.runtime.sendMessage({type:"START_RECORDING",target:"offscreen",streamId});
});
chrome.runtime.onMessage.addListener(async message => {
  if (message?.type === "STOP_TAB_CAPTURE") chrome.runtime.sendMessage({type:"STOP_RECORDING",target:"offscreen"});
});
