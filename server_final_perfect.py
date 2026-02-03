from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import psutil
from psutil import AF_LINK
import platform
import socket # Для работы с сетевыми адресами
# socket.AF_INET нужен для идентификации IPv4 адресов
from datetime import datetime
from fastapi.staticfiles import StaticFiles
import subprocess

app = FastAPI(title="Мой серверный дашборд - ФИНАЛЬНАЯ ВЕРСИЯ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("templates/index.html")

@app.get("/api/system")
def get_system_info():
    return {
        "timestamp": datetime.now().isoformat(),
        "system": f"{platform.system()} {platform.release()}",
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("C:/").percent,
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
    }

@app.get("/api/processes")
def get_top_processes():
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            processes.append({
                "pid": proc.info["pid"],
                "name": proc.info["name"],
                "cpu_percent": proc.info["cpu_percent"]
            })
        except:
            pass
    processes.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
    return {"processes": processes[:5]}

@app.get("/api/wifi")
def get_wifi_info():
    """Возвращает информацию о Wi-Fi соединении"""
    import subprocess
    
    # Базовая структура данных
    wifi_data = {
        "network": "Не подключен",
        "signal": "0", 
        "ip": "Нет подключения",
        "status": "disconnected",  # Добавляем поле статуса
        "channel": "Не определен"
    }
    
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            encoding='cp866'
        )
        
        output = result.stdout
        
        # Проверяем, есть ли вообще Wi-Fi адаптер в состоянии "подключено"
        if "Состояние" in output and "подключено" in output.lower():
            wifi_data["status"] = "connected"
            
            # Парсим SSID (имя сети)
            for line in output.split('\n'):
                if 'SSID' in line and ':' in line and 'BSSID' not in line:
                    network_name = line.split(':')[1].strip()
                    if network_name and network_name != '':
                        wifi_data['network'] = network_name
                        break
            
            # Парсим силу сигнала
            for line in output.split('\n'):
                if 'Сигнал' in line and ':' in line:
                    wifi_data['signal'] = line.split(':')[1].strip().replace('%', '')
                    break

            # Парсим канал
            for line in output.split('\n'):
                if 'Канал' in line and ':' in line:
                    wifi_data['channel'] = line.split(':')[1].strip()
                    break
            
            # Получаем IP только если есть активное соединение
            wifi_data['ip'] = get_real_ip_address() or "Определяется..."
            
        else:
            # Wi-Fi адаптер есть, но нет подключения
            wifi_data["status"] = "no_connection"
            
    except Exception as e:
        print(f"Ошибка получения Wi-Fi данных: {e}")
        wifi_data["status"] = "error"
    
    return wifi_data

def get_real_ip_address():
    """Получает реальный IP адрес Wi-Fi интерфейса"""
    import socket
    import psutil
    
    # Получаем все сетевые интерфейсы
    net_if_addrs = psutil.net_if_addrs()

    for interface_name, addresses in net_if_addrs.items():
        # Ищем Wi-Fi интерфейсы
        if interface_name.startswith(('Wi-Fi', 'wlan', 'WiFi', 'Беспроводная')):
            for addr in addresses:
                # Берем IPv4 адрес (не localhost)
                if addr.family == socket.AF_INET and addr.address != '127.0.0.1':
                    return addr.address
    
    # Если не нашли - пробуем другой способ
    try:
        # Создаем временное соединение, чтобы узнать внешний IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'Не определено'

def format_bytes(bytes_num):
    """
    Преобразует количество байт в удобочитаемую строку
    Например: 1024 → '1.0 KB', 1500000 → '1.43 MB'
    """
    if bytes_num < 1024:
        # Если меньше 1 КБ, возвращаем в байтах
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        # Если меньше 1 МБ, переводим в КБ
        kilobytes = bytes_num / 1024
        return f"{kilobytes:.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        # Если меньше 1 ГБ, переводим в МБ
        megabytes = bytes_num / (1024 * 1024)
        return f"{megabytes:.1f} MB"
    else:
        # Если 1 ГБ или больше
        gigabytes = bytes_num / (1024 * 1024 * 1024)
        return f"{gigabytes:.2f} GB"


@app.get("/api/network-connections")
def get_network_connections():
    """Возвращает информацию о всех сетевых подключениях"""
    connections = []

    net_io = psutil.net_io_counters(pernic=True) 
    # Возвращает статистику сетевого ввода-вывода для каждого интерфейса 
    # {'Wi-Fi': snetio(bytes_sent=12345, bytes_recv=67890, ...)}
    net_if_addrs = psutil.net_if_addrs() 
    # Возвращает адреса сетевых интерфейсов (IP, MAC адреса) 
    # {'Wi-Fi': [snicaddr(family=2, address='192.168.1.100', ...)]}

    net_if_stats = psutil.net_if_stats() 
    # Возвращает статус интерфейсов (включен/выключен, скорость) 
    # {'Wi-Fi': snicstats(isup=True, speed=433, ...)}

    for interface_name in net_if_addrs: # цикл по всем сетевым интерфейсам
        if interface_name.startswith(('vEthernet', 'Loopback', 'isatap', 'teredo')): 
            # vEthernet - виртуальные интерфейсы (например, от Docker, WSL, Hyper-V) 
            # Loopback - loopback интерфейс (localhost, 127.0.0.1) 
            # isatap, teredo - устаревшие туннельные интерфейсы
            continue

        interface_info = { # Ключи словаря соответствуют полям, которые будут в JSON ответе
            "name": interface_name,
            "type": "unknown",
            "status": "down",
            "ip": "Нет IP",
            "mac": "Нет MAC",
            "speed": "Не определено",
            "bytes_sent": 0,
            "bytes_recv": 0,
            "sent_human": "0 B",  # Добавлено
            "recv_human": "0 B"   # Добавлено
        }

        # Определяем тип интерфейса
        if interface_name.startswith(('Wi-Fi', 'wlan', 'WiFi', 'Беспроводная')):
            interface_info["type"] = "wifi"
        elif interface_name.startswith(('Ethernet', 'eth', 'Подключение по локальной сети')):
            interface_info["type"] = "ethernet"

        # Получаем статус
        if interface_name in net_if_stats:
            stats = net_if_stats[interface_name]
            interface_info["status"] = "up" if stats.isup else "down"
            interface_info["speed"] = f"{stats.speed} Мбит/с" if stats.speed > 0 else "Не определено"

        # Получаем IP и MAC адреса
        addresses = net_if_addrs.get(interface_name, [])
        # addresses содержит список всех адресов интерфейса
        # Каждый адрес имеет family (семейство протоколов) и address (значение адреса)
        for addr in addresses:
            # IPv4 адреса
            if addr.family == socket.AF_INET:
                # socket.AF_INET соответствует семейству IPv4 (значение обычно равно 2)
                # Проверяем, не является ли адрес локальным (127.0.0.1)
                if addr.address != '127.0.0.1':
                    interface_info["ip"] = addr.address
                    # Сохраняем IPv4 адрес, например '192.168.1.100'

            # MAC адрес (аппаратный адрес сетевой карты)       
            elif addr.family == AF_LINK:
                # psutil.AF_LINK соответствует канальному уровню (MAC адреса)
                # addr.address содержит MAC адрес в формате 'A4-4B-D5-12-34-56'
                interface_info["mac"] = addr.address.upper()
                # Приводим к верхнему регистру для единообразия

        # Получаем статистику трафика
        if interface_name in net_io:
            io_stats = net_io[interface_name]
            # io_stats содержит объект snetio со статистикой трафика
            interface_info["bytes_sent"] = io_stats.bytes_sent
            interface_info["bytes_recv"] = io_stats.bytes_recv
            # Общее количество принятых байт через этот интерфейс
            # Эти значения накапливаются с момента запуска системы

            # Добавляем человекочитаемые форматы
            interface_info["sent_human"] = format_bytes(io_stats.bytes_sent)
            # Функция format_bytes преобразует байты в КБ, МБ, ГБ и т.д.
            interface_info["recv_human"] = format_bytes(io_stats.bytes_recv)
            # Например: '1.24 MB', '45.6 GB'
        
        # Добавляем интерфейс в список
        connections.append(interface_info)
        # Добавляем словарь с информацией об интерфейсе в общий список

        # Сортируем интерфейсы: сначала активные, потом по типу
    connections.sort(key=lambda x: (
        0 if x["status"] == "up" else 1, # Активные сверху (0 < 1)
        x["type"] # Затем сортируем по типу (wifi, ethernet, unknown)
    ))
        # lambda создает ключ сортировки: сначала статус, потом тип
        # Это обеспечивает логическое отображение интерфейсов
    
    return connections
    # Возвращаем список словарей в формате JSON


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("✨ ФИНАЛЬНАЯ ВЕРСИЯ С ЛОКАЛЬНЫМИ ИКОНКАМИ")
    print("=" * 50)
    print("🌐 Откройте: http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
