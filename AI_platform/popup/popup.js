document.addEventListener('DOMContentLoaded', function() {
  // 获取DOM元素
  const captureButton = document.getElementById('captureAndGenerate');
  const loadingIndicator = document.getElementById('loadingIndicator');
  const instructionResult = document.getElementById('instructionResult');
  const actionContainer = document.getElementById('actionContainer');
  const newTaskButton = document.getElementById('newTaskButton');
  const userTaskInput = document.getElementById('userTaskInput');

  const sceneSelector = document.getElementById('sceneSelector');
  const manageScenesButton = document.getElementById('manageScenesButton');

  // 初始化场景列表
  const defaultScenes = [
    { name: '默认', prompt: '' },
    { name: '编程问题', prompt: '请描述编程问题的具体要求...' },
    { name: '学术论文', prompt: '请描述学术论文的标题或关键发现...' },
    { name: '技术文档', prompt: '请描述技术文档的具体内容...' },
    { name: '产品页面', prompt: '请描述产品的名称、型号和特点...' }
  ];

  // 从存储中加载场景
  chrome.storage.local.get(['scenes'], function(result) {
    const scenes = result.scenes || defaultScenes;
    populateSceneSelector(scenes);
  });

  // 填充场景选择器
  function populateSceneSelector(scenes) {
    sceneSelector.innerHTML = '';
    scenes.forEach(scene => {
      const option = document.createElement('option');
      option.value = scene.prompt;
      option.textContent = scene.name;
      sceneSelector.appendChild(option);
    });
  }

  // 监听场景选择变化
  sceneSelector.addEventListener('change', function() {
    const selectedPrompt = sceneSelector.value;
    userTaskInput.value = selectedPrompt; // 自动填充补充说明
  });

  // 管理场景按钮点击事件
  manageScenesButton.addEventListener('click', function() {
    const sceneName = prompt('请输入场景名称：');
    if (!sceneName) return;

    const scenePrompt = prompt('请输入该场景的Prompt：');
    if (scenePrompt === null) return;

    chrome.storage.local.get(['scenes'], function(result) {
      const scenes = result.scenes || defaultScenes;
      scenes.push({ name: sceneName, prompt: scenePrompt });

      // 保存到存储
      chrome.storage.local.set({ scenes }, function() {
        populateSceneSelector(scenes);
        alert('场景已添加！');
      });
    });
  });
  
  // 从存储中恢复之前的状态
  restoreState();
  
  // 清除数据按钮
  document.getElementById('clearData').addEventListener('click', function() {
    chrome.storage.local.set({ behaviorData: [] }, function() {
      alert('数据已清除');
    });
  });

  // 导出数据按钮
  document.getElementById('exportData').addEventListener('click', function() {
    chrome.storage.local.get(['behaviorData'], function(result) {
      const data = result.behaviorData || [];
      const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = '行为数据_' + new Date().toISOString().slice(0,10) + '.json';
      a.click();
      
      URL.revokeObjectURL(url);
    });
  });

  // 新任务按钮
  newTaskButton.addEventListener('click', function() {
    // 清空当前结果
    instructionResult.disabled = false;
    instructionResult.value = '';
    instructionResult.style.display = 'none';
    
    // 清空操作按钮容器
    actionContainer.innerHTML = '';
    
    // 隐藏新任务按钮
    newTaskButton.style.display = 'none';
    
    // 显示截屏按钮
    captureButton.disabled = false;
    
    // 清空用户输入框
    userTaskInput.value = '';
    
    // 清除存储的当前指令
    chrome.storage.local.remove(['currentInstruction']);
    
    // 更新状态
    saveState({
      hasResult: false,
      instruction: null
    });
  });

  // 截屏并生成指令按钮
  captureButton.addEventListener('click', function() {
    loadingIndicator.style.display = 'block';
    instructionResult.style.display = 'none';
    
    // 发送消息给background.js进行截屏
    chrome.runtime.sendMessage({type: 'captureScreen'}, function(response) {
      if (response && response.success) {
        // 截屏成功，调用大模型API
        callQwenAPI(response.imageData);
      } else {
        loadingIndicator.style.display = 'none';
        alert('截屏失败: ' + (response ? response.error : '未知错误'));
      }
    });
  });

  // 调用千问API
  function callQwenAPI(imageBase64) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    const instructionResult = document.getElementById('instructionResult');
    
    // 构建发送给千问的prompt
    const prompt = `你是一个智能截屏分析助手。请仔细分析这个网页截图，重点关注并提取其中的文字内容，然后生成一个具体的一句话指令给Owl模型。

指令生成规则：
1. 优先识别并提取截图中的主要文字内容，不要被图片、按钮等非文本元素干扰
2. 如果截图是编程问题（如LeetCode题目），提取题目的具体名称和要求，生成"请你解释如何解决[具体题目名称]问题，要求是[具体要求]"
3. 如果截图是学术论文，提取论文的具体标题、作者或关键发现，生成"请你查找关于[具体论文标题/作者]的[具体研究发现]的详细信息"
4. 如果截图是技术文档，提取具体的技术名称、版本号和功能描述，生成"请你详细解释[具体技术名称][版本号]中的[具体功能]如何实现"
5. 如果截图是产品页面，提取产品的具体名称、型号和特点，生成"请你比较[具体产品名称][型号]与其他同类产品的区别"

直接输出一句话指令，不要有任何解释或前缀。指令必须包含截图中的具体文字信息，避免使用泛泛的描述。`;
    
    // 使用阿里云DashScope API (OpenAI兼容模式)
    const apiUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions';
    const apiKey = 'sk-3f855bc5d6b34f2fba9a2491cff46b61'; // 您的API密钥
    
    // 修正请求格式
    const requestData = {
      model: 'qwen-vl-plus',
      messages: [
        {
          role: 'user',
          content: [
            { type: 'text', text: prompt },
            { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${imageBase64}` } }
          ]
        }
      ],
      temperature: 0.7,
      max_tokens: 300
    };
    
    console.log('发送API请求...');
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + apiKey
      },
      body: JSON.stringify(requestData)
    })
    .then(response => {
      console.log('收到API响应状态:', response.status);
      if (!response.ok) {
        return response.text().then(text => {
          console.error('API错误响应详情:', text);
          throw new Error('API请求失败: ' + response.status);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('API响应数据:', data);
      loadingIndicator.style.display = 'none';
      
      // 提取生成的指令
      const instruction = data.choices[0].message.content;
      
      instructionResult.value = instruction;
      instructionResult.style.display = 'block';
      instructionResult.disabled = false; // 确保文本框可编辑
      
      // 保存当前指令到存储
      chrome.storage.local.set({ currentInstruction: instruction });
      
      // 创建操作按钮
      createActionButtons();
      
      // 显示新任务按钮
      newTaskButton.style.display = 'block';
      
      // 保存状态
      saveState({
        hasResult: true,
        instruction: instruction
      });
    })
    .catch(error => {
      loadingIndicator.style.display = 'none';
      let errorMessage = '生成指令时发生错误';
      
      if (error.response) {
        // 服务器返回了错误响应
        errorMessage += `: ${error.response.status} - ${error.response.statusText}`;
        console.error('API响应错误:', error.response);
      } else if (error.request) {
        // 请求已发送但没有收到响应
        errorMessage += ': 服务器无响应';
        console.error('API请求无响应:', error.request);
      } else {
        // 请求设置时出错
        errorMessage += `: ${error.message}`;
        console.error('API请求设置错误:', error.message);
      }
      
      instructionResult.value = errorMessage;
      instructionResult.style.display = 'block';
      console.error('API调用详细错误:', error);
    });
  }
  
  // 创建操作按钮
  function createActionButtons() {
    // 清空操作按钮容器
    actionContainer.innerHTML = '';
    
    // 创建发送到OWL的按钮
    const sendToOwlButton = document.createElement('button');
    sendToOwlButton.textContent = '发送到OWL处理';
    sendToOwlButton.className = 'action-button';
    sendToOwlButton.onclick = function() {
      const editedInstruction = instructionResult.value.trim();
      if (editedInstruction) {
        sendInstructionToOwl(editedInstruction);
      } else {
        alert('请先生成或输入指令');
      }
    };
    
    // 创建复制按钮
    const copyButton = document.createElement('button');
    copyButton.textContent = '复制指令';
    copyButton.className = 'action-button';
    copyButton.onclick = function() {
      // 直接从文本框获取可能已编辑的指令
      const editedInstruction = instructionResult.value.trim();
      if (editedInstruction) {
        navigator.clipboard.writeText(editedInstruction)
          .then(() => {
            alert('指令已复制到剪贴板');
          })
          .catch(err => {
            console.error('复制失败:', err);
          });
      } else {
        alert('没有可复制的指令');
      }
    };
    
    // 将按钮添加到容器
    actionContainer.appendChild(sendToOwlButton);
    actionContainer.appendChild(copyButton);
  }
  
  // 发送指令到OWL系统
  function sendInstructionToOwl(instruction) {
    // 获取用户输入的补充说明
    const userTask = userTaskInput.value.trim();
    
    // 组合最终指令
    let finalInstruction = instruction;
    if (userTask) {
      finalInstruction = `${instruction}。补充说明：${userTask}`;
    }
    
    fetch('http://localhost:7861/api/process_instruction', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        instruction: finalInstruction
      })
    })
    .then(response => response.json())
    .then(data => {
      alert('指令已发送到OWL系统处理！');
      
      // 禁用截屏按钮，防止重复操作
      captureButton.disabled = true;
      
      // 打开结果查看器页面
      chrome.tabs.create({ url: 'http://localhost:7865' });
    })
    .catch(error => {
      console.error('发送指令到OWL时出错:', error);
      alert('发送指令到OWL时出错，请确保OWL系统正在运行。');
    });
  }
  
  // 保存插件状态
  function saveState(state) {
    chrome.storage.local.set({ popupState: state });
  }
  
  // 恢复插件状态
  function restoreState() {
    chrome.storage.local.get(['popupState', 'currentInstruction'], function(result) {
      const state = result.popupState;
      const instruction = result.currentInstruction;
      
      if (state && state.hasResult && instruction) {
        // 恢复指令显示（使用value而不是textContent）
        instructionResult.value = instruction;
        instructionResult.style.display = 'block';
        instructionResult.disabled = false; // 确保文本框可编辑
        
        // 创建操作按钮
        createActionButtons();
        
        // 显示新任务按钮
        newTaskButton.style.display = 'block';
      }
    });
  }
}); 