// 处理来自content.js的行为数据和其他消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[DEBUG] Received message:', message);
  
  if (message.type === 'dom_change' || message.type === 'click') {
    // 存储行为数据
    chrome.storage.local.get(['behaviorData'], result => {
      const newData = result.behaviorData || [];
      newData.push({
        timestamp: new Date().toISOString(),
        type: message.type,
        details: message
      });
      chrome.storage.local.set({ behaviorData: newData });
    });
  } else if (message.type === 'captureScreen') {
    // 处理截屏请求
    captureCurrentTab(sendResponse);
    return true; // 保持消息通道开放，以便异步响应
  }
});

// 截取当前标签页的屏幕
function captureCurrentTab(sendResponse) {
  chrome.tabs.captureVisibleTab(null, {format: 'jpeg', quality: 70}, function(dataUrl) {
    if (chrome.runtime.lastError) {
      console.error('截屏错误:', chrome.runtime.lastError);
      sendResponse({success: false, error: chrome.runtime.lastError.message});
      return;
    }
    
    // 从dataUrl中提取Base64数据
    const base64Data = dataUrl.replace(/^data:image\/jpeg;base64,/, '');
    
    // 检查Base64数据是否有效
    if (!base64Data || !/^[A-Za-z0-9+/=]+$/.test(base64Data)) {
      console.error('无效的Base64数据');
      sendResponse({success: false, error: '无效的Base64数据'});
      return;
    }
    
    console.log('截屏成功，数据长度:', base64Data.length);
    sendResponse({success: true, imageData: base64Data});
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    console.log('[DEBUG] Received message:', msg)
});