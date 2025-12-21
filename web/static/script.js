const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const serverUrlWebsocket = protocol + window.location.hostname + (window.location.port ? ':' + window.location.port : '') + '/websocket';
const logsContent = document.getElementById('logs-content');
const toggleSwitch = document.getElementById('dark-mode-toggle');
const body = document.body;

// 初始化日志顶栏
function initLogsHeader() {
    if (!logsContent) return;
    
    // 检查日志顶栏是否存在
    let logsHeader = document.getElementById('logs-header');
    
    if (!logsHeader) {
        // 创建日志顶栏
        logsHeader = document.createElement('div');
        logsHeader.id = 'logs-header';
        logsHeader.className = 'logs-header';
        
        // 创建展开/收起日志选项按钮
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'toggle-logs-header';
        toggleBtn.className = 'toggle-logs-header-btn';
        toggleBtn.title = '展开/收起日志选项';
        
        // 创建向下箭头
        const arrowDown = document.createElement('span');
        arrowDown.className = 'arrow-down';
        toggleBtn.appendChild(arrowDown);
        
        // 创建日志选项容器
        const logsOptions = document.createElement('div');
        logsOptions.id = 'logs-options';
        logsOptions.className = 'logs-options';
        
        // 创建日志选项
        const options = [
            { id: 'show-debug', label: 'Debug', checked: true },
            { id: 'show-info', label: 'Info', checked: true },
            { id: 'show-warn', label: 'Warn', checked: true },
            { id: 'show-error', label: 'Error', checked: true }
        ];
        
        options.forEach(option => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = option.id;
            checkbox.checked = option.checked;
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(` ${option.label}`));
            logsOptions.appendChild(label);
        });
        
        // 将元素添加到日志顶栏
        logsHeader.appendChild(toggleBtn);
        logsHeader.appendChild(logsOptions);
        
        // 将日志顶栏添加到日志内容容器的开头
        logsContent.insertBefore(logsHeader, logsContent.firstChild);
    }
    
    // 获取元素（重新获取，因为可能是新创建的）
    const toggleBtn = document.getElementById('toggle-logs-header');
    
    // 移除旧的事件监听器，防止多次绑定
    toggleBtn.removeEventListener('click', toggleLogsHeader);
    
    // 定义展开/收起日志选项的函数
    function toggleLogsHeader() {
        logsHeader.classList.toggle('expanded');
    }
    
    // 绑定展开/收起日志选项的事件
    toggleBtn.addEventListener('click', toggleLogsHeader);
}

// 初始化日志过滤器
function initLogsFilter() {
    // 获取元素
    const showDebug = document.getElementById('show-debug');
    const showInfo = document.getElementById('show-info');
    const showWarn = document.getElementById('show-warn');
    const showError = document.getElementById('show-error');
    
    if (!showDebug || !showInfo || !showWarn || !showError) return;
    
    // 过滤日志的函数
    function filterLogs() {
        const debugVisible = showDebug.checked;
        const infoVisible = showInfo.checked;
        const warnVisible = showWarn.checked;
        const errorVisible = showError.checked;
        
        // 获取所有日志条目
        const logEntries = document.querySelectorAll('.log-entry');
        
        logEntries.forEach(entry => {
            const isDebug = entry.classList.contains('deb');
            const isInfo = entry.classList.contains('inf');
            const isWarn = entry.classList.contains('war');
            const isError = entry.classList.contains('err');
            
            // 根据日志级别和选中状态决定是否显示
            let shouldShow = false;
            if (isDebug && debugVisible) shouldShow = true;
            if (isInfo && infoVisible) shouldShow = true;
            if (isWarn && warnVisible) shouldShow = true;
            if (isError && errorVisible) shouldShow = true;
            
            entry.style.display = shouldShow ? 'block' : 'none';
        });
    }
    
    // 绑定过滤事件
    showDebug.addEventListener('change', filterLogs);
    showInfo.addEventListener('change', filterLogs);
    showWarn.addEventListener('change', filterLogs);
    showError.addEventListener('change', filterLogs);
    
    // 初始过滤
    filterLogs();
}

// 初始化滚动按钮
function initScrollButton() {
    if (!logsContent) return;
    
    // 检查滚动按钮是否存在
    let scrollButton = document.getElementById('scroll-to-bottom');
    
    if (!scrollButton) {
        // 创建滚动按钮
        scrollButton = document.createElement('button');
        scrollButton.id = 'scroll-to-bottom';
        scrollButton.className = 'scroll-to-bottom-btn';
        scrollButton.title = '滚动到底部';
        scrollButton.innerHTML = '<span class="arrow-down"></span>';
        scrollButton.onclick = function() {
            logsContent.scrollTop = logsContent.scrollHeight;
        };
        
        // 添加到日志内容容器
        logsContent.appendChild(scrollButton);
    }
    
    // 动态计算并更新滚动按钮的位置
    function updateScrollButtonPosition() {
        const logsRect = logsContent.getBoundingClientRect();
        scrollButton.style.position = 'fixed';
        scrollButton.style.left = `${logsRect.right - 70}px`; // 70px = 50px (按钮宽度) + 20px (右侧边距)
        scrollButton.style.top = `${logsRect.bottom - 70}px`; // 70px = 50px (按钮高度) + 20px (底部边距)
    }
    
    // 重新绑定点击事件
    scrollButton.onclick = function() {
        logsContent.scrollTop = logsContent.scrollHeight;
    };
    
    // 初始计算滚动按钮的位置
    updateScrollButtonPosition();
    
    // 当窗口大小改变或页面滚动时，更新滚动按钮的位置
    window.addEventListener('resize', updateScrollButtonPosition);
    window.addEventListener('scroll', updateScrollButtonPosition);
    
    // 当日志内容容器滚动时，更新滚动按钮的位置
    logsContent.addEventListener('scroll', updateScrollButtonPosition);
}

// 初始化页面
document.getElementById('status-page').classList.add('active');
setInterval(function() {
    const serviceDiv = document.getElementById('service-status');
    fetch('/api/services_status')
        .then(response => response.json())
        .then(data => {
            const fragment = document.createDocumentFragment();
            for (const serviceName in data) {
                if (data.hasOwnProperty(serviceName)) {
                    const status = data[serviceName];
                    const p = document.createElement('p');
                    p.textContent = `${serviceName}: ${status ? 'Alive' : 'Dead'}`;
                    fragment.appendChild(p);
                }
            }
            serviceDiv.replaceChildren(fragment);
        })
        .catch(error => console.error('Error fetching service status:', error));
}, 1000);

// 检查是否有本地存储的模式设置
const currentMode = localStorage.getItem('mode');
if (currentMode === 'dark') {
    body.classList.add('dark-mode');
    toggleSwitch.checked = true;
}

toggleSwitch.addEventListener('change', function () {
    if (toggleSwitch.checked) {
        // 切换到黑夜模式
        body.classList.add('dark-mode');
        localStorage.setItem('mode', 'dark');
    } else {
        // 切换到白天模式
        body.classList.remove('dark-mode');
        localStorage.setItem('mode', 'light');
    }
});

// 切换页面
document.getElementById('status-link').addEventListener('click', function() {
    document.getElementById('status-page').classList.add('active');
    document.getElementById('logs-page').classList.remove('active');
});

document.getElementById('logs-link').addEventListener('click', function() {
    document.getElementById('status-page').classList.remove('active');
    document.getElementById('logs-page').classList.add('active');
    
    // 确保滚动按钮存在
    initScrollButton();
    
    // 立即执行一次滚动到底部
    logsContent.scrollTop = logsContent.scrollHeight;
    
    // 监听滚动事件，当用户手动滚动时停止自动滚动
    let autoScrollEnabled = true;
    
    function handleScroll() {
        // 检查用户是否手动滚动
        const isAtBottom = logsContent.scrollTop + logsContent.clientHeight >= logsContent.scrollHeight - 10;
        if (!isAtBottom) {
            autoScrollEnabled = false;
        }
    }
    
    logsContent.addEventListener('scroll', handleScroll);
    
    // 在之后的1秒内，每200ms执行一次滚动到底部，确保所有日志内容都加载完成
    let count = 0;
    const scrollInterval = setInterval(() => {
        if (autoScrollEnabled) {
            logsContent.scrollTop = logsContent.scrollHeight;
        }
        count++;
        if (count >= 5) {
            clearInterval(scrollInterval);
            logsContent.removeEventListener('scroll', handleScroll);
        }
    }, 200);
});

// 初始化滚动到底部按钮事件 - 移到initScrollButton函数中处理

// 初始化时如果日志页面是激活状态，滚动到底部
if (document.getElementById('logs-page').classList.contains('active')) {
    const initScrollInterval = setInterval(() => {
        if (logsContent.scrollHeight > 0) {
            logsContent.scrollTop = logsContent.scrollHeight;
            clearInterval(initScrollInterval);
        }
    }, 50);
}

function addLogEntry(message) {
    const logEntry = document.createElement('p');
    logEntry.className = 'log-entry';

    // 根据日志信息的类型添加样式
    if (message.startsWith('[DEB]')) {
        logEntry.classList.add('deb');
    } else if (message.startsWith('[INF]')) {
        logEntry.classList.add('inf');
    } else if (message.startsWith('[WAR]')) {
        logEntry.classList.add('war');
    } else if (message.startsWith('[ERR]')) {
        logEntry.classList.add('err');
    }

    logEntry.textContent = message;
    logsContent.appendChild(logEntry);

    // 始终自动滚动到底部
    logsContent.scrollTop = logsContent.scrollHeight;
}

