const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const serverUrlWebsocket = protocol + window.location.hostname + (window.location.port ? ':' + window.location.port : '') + '/websocket';
const logsContent = document.getElementById('logs-content');
const toggleSwitch = document.getElementById('dark-mode-toggle');
const body = document.body;

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
});

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

    // 如果滚动条在最底部，自动滚动到底部
    const atBottom = logsContent.scrollTop + logsContent.clientHeight >= logsContent.scrollHeight;
    if (atBottom) {
        logsContent.scrollTop = logsContent.scrollHeight;
    }
}

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
            logsContent.replaceChildren()
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

reconnect();