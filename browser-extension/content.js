function collectTranscript() {
  const host = location.hostname;
  if (host.includes("youtube.com")) {
    const nodes = [...document.querySelectorAll("ytd-transcript-segment-renderer")];
    const segments = nodes.map((node,i) => ({index:i,text:(node.innerText||node.textContent||"").trim().replace(/\s+/g," ")})).filter(x=>x.text);
    if (segments.length) return {site:"youtube",url:location.href,title:document.title,segments};
  }
  const selection = window.getSelection()?.toString().trim();
  return {site:host,url:location.href,title:document.title,text:selection||""};
}
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{
  if(message?.type==="EXTRACT_TRANSCRIPT") sendResponse(collectTranscript());
});