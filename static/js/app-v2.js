// Простой и надёжный монитор - ОДНА ФУНКЦИЯ ДЛЯ ВСЕГО
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM загружен! Начинаем работу...');
    
    // Основная и ЕДИНСТВЕННАЯ функция обновления
    async function updateDashboard() {
        console.log('🔁 Обновление данных начато...');
        
        try {
            // 1. Получаем системные данные
            const systemRes = await fetch('/api/system');
            const systemData = await systemRes.json();
            
            // Обновляем CPU, RAM, Disk
            document.getElementById('cpu').textContent = systemData.cpu_percent.toFixed(1) + '%';
            document.getElementById('ram').textContent = systemData.memory_percent.toFixed(1) + '%';
            document.getElementById('disk').textContent = systemData.disk_percent.toFixed(1) + '%';
            
            // Прогресс-бары
            document.getElementById('cpu-bar').style.width = systemData.cpu_percent + '%';
            document.getElementById('ram-bar').style.width = systemData.memory_percent + '%';
            document.getElementById('disk-bar').style.width = systemData.disk_percent + '%';
            
            // Информация о системе
            document.getElementById('system').textContent = systemData.system;
            
            // Время работы
            const bootTime = new Date(systemData.boot_time);
            const uptimeMs = Date.now() - bootTime.getTime();
            const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
            const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
            document.getElementById('uptime').textContent = hours + 'ч ' + minutes + 'м';
            
            console.log('✅ Системные данные обновлены: CPU ' + systemData.cpu_percent.toFixed(1) + '%');
            
        } catch (systemError) {
            console.error('❌ Ошибка системных данных:', systemError);
        }
        
        try {
            // 2. Получаем Wi-Fi данные (ПЕРВАЯ карточка)
            const wifiRes = await fetch('/api/wifi');
            const wifiData = await wifiRes.json();

            // Обрабатываем разные статусы
            const statusElement = document.getElementById('connection-status');
            const signalElement = document.getElementById('wifi-signal-main');
            const barElement = document.getElementById('wifi-bar-main');

            switch(wifiData.status) {
                case 'connected':
                    // Всё подключено - обычный режим
                    document.getElementById('wifi-channel-main').textContent = wifiData.channel || 'Не определен';
                    signalElement.textContent = wifiData.signal || '0';
                    barElement.style.width = (wifiData.signal || 0) + '%';
                    document.getElementById('wifi-network-main').textContent = wifiData.network || 'Неизвестно';
                    document.getElementById('wifi-ip-main').textContent = wifiData.ip || 'Нет IP';
        
                    statusElement.textContent = '● Активно';
                    statusElement.className = 'connection-status active';
                    document.getElementById('connection-type').textContent = 'Wi-Fi';
        
                    console.log('✅ Wi-Fi подключен: ' + wifiData.network);
                    break;
        
                case 'no_connection':
                    // Wi-Fi адаптер есть, но нет сети
                    signalElement.textContent = '0';
                    barElement.style.width = '0%';
                    document.getElementById('wifi-network-main').textContent = 'Нет подключения';
                    document.getElementById('wifi-ip-main').textContent = '—';
        
                    statusElement.textContent = '● Не активно';
                    statusElement.className = 'connection-status inactive';
                    document.getElementById('connection-type').textContent = 'Wi-Fi';
        
                    console.log('⚠️ Wi-Fi адаптер есть, но нет подключения');
                    break;
        
                case 'disconnected':
                    // Wi-Fi отключен полностью
                    signalElement.textContent = '0';
                    barElement.style.width = '0%';
                    document.getElementById('wifi-network-main').textContent = 'Wi-Fi отключен';
                    document.getElementById('wifi-ip-main').textContent = '—';
        
                    statusElement.textContent = '✗ Отключен';
                    statusElement.className = 'connection-status disabled';
                    document.getElementById('connection-type').textContent = 'Беспроводная сеть';
        
                    console.log('⚠️ Wi-Fi отключен');
                    break;
        
                default: // error или неизвестный статус
                    signalElement.textContent = '0';
                    barElement.style.width = '0%';
                    document.getElementById('wifi-network-main').textContent = 'Ошибка';
                    document.getElementById('wifi-ip-main').textContent = '—';
        
                    statusElement.textContent = '⚠️ Ошибка';
                    statusElement.className = 'connection-status error';
                    document.getElementById('connection-type').textContent = '—';
        
                    console.error('❌ Ошибка Wi-Fi данных:', wifiData);
            }

        } catch (wifiError) {  // ← ЭТОЙ СТРОКИ НЕТ в твоём коде
            console.error('❌ Ошибка Wi-Fi данных:', wifiError);
            // Показываем ошибку пользователю
            document.getElementById('connection-status').textContent = '⚠️ Ошибка';
            document.getElementById('connection-status').className = 'connection-status error';
        } 

        try {
            // 3. Получаем сетевые подключения (ВТОРАЯ карточка)
            const networkRes = await fetch('/api/network-connections');
            const connections = await networkRes.json();
            
            // Находим активное Wi-Fi подключение
            const activeWifi = connections.find(conn => 
                conn.type === 'wifi' && conn.status === 'up'
            );
            
            if (activeWifi) {
                // Обновляем вторую карточку (детали сети)
                document.getElementById('interface-name').textContent = activeWifi.name;
                document.getElementById('network-speed').textContent = activeWifi.speed;
                document.getElementById('mac-address').textContent = activeWifi.mac;
                document.getElementById('bytes-sent').textContent = activeWifi.sent_human;
                document.getElementById('bytes-recv').textContent = activeWifi.recv_human;
                
                console.log('✅ Сетевые данные обновлены: ' + activeWifi.name);
            } else {
                // ЕСЛИ WI-FI НЕ НАЙДЕН - показываем сообщение
                document.getElementById('interface-name').textContent = 'Wi-Fi не активен';
                document.getElementById('network-speed').textContent = '—';
                document.getElementById('mac-address').textContent = '—';
                document.getElementById('bytes-sent').textContent = '0 B';
                document.getElementById('bytes-recv').textContent = '0 B';
    
                console.log('⚠️ Активное Wi-Fi подключение не найдено');
            }
            
        } catch (networkError) {
            console.error('❌ Ошибка сетевых данных:', networkError);
        }
        
        try {
            // 4. Получаем процессы
            const processesRes = await fetch('/api/processes');
            const processesData = await processesRes.json();
            
            const tbody = document.querySelector('#process-table tbody');
            tbody.innerHTML = '';
            
            // Только первые 5 процессов
            processesData.processes.slice(0, 5).forEach(proc => {
                const row = document.createElement('tr');
                const cpuPercent = proc.cpu_percent ? proc.cpu_percent.toFixed(1) : '0.0';
                
                row.innerHTML = `<td>${proc.pid}</td>
                                <td>${proc.name || 'Без имени'}</td>
                                <td>${cpuPercent}%</td>`;
                tbody.appendChild(row);
            });
            
            console.log('✅ Процессы обновлены');
            
        } catch (processError) {
            console.error('❌ Ошибка процессов:', processError);
        }
        
        // Обновляем время
        const now = new Date();
        document.getElementById('time').textContent = now.toLocaleTimeString();
        document.getElementById('last-update').textContent = 'Последнее обновление: ' + now.toLocaleTimeString();
        
        console.log('✅ Все данные обновлены в ' + now.toLocaleTimeString());
    }
    
    // Запускаем сразу
    updateDashboard();
    
    // И каждые 2 секунды
    setInterval(updateDashboard, 2000);
    
    // Клик на карточку = обновление
    document.addEventListener('click', function(e) {
        if (e.target.closest('.card')) {
            console.log('🖱️ Обновление по клику');
            updateDashboard();
        }
    });
    
    console.log('🚀 Мой Серверный Монитор ЗАПУЩЕН!');
});