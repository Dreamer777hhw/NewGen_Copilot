// * @FileDescription: 行为采集与指令生成插件
// * @Author: 胡皓文
// * @Date: 2025-04-01
// * @LastEditors: 胡皓文
// * @LastEditTime: 2025-04-05
// * @Contributors: 胡皓文，范起豪 


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
  const sceneManagementModal = document.getElementById('sceneManagementModal');
  const closeSceneModal = document.getElementById('closeSceneModal');
  const sceneManagementView = document.getElementById('sceneManagementView');
  const sceneEditView = document.getElementById('sceneEditView');
  const sceneList = document.getElementById('sceneList');
  const addSceneButton = document.getElementById('addSceneButton');
  const editSceneName = document.getElementById('editSceneName');
  const editScenePrompt = document.getElementById('editScenePrompt');
  const deleteSceneButton = document.getElementById('deleteSceneButton');
  const saveSceneButton = document.getElementById('saveSceneButton');
  const cancelEditButton = document.getElementById('cancelEditButton');

  let scenes = [];
  let currentEditIndex = null;

  const defaultScenes = [
    { name: '默认', prompt: '', qwenPrompt: `你是一个智能截屏分析助手。请仔细分析这个网页截图，重点关注并提取其中的文字内容，然后生成一个具体的一句话指令给Owl模型。

指令生成规则：
1. 优先识别并提取截图中的主要文字内容，不要被图片、按钮等非文本元素干扰
2. 如果截图是编程问题（如LeetCode题目），提取题目的具体名称和要求，生成"请你解释如何解决[具体题目名称]问题，要求是[具体要求]"
3. 如果截图是学术论文，提取论文的具体标题、作者或关键发现，生成"请你查找关于[具体论文标题/作者]的[具体研究发现]的详细信息"
4. 如果截图是技术文档，提取具体的技术名称、版本号和功能描述，生成"请你详细解释[具体技术名称][版本号]中的[具体功能]如何实现"
5. 如果截图是产品页面，提取产品的具体名称、型号和特点，生成"请你比较[具体产品名称][型号]与其他同类产品的区别"

直接输出一句话指令，不要有任何解释或前缀。指令必须包含截图中的具体文字信息，避免使用泛泛的描述。` },
    { name: '文档助手', prompt: '请描述文档的具体内容...', qwenPrompt: `你是一个网页内容分析助手。请简洁分析这个网页截图，识别其所属领域和主要内容。

指令生成规则：
1. 识别截图中的网页所属领域（如编程、技术文档、新闻等）
2. 简要概括网页的主要内容
3. 保持极度简洁，不超过一句话

生成的指令格式应为：考虑[领域]的[主要内容]

直接输出一句话指令，不要有任何解释或前缀。` },
    { name: '学术论文', prompt: '请描述学术论文的标题或关键发现...', qwenPrompt: `你是一个学术论文分析助手。请仔细分析这个学术论文相关网页截图，提取其中的论文标题、作者、摘要或关键发现，然后生成一个具体的指令给Owl模型。

指令生成规则：
1. 识别截图中的论文标题、作者名称、期刊名称和发表年份
2. 提取论文的研究领域、研究方法和主要发现
3. 关注论文的创新点、实验结果或理论贡献
4. 如果有图表，提取图表展示的关键数据或趋势

生成的指令格式应为：请你查找并解释关于[论文标题/作者]的[具体研究发现/方法/结论]的详细信息

直接输出一句话指令，不要有任何解释或前缀。指令必须包含截图中的具体学术信息，避免使用泛泛的描述。` },
    { name: '聚焦事件', prompt: '请描述聚焦事件的具体内容...', qwenPrompt: `你是一个新闻事件分析助手。请仔细分析这个新闻或事件相关网页截图，提取其中的事件名称、时间、地点、人物和关键细节，然后生成一个具体的指令给Owl模型。

指令生成规则：
1. 识别截图中的事件主题、发生时间和地点
2. 提取相关人物、组织或机构的名称
3. 关注事件的起因、经过和结果
4. 注意事件的社会影响或意义

生成的指令格式应为：请你查找关于[具体事件名称]的权威报道，分析事件的起因和经过，解释其中的专业术语[列出可能的专业术语]，并收集各方评价给出公平公正的分析

直接输出一句话指令，不要有任何解释或前缀。指令必须包含截图中的具体事件信息，避免使用泛泛的描述。` },
    { name: '产品页面', prompt: '请描述产品的名称、型号和特点...', qwenPrompt: `你是一个产品分析助手。请仔细分析这个产品相关网页截图，提取其中的产品名称、品牌、型号、价格和主要特点，然后生成一个具体的一句话指令给Owl模型。

指令生成规则：
1. 识别截图中的产品名称、品牌和具体型号
2. 提取产品的价格、规格和主要功能特点
3. 关注产品的技术参数、材质或设计亮点
4. 注意产品的用户评价或市场定位

生成的指令应包含产品的具体名称、型号和关键特点，例如：这是[产品名称][型号]，[关键特点]

直接输出一句话指令，不要有任何引号、解释或前缀。指令必须包含截图中的具体产品信息，避免使用泛泛的描述。` },
      { name: '旅行助手', prompt: '请描述旅行目的地和具体行程...', qwenPrompt: `你是一个旅行助手。请仔细分析这个旅行相关网页截图，提取其中的旅行目的地或景点信息，然后生成一个具体的指令给Owl模型。

指令生成规则：
1. 优先识别截图中的目的地名称或具体景点名称
2. 这个目的地的所属地区是哪里
3. 如果截图包含日期信息，将其纳入指令中
4. 如果截图包含交通方式或住宿信息，也将其纳入指令中
5. 如果截图是关于特定景点的详情，则重点关注该景点的特色和亮点

生成的指令应简洁明了，仅包含截图中实际存在的信息以及这个目的地的所属地区是哪里，例如：
- 如果只有目的地："请介绍[所在地级市][目的地名称]的旅游攻略和必游景点"
- 如果有更多信息："请提供[所在地级市][目的地名称][具体日期]旅行的建议，包括[已知的交通/住宿信息]"

直接输出一句话指令，不要有任何引号、解释或前缀。` }
  ];

  // 从存储中加载场景并填充下拉框
  chrome.storage.local.get(['scenes'], function (result) {
    scenes = result.scenes || defaultScenes;
    if (!scenes.some(scene => scene.name === '默认')) {
      scenes.unshift({ name: '默认', prompt: '' }); // 添加到列表开头
    }
    populateSceneSelector();
  });

  // 填充场景选择器
  function populateSceneSelector() {
    sceneSelector.innerHTML = ''; // 清空现有内容

    scenes.forEach((scene, index) => {
      const option = document.createElement('option');
      option.value = index; // 使用索引作为值
      option.textContent = scene.name;
      sceneSelector.appendChild(option);
    });
  }

  // 监听场景选择变化
  sceneSelector.addEventListener('change', function () {
    const selectedValue = sceneSelector.value;

    if (selectedValue !== '') {
      const selectedScene = scenes[selectedValue];
      document.getElementById('userTaskInput').value = selectedScene.prompt; // 填充补充说明
    }
  });

  // 显示场景管理弹出层
  manageScenesButton.addEventListener('click', function () {
    populateSceneList();
    sceneManagementView.style.display = 'block';
    sceneEditView.style.display = 'none';
    sceneManagementModal.style.display = 'block';
  });

  // 关闭场景管理弹出层
  closeSceneModal.addEventListener('click', function () {
    sceneManagementModal.style.display = 'none';
  });

  // 点击弹出层外部关闭
  window.addEventListener('click', function(event) {
    if (event.target == sceneManagementModal) {
      sceneManagementModal.style.display = 'none';
    }
  });

  // 填充场景列表
  function populateSceneList() {
    sceneList.innerHTML = '';
    scenes.forEach((scene, index) => {
      const sceneItem = document.createElement('div');
      sceneItem.style.display = 'flex';
      sceneItem.style.justifyContent = 'space-between';
      sceneItem.style.alignItems = 'center';
      sceneItem.style.marginBottom = '5px';
      sceneItem.style.padding = '5px';
      sceneItem.style.borderBottom = '1px solid #eee';

      const sceneName = document.createElement('span');
      sceneName.textContent = scene.name;
      sceneName.style.cursor = 'pointer';
      sceneName.style.flexGrow = '1';
      sceneName.style.color = '#333';
      sceneName.addEventListener('click', function () {
        openEditSceneView(index);
      });

      sceneItem.appendChild(sceneName);
      sceneList.appendChild(sceneItem);
    });
  }

  // 打开编辑场景视图
  function openEditSceneView(index) {
    currentEditIndex = index;
    const scene = scenes[index];
    editSceneName.value = scene.name;
    editScenePrompt.value = scene.prompt;
    
    // 添加千问Prompt编辑
    if (document.getElementById('editQwenPrompt')) {
      document.getElementById('editQwenPrompt').value = scene.qwenPrompt || '';
    } else {
      // 如果HTML中没有相应元素，可以在这里添加提示
      console.warn('未找到editQwenPrompt元素，无法编辑千问Prompt');
    }

    sceneManagementView.style.display = 'none';
    sceneEditView.style.display = 'block';
  }

  // 添加新场景
  addSceneButton.addEventListener('click', function () {
    currentEditIndex = null;
    editSceneName.value = '';
    editScenePrompt.value = '';
    
    // 添加千问Prompt编辑
    if (document.getElementById('editQwenPrompt')) {
      document.getElementById('editQwenPrompt').value = '';
    }

    sceneManagementView.style.display = 'none';
    sceneEditView.style.display = 'block';
  });

  // 保存场景
  saveSceneButton.addEventListener('click', function () {
    const name = editSceneName.value.trim();
    const prompt = editScenePrompt.value.trim();
    
    // 获取千问Prompt
    let qwenPrompt = '';
    if (document.getElementById('editQwenPrompt')) {
      qwenPrompt = document.getElementById('editQwenPrompt').value.trim();
    }

    if (!name) {
      alert('场景名称不能为空！');
      return;
    }

    if (currentEditIndex === null) {
      // 添加新场景
      scenes.push({ name, prompt, qwenPrompt });
    } else {
      // 修改现有场景
      scenes[currentEditIndex] = { name, prompt, qwenPrompt };
    }

    chrome.storage.local.set({ scenes }, function () {
      alert('场景已保存！');
      sceneEditView.style.display = 'none';
      sceneManagementView.style.display = 'block';
      populateSceneList();
      populateSceneSelector(); // 更新下拉框
    });
  });

  // 删除场景
  deleteSceneButton.addEventListener('click', function () {
    if (currentEditIndex === null) return;

    const confirmDelete = confirm('确定要删除该场景吗？');
    if (!confirmDelete) return;

    scenes.splice(currentEditIndex, 1);

    chrome.storage.local.set({ scenes }, function () {
      alert('场景已删除！');
      sceneEditView.style.display = 'none';
      sceneManagementView.style.display = 'block';
      populateSceneList();
      populateSceneSelector(); // 更新下拉框
    });
  });

  // 取消编辑，返回场景列表
  cancelEditButton.addEventListener('click', function () {
    sceneEditView.style.display = 'none';
    sceneManagementView.style.display = 'block';
  });
  
  // 从存储中恢复之前的状态
  restoreState();
  
  // 确保指令结果文本框始终可见
  instructionResult.style.display = 'block';
  instructionResult.disabled = false;
  
  // 确保操作按钮始终可见
  createActionButtons();
  
  // 确保新任务按钮始终可见
  newTaskButton.style.display = 'block';
  
  // 新任务按钮
  newTaskButton.addEventListener('click', function() {
    // 将场景选择器设置为默认场景（通常是索引0）
    sceneSelector.value = '0';
    
    // 清空当前结果
    instructionResult.disabled = false;
    instructionResult.value = '';
    
    // 清空用户输入框
    userTaskInput.value = '';
    
    // 如果当前有选择的场景，恢复该场景的提示内容
    const selectedScene = scenes[0]; // 使用默认场景
    if (selectedScene) {
      userTaskInput.value = selectedScene.prompt; // 填充补充说明
    }
    
    // 清除存储的当前指令
    chrome.storage.local.remove(['currentInstruction']);
    
    // 更新状态，场景选择改为默认
    saveState({
      hasResult: false,
      instruction: null,
      selectedSceneIndex: '0'
    });
  });

  // 截屏并生成指令按钮
  captureButton.addEventListener('click', function() {
    // 更新状态为处理中
    const statusElement = document.getElementById('status');
    statusElement.textContent = '处理中...';
    statusElement.className = 'processing';
    
    // 禁用截屏按钮，防止重复点击
    captureButton.disabled = true;
    
    // 发送消息给background.js进行截屏
    chrome.runtime.sendMessage({type: 'captureScreen'}, function(response) {
      if (response && response.success) {
        // 截屏成功，调用大模型API
        callQwenAPI(response.imageData);
      } else {
        // 更新状态为错误
        statusElement.textContent = '截屏失败';
        statusElement.className = 'error';
        
        // 启用截屏按钮
        captureButton.disabled = false;
        
        alert('截屏失败: ' + (response ? response.error : '未知错误'));
      }
    });
  });

  // 调用千问API
  function callQwenAPI(imageBase64) {
    const statusElement = document.getElementById('status');
    const instructionResult = document.getElementById('instructionResult');
    
    // 获取当前选择的场景
    const selectedSceneIndex = sceneSelector.value;
    const selectedScene = scenes[selectedSceneIndex];
    
    // 根据场景选择不同的prompt
    let prompt;
    if (selectedScene && selectedScene.qwenPrompt) {
      prompt = selectedScene.qwenPrompt;
    } else {
      // 默认prompt
      prompt = `你是一个智能截屏分析助手。请仔细分析这个网页截图，重点关注并提取其中的文字内容，然后生成一个具体的一句话指令给Owl模型。

指令生成规则：
1. 优先识别并提取截图中的主要文字内容，不要被图片、按钮等非文本元素干扰
2. 如果截图是编程问题（如LeetCode题目），提取题目的具体名称和要求，生成"请你解释如何解决[具体题目名称]问题，要求是[具体要求]"
3. 如果截图是学术论文，提取论文的具体标题、作者或关键发现，生成"请你查找关于[具体论文标题/作者]的[具体研究发现]的详细信息"
4. 如果截图是技术文档，提取具体的技术名称、版本号和功能描述，生成"请你详细解释[具体技术名称][版本号]中的[具体功能]如何实现"
5. 如果截图是产品页面，提取产品的具体名称、型号和特点，生成"请你比较[具体产品名称][型号]与其他同类产品的区别"

直接输出一句话指令，不要有任何解释或前缀。指令必须包含截图中的具体文字信息，避免使用泛泛的描述。`;
    }
    
    // 使用阿里云DashScope API (OpenAI兼容模式)
    const apiUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions';
    const apiKey = 'sk-85b3232583484cd68b1474832810edaa'; // 您的API密钥
    // const apiKey = 'YOUR-API-KEY'; // 您的API密钥
    
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
    console.log('使用场景:', selectedScene ? selectedScene.name : '默认');
    
    statusElement.textContent = '正在分析截图...';
    
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
      
      // 更新状态为成功
      statusElement.textContent = '指令生成成功';
      statusElement.className = 'success';
      
      // 启用截屏按钮
      captureButton.disabled = false;
      
      // 提取生成的指令
      const instruction = data.choices[0].message.content;
      
      instructionResult.value = instruction;
      instructionResult.disabled = false; // 确保文本框可编辑
      
      // 保存当前指令到存储
      chrome.storage.local.set({ currentInstruction: instruction });
      
      // 创建操作按钮
      createActionButtons();
      
      // 保存状态
      saveState({
        hasResult: true,
        instruction: instruction
      });
      
      // 3秒后恢复状态显示
      setTimeout(function() {
        statusElement.textContent = '正在运行';
        statusElement.className = '';
      }, 3000);
    })
    .catch(error => {
      // 更新状态为错误
      statusElement.textContent = '生成指令失败';
      statusElement.className = 'error';
      
      // 启用截屏按钮
      captureButton.disabled = false;
      
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
      instructionResult.disabled = false;
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
        alert('请先输入指令');
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
    // 获取状态元素
    const statusElement = document.getElementById('status');
    
    // 更新状态为处理中
    statusElement.textContent = '正在发送到OWL...';
    statusElement.className = 'processing';
    
    // 获取用户输入的补充说明
    const userTask = userTaskInput.value.trim();
    
    // 组合最终指令
    let finalInstruction = instruction;
    if (userTask) {
      finalInstruction = `${instruction}补充说明：${userTask}`;
    }
    
    // 获取当前选择的场景
    const selectedSceneIndex = sceneSelector.value;
    const selectedScene = scenes[selectedSceneIndex];
    const sceneName = selectedScene ? selectedScene.name : '默认';
    
    // 首先获取当前标签页的URL
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      const currentUrl = tabs[0].url;
      
      // 如果是学术论文或文档助手场景，先保存URL
      if (selectedScene && (selectedScene.name === '学术论文' || selectedScene.name === '文档助手')) {
        // 先保存URL
        fetch('http://localhost:7861/api/save_url', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            url: currentUrl
          })
        })
        .then(response => response.json())
        .then(data => {
          console.log('URL已保存:', data);
          // URL保存成功后，发送指令
          sendInstructionToOwlAPI(finalInstruction, sceneName);
        })
        .catch(error => {
          console.error('保存URL时出错:', error);
          // 即使URL保存失败，也尝试发送指令
          sendInstructionToOwlAPI(finalInstruction, sceneName);
        });
      } else {
        // 不是需要保存URL的场景，直接发送指令
        sendInstructionToOwlAPI(finalInstruction, sceneName);
      }
    });
  }

  // 实际发送指令到OWL API的函数
  function sendInstructionToOwlAPI(instruction, sceneName) {
    const statusElement = document.getElementById('status');
    
    fetch('http://localhost:7861/api/process_instruction', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        instruction: instruction,
        scene: sceneName
      })
    })
    .then(response => response.json())
    .then(data => {
      // 更新状态为成功
      statusElement.textContent = '指令已发送成功';
      statusElement.className = 'success';
      
      alert('指令已发送到OWL系统处理！');
      
      // 禁用截屏按钮，防止重复操作
      captureButton.disabled = true;
      
      // 打开结果查看器页面
      chrome.tabs.create({ url: 'http://localhost:7865' });
      
      // 3秒后恢复状态显示
      setTimeout(function() {
        statusElement.textContent = '正在运行';
        statusElement.className = '';
      }, 3000);
    })
    .catch(error => {
      // 更新状态为错误
      statusElement.textContent = '发送指令失败';
      statusElement.className = 'error';
      
      console.error('发送指令到OWL时出错:', error);
      alert('发送指令到OWL时出错，请确保OWL系统正在运行。');
      
      // 3秒后恢复状态显示
      setTimeout(function() {
        statusElement.textContent = '正在运行';
        statusElement.className = '';
      }, 3000);
    });
  }
  
  // 保存插件状态
  function saveState(state) {
    // 获取当前选择的场景索引
    const selectedSceneIndex = sceneSelector.value;
    // 获取当前用户输入的提示内容
    const userPrompt = userTaskInput.value;
    
    // 合并传入的状态、场景索引和用户提示
    const fullState = {
      ...state,
      selectedSceneIndex: selectedSceneIndex,
      userPrompt: userPrompt // 新增：保存用户输入的提示内容
    };
    
    chrome.storage.local.set({ popupState: fullState });
  }
  
  // 恢复插件状态
  function restoreState() {
    chrome.storage.local.get(['popupState', 'currentInstruction'], function(result) {
      const state = result.popupState;
      const instruction = result.currentInstruction;
      
      if (state) {
        // 恢复之前选择的场景
        if (state.selectedSceneIndex !== undefined) {
          sceneSelector.value = state.selectedSceneIndex;
          
          // 如果保存了用户提示，则恢复用户提示
          if (state.userPrompt !== undefined) {
            userTaskInput.value = state.userPrompt;
          }
          // 如果没有保存用户提示且没有结果，则填充场景的默认提示内容
          else if (!state.hasResult && state.selectedSceneIndex !== '') {
            const selectedScene = scenes[state.selectedSceneIndex];
            if (selectedScene) {
              userTaskInput.value = selectedScene.prompt;
            }
          }
        }
        
        // 恢复之前生成的指令
        if (state.hasResult && instruction) {
          instructionResult.value = instruction;
          instructionResult.disabled = false;
          
          // 创建操作按钮
          createActionButtons();
        }
      }
    });
  }
}); 