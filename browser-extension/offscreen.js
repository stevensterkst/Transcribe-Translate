let recorder=null,chunks=[],stream=null;
chrome.runtime.onMessage.addListener(async message=>{
 if(message?.type!=="START_RECORDING"||message.target!=="offscreen")return;
 stream=await navigator.mediaDevices.getUserMedia({audio:{mandatory:{chromeMediaSource:"tab",chromeMediaSourceId:message.streamId}},video:{mandatory:{chromeMediaSource:"tab",chromeMediaSourceId:message.streamId}}});
 const output=new AudioContext(); output.createMediaStreamSource(stream).connect(output.destination);
 chunks=[]; recorder=new MediaRecorder(stream,{mimeType:"audio/webm;codecs=opus"});
 recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
 recorder.start(1000);
});
chrome.runtime.onMessage.addListener(async message => {
 if(message?.type!=="STOP_RECORDING"||message.target!=="offscreen"||!recorder)return;
 recorder.stop();
});