// 监听日志内容变化，自动滚动到底部
const observer = new MutationObserver(() => {
    logsContent.scrollTop = logsContent.scrollHeight;
});

observer.observe(logsContent, {
    childList: true,
    subtree: true
});

function reconnect() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('reconnect-button').style.display = 'none';
    document.getElementById('reconnect-status').innerText = '';

    function disconnected() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('connected').innerText = '未连接';
        document.getElementById('reconnect-button').style.display = 'inline';
        document.getElementById('reconnect-status').innerText = '连接失败';
    }

    try {
        let socket = new WebSocket(serverUrlWebsocket);
        socket.onopen = function () {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('connected').innerText = '已连接';
            document.getElementById('reconnect-button').style.display = 'none';
            document.getElementById('reconnect-status').innerText = '';
            
            // 保存滚动按钮元素
            const scrollButton = document.getElementById('scroll-to-bottom');
            
            // 清空日志内容容器
            logsContent.replaceChildren();
            
            // 重新添加日志顶栏
            initLogsHeader();
            
            // 创建实际日志容器
            const actualLogs = document.createElement('div');
            actualLogs.id = 'actual-logs';
            actualLogs.className = 'actual-logs';
            logsContent.appendChild(actualLogs);
            
            // 重新添加滚动按钮
            if (scrollButton) {
                logsContent.appendChild(scrollButton);
            } else {
                // 如果滚动按钮不存在，重新创建
                initScrollButton();
            }
            
            // 重新初始化日志过滤器
            initLogsFilter();
            
            // WebSocket连接成功后，如果当前是日志页面，滚动到底部
            if (document.getElementById('logs-page').classList.contains('active')) {
                logsContent.scrollTop = logsContent.scrollHeight;
            }
        };

        socket.onmessage = function (evt) {
            addLogEntry(evt.data)
        };

        socket.onclose = disconnected

        socket.onerror = function (error) {
            console.error('Reconnection error:', error);
            disconnected();
        };
    } catch (error) {
        console.error('Reconnection attempt failed:', error);
        document.getElementById('reconnect-status').innerText = '重连失败';
        disconnected();
    }
}

// 页面加载完成后初始化所有组件
function initAllComponents() {
    initLogsHeader();
    
    // 创建实际日志容器（如果不存在）
    let actualLogs = document.getElementById('actual-logs');
    if (!actualLogs) {
        actualLogs = document.createElement('div');
        actualLogs.id = 'actual-logs';
        actualLogs.className = 'actual-logs';
        
        // 将现有日志条目移动到实际日志容器
        const existingLogs = logsContent.querySelectorAll('.log-entry');
        logsContent.appendChild(actualLogs);
        existingLogs.forEach(logEntry => {
            actualLogs.appendChild(logEntry);
        });
    }
    
    initLogsFilter();
    initScrollButton();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllComponents);
} else {
    initAllComponents();
}

// 修改addLogEntry函数，确保新添加的日志条目也会被正确过滤
function addLogEntry(message) {
    const logEntry = document.createElement('p');
    logEntry.className = 'log-entry';

    // 根据日志信息的类型添加样式
    if (message.startsWith('[DEB]')) {
        logEntry.classList.add('deb');
    } else if (message.startsWith('[INF]')) {
        logEntry.classList.add('inf');
    } else if (message.startsWith('[WAR]')) {
        logEntry.classList.add('war');
    } else if (message.startsWith('[ERR]')) {
        logEntry.classList.add('err');
    }

    logEntry.textContent = message;
    
    // 获取实际日志容器
    const actualLogs = document.getElementById('actual-logs') || logsContent;
    actualLogs.appendChild(logEntry);

    // 始终自动滚动到底部
    logsContent.scrollTop = logsContent.scrollHeight;
    
    // 应用日志过滤
    const showDebug = document.getElementById('show-debug');
    const showInfo = document.getElementById('show-info');
    const showWarn = document.getElementById('show-warn');
    const showError = document.getElementById('show-error');
    
    if (showDebug && showInfo && showWarn && showError) {
        const debugVisible = showDebug.checked;
        const infoVisible = showInfo.checked;
        const warnVisible = showWarn.checked;
        const errorVisible = showError.checked;
        
        const isDebug = logEntry.classList.contains('deb');
        const isInfo = logEntry.classList.contains('inf');
        const isWarn = logEntry.classList.contains('war');
        const isError = logEntry.classList.contains('err');
        
        // 根据日志级别和选中状态决定是否显示
        let shouldShow = false;
        if (isDebug && debugVisible) shouldShow = true;
        if (isInfo && infoVisible) shouldShow = true;
        if (isWarn && warnVisible) shouldShow = true;
        if (isError && errorVisible) shouldShow = true;
        
        logEntry.style.display = shouldShow ? 'block' : 'none';
    }
}

reconnect();