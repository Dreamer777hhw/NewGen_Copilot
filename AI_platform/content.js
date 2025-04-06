// * @FileDescription: 插件内容脚本
// * @Author: 胡皓文
// * @Date: 2025-04-01
// * @LastEditors: 胡皓文
// * @LastEditTime: 2025-04-01
// * @Contributors: 胡皓文 


// 监听DOM变化 - 添加错误处理
/*
const observer = new MutationObserver(mutations => {
  try {
    mutations.forEach(mutation => {
      if (mutation.type === 'childList') {
        chrome.runtime.sendMessage({
          type: 'dom_change',
          target: mutation.target ? mutation.target.nodeName : 'unknown',
          addedNodes: mutation.addedNodes ? mutation.addedNodes.length : 0
        });
      }
    });
  } catch (error) {
    console.error('DOM观察器错误:', error);
  }
});
*/

// 监听点击事件 - 添加错误处理
/*
document.addEventListener('click', e => {
  try {
    // 获取点击元素的文本内容
    const textContent = e.target.textContent?.trim() || '';
    
    chrome.runtime.sendMessage({
      type: 'click',
      xpath: getXPath(e.target),
      text: textContent,
      timestamp: Date.now()
    });
  } catch (error) {
    console.error('点击事件处理错误:', error);
  }
});
*/

// 获取元素XPath - 增强错误处理
function getXPath(element) {
  try {
    if (!element) return '';
    if (element.id) return `//*[@id="${element.id}"]`;
    if (element === document.body) return element.tagName;
    if (!element.parentNode) return '';
    
    let ix = 0;
    const siblings = element.parentNode?.childNodes || [];
    for (let i = 0; i < siblings.length; i++) {
      const sibling = siblings[i];
      if (sibling === element) 
        return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
      if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
        ix++;
    }
    return '';
  } catch (error) {
    console.error('XPath生成错误:', error);
    return '';
  }
}

// 检查元素是否可见
function isElementVisible(element) {
  if (!element) return false;
  
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && 
         style.visibility !== 'hidden' && 
         style.opacity !== '0' &&
         element.offsetWidth > 0 && 
         element.offsetHeight > 0;
}

// 提取页面中的文本片段
function extractTextFragments() {
  try {
    const textNodes = [];
    const textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, div, a, li, td, th');
    
    textElements.forEach(element => {
      const text = element.textContent?.trim();
      if (text && text.length > 5) { // 只收集有意义的文本片段
        // 清理文本，移除特殊字符
        const cleanedText = text.replace(/[\uD800-\uDFFF]|[\u0080-\u009F]|[\u2000-\u20FF]|[\uE000-\uF8FF]/g, '');
        
        textNodes.push({
          text: cleanedText,
          xpath: getXPath(element),
          tag: element.tagName.toLowerCase(),
          isVisible: isElementVisible(element)
        });
      }
    });
    
    chrome.runtime.sendMessage({
      type: 'text_fragments',
      fragments: textNodes,
      timestamp: Date.now(),
      url: window.location.href,
      title: document.title
    });
  } catch (error) {
    console.error('文本提取错误:', error);
  }
}

// 页面加载完成后的处理
/*
window.addEventListener('load', () => {
  setTimeout(extractTextFragments, 1000); // 延迟1秒执行，确保页面完全加载
});

// 定期提取文本（每10秒）
setInterval(extractTextFragments, 10000);
*/

// 监听来自background.js的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'instructionGenerated') {
    // 可以在页面上显示生成的指令，或者执行其他操作
    console.log('生成的指令:', message.instruction);
  } else if (message.type === 'extractText') {
    // 按需提取文本
    extractTextFragments();
    sendResponse({success: true});
    return true;
  }
});

// 不启动DOM观察器
/*
// 配置观察器
const config = { childList: true, subtree: true };
// 启动观察器
observer.observe(document.body, config);
*/

console.log('内容脚本已加载 - 行为记录功能已禁用');