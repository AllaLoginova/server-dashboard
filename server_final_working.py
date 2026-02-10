from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import psutil
from psutil import AF_LINK
import platform
import socket
from datetime import datetime
from fastapi.staticfiles import StaticFiles
import subprocess
import re
import ctypes
from ctypes import wintypes
import struct

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


# ==================== НОВЫЙ КОД ДЛЯ ПОЛУЧЕНИЯ СИГНАЛА WI-FI ====================

def get_wifi_signal_quality():
    """Получает качество сигнала Wi-Fi через Windows Native WiFi API"""
    try:
        # Загружаем библиотеки
        wlanapi = ctypes.windll.wlanapi
        ole32 = ctypes.windll.ole32

        # Определяем структуры
        class GUID(ctypes.Structure):
            _fields_ = [
                ('Data1', wintypes.DWORD),
                ('Data2', wintypes.WORD),
                ('Data3', wintypes.WORD),
                ('Data4', wintypes.BYTE * 8)
            ]

        class WLAN_INTERFACE_INFO(ctypes.Structure):
            _fields_ = [
                ('InterfaceGuid', GUID),
                ('strInterfaceDescription', wintypes.WCHAR * 256),
                ('isState', wintypes.DWORD)
            ]

        class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
            _fields_ = [
                ('dwNumberOfItems', wintypes.DWORD),
                ('dwIndex', wintypes.DWORD),
                ('InterfaceInfo', WLAN_INTERFACE_INFO * 1)
            ]

        # Инициализация
        handle = wintypes.HANDLE()
        negotiated_version = wintypes.DWORD()

        # Открываем хендл WLAN
        result = wlanapi.WlanOpenHandle(
            wintypes.DWORD(2),  # Client version 2.0
            None,
            ctypes.byref(negotiated_version),
            ctypes.byref(handle)
        )

        if result != 0:
            return None

        try:
            # Получаем список интерфейсов
            interface_list = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
            result = wlanapi.WlanEnumInterfaces(
                handle,
                None,
                ctypes.byref(interface_list)
            )

            if result != 0 or not interface_list:
                return None

            # Проходим по всем интерфейсам
            for i in range(interface_list.contents.dwNumberOfItems):
                interface_info = interface_list.contents.InterfaceInfo[i]

                # Получаем информацию о подключении
                connection_info = ctypes.c_void_p()
                result = wlanapi.WlanQueryInterface(
                    handle,
                    ctypes.byref(interface_info.InterfaceGuid),
                    wintypes.DWORD(7),  # wlan_intf_opcode_current_connection
                    None,
                    ctypes.byref(wintypes.DWORD()),
                    ctypes.byref(connection_info),
                    ctypes.c_void_p()
                )

                if result == 0 and connection_info:
                    # Парсим структуру WLAN_CONNECTION_ATTRIBUTES
                    # Смещение для wlanAssociationAttributes
                    ptr = ctypes.cast(connection_info, ctypes.c_void_p)

                    # Пробуем получить RSSI (сила сигнала)
                    try:
                        # Читаем сырые данные
                        data = (ctypes.c_byte * 1024)()
                        ctypes.memmove(data, ptr, 1024)

                        # RSSI обычно находится по смещению
                        # Это хак, так как структура сложная
                        for offset in range(100, 200, 4):
                            try:
                                value = struct.unpack('i', bytes(data[offset:offset + 4]))[0]
                                if -100 <= value <= 0:  # RSSI в диапазоне -100..0 dBm
                                    # Конвертируем в проценты (примерно)
                                    # -50 dBm = 100%, -100 dBm = 0%
                                    percentage = max(0, min(100, int((value + 100) * 2)))
                                    return str(percentage)
                            except:
                                continue
                    except:
                        pass

                    # Освобождаем память
                    wlanapi.WlanFreeMemory(connection_info)

        finally:
            # Закрываем хендл
            wlanapi.WlanCloseHandle(handle, None)

    except Exception as e:
        print(f"Ошибка получения сигнала через WLAN API: {e}")

    return None


def get_wifi_info_netsh():
    """Пытаемся получить данные Wi-Fi через netsh"""
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            encoding='cp866',
            timeout=2
        )

        if result.returncode != 0:
            return None

        output = result.stdout

        data = {
            "network": "Неизвестно",
            "signal": "0",
            "channel": "Не определен",
            "success": False
        }

        # Парсим SSID
        for line in output.split('\n'):
            if 'SSID' in line and ':' in line and 'BSSID' not in line:
                network_name = line.split(':')[1].strip()
                if network_name and network_name != '':
                    data['network'] = network_name
                    break

        # Парсим сигнал
        signal_found = False
        for line in output.split('\n'):
            if 'Сигнал' in line and ':' in line:
                signal_str = line.split(':')[1].strip()
                numbers = re.findall(r'\d+', signal_str)
                if numbers:
                    data['signal'] = numbers[0]
                    signal_found = True
                    break

        if not signal_found:
            for line in output.split('\n'):
                if 'Signal' in line and ':' in line:
                    signal_str = line.split(':')[1].strip()
                    numbers = re.findall(r'\d+', signal_str)
                    if numbers:
                        data['signal'] = numbers[0]
                        break

        # Парсим канал
        channel_found = False
        for line in output.split('\n'):
            if 'Канал' in line and ':' in line:
                data['channel'] = line.split(':')[1].strip()
                channel_found = True
                break

        if not channel_found:
            for line in output.split('\n'):
                if 'Channel' in line and ':' in line:
                    data['channel'] = line.split(':')[1].strip()
                    break

        data['success'] = True
        return data

    except Exception as e:
        print(f"Ошибка netsh: {e}")
        return None


@app.get("/api/wifi")
def get_wifi_info():
    """Основная функция получения информации о Wi-Fi"""

    wifi_data = {
        "network": "Не подключен",
        "signal": "0",
        "ip": "Нет подключения",
        "status": "disconnected",
        "status_text": "Не активно",
        "channel": "Не определен",
        "interface_name": "Не определено",
        "mac_address": "Не определено",
        "speed": "Не определено"
    }

    try:
        # Получаем базовую информацию через psutil
        net_if_stats = psutil.net_if_stats()
        net_if_addrs = psutil.net_if_addrs()

        wifi_keywords = ['беспроводн', 'wireless', 'wi-fi', 'wlan', 'wi fi']
        active_wifi_found = False

        for interface_name, stats in net_if_stats.items():
            ifname_lower = interface_name.lower()
            is_wifi_interface = any(keyword in ifname_lower for keyword in wifi_keywords)

            if is_wifi_interface and stats.isup:
                active_wifi_found = True

                # Основные данные
                wifi_data.update({
                    "status": "connected",
                    "status_text": "Активно",
                    "interface_name": interface_name,
                    "speed": f"{stats.speed} Мбит/с" if stats.speed > 0 else "Не определено"
                })

                # IP адрес
                if interface_name in net_if_addrs:
                    for addr in net_if_addrs[interface_name]:
                        if addr.family == socket.AF_INET and addr.address != '127.0.0.1':
                            wifi_data['ip'] = addr.address
                            break

                # MAC адрес
                if interface_name in net_if_addrs:
                    for addr in net_if_addrs[interface_name]:
                        if addr.family == psutil.AF_LINK:
                            wifi_data['mac_address'] = addr.address.upper()
                            break

                # Пробуем получить имя сети и детали
                netsh_data = get_wifi_info_netsh()

                if netsh_data and netsh_data['success']:
                    wifi_data['network'] = netsh_data.get('network', 'Неизвестно')
                    wifi_data['channel'] = netsh_data.get('channel', 'Не определен')

                    # Сигнал из netsh
                    signal_from_netsh = netsh_data.get('signal', '0')
                    if signal_from_netsh != '0':
                        wifi_data['signal'] = signal_from_netsh
                    else:
                        # Пробуем получить сигнал через Windows API
                        wifi_signal = get_wifi_signal_quality()
                        if wifi_signal:
                            wifi_data['signal'] = wifi_signal
                else:
                    # Если netsh не сработал, пробуем Windows API для сигнала
                    wifi_signal = get_wifi_signal_quality()
                    if wifi_signal:
                        wifi_data['signal'] = wifi_signal

                    # Имя сети по умолчанию
                    wifi_data['network'] = "Беспроводная сеть"

                break

        if not active_wifi_found:
            # Wi-Fi не активен
            wifi_adapters = []
            for interface_name in net_if_stats.keys():
                if any(keyword in interface_name.lower() for keyword in wifi_keywords):
                    wifi_adapters.append(interface_name)

            if wifi_adapters:
                wifi_data.update({
                    "status": "disabled",
                    "status_text": "Wi-Fi выключен",
                    "interface_name": wifi_adapters[0]
                })
            else:
                wifi_data.update({
                    "status": "no_adapter",
                    "status_text": "Нет Wi-Fi адаптера"
                })

    except Exception as e:
        print(f"Ошибка получения Wi-Fi данных: {e}")
        wifi_data.update({
            "status": "error",
            "status_text": f"Ошибка: {str(e)[:30]}..."
        })

    return wifi_data


def format_bytes(bytes_num):
    """Преобразует количество байт в удобочитаемую строку"""
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        kilobytes = bytes_num / 1024
        return f"{kilobytes:.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        megabytes = bytes_num / (1024 * 1024)
        return f"{megabytes:.1f} MB"
    else:
        gigabytes = bytes_num / (1024 * 1024 * 1024)
        return f"{gigabytes:.2f} GB"


@app.get("/api/network-connections")
def get_network_connections():
    """Возвращает информацию о всех сетевых подключениях"""
    connections = []

    net_io = psutil.net_io_counters(pernic=True)
    net_if_addrs = psutil.net_if_addrs()
    net_if_stats = psutil.net_if_stats()

    for interface_name in net_if_addrs:
        if interface_name.startswith(('vEthernet', 'Loopback', 'isatap', 'teredo')):
            continue

        interface_info = {
            "name": interface_name,
            "type": "unknown",
            "status": "down",
            "ip": "Нет IP",
            "mac": "Нет MAC",
            "speed": "Не определено",
            "bytes_sent": 0,
            "bytes_recv": 0,
            "sent_human": "0 B",
            "recv_human": "0 B"
        }

        # Определяем тип интерфейса
        ifname_lower = interface_name.lower()
        if any(keyword in ifname_lower for keyword in
               ['wi-fi', 'wlan', 'wi fi', 'беспроводн', 'wireless']):
            interface_info["type"] = "wifi"
        elif interface_name.startswith(('Ethernet', 'eth', 'Подключение по локальной сети')):
            interface_info["type"] = "ethernet"

        # Получаем статус
        if interface_name in net_if_stats:
            stats = net_if_stats[interface_name]
            interface_info["status"] = "up" if stats.isup else "down"
            if stats.speed > 0:
                interface_info["speed"] = f"{stats.speed} Мбит/с"

        # Получаем IP и MAC адреса
        addresses = net_if_addrs.get(interface_name, [])
        for addr in addresses:
            # IPv4 адреса
            if addr.family == socket.AF_INET:
                if addr.address != '127.0.0.1':
                    interface_info["ip"] = addr.address
            # MAC адрес
            elif addr.family == AF_LINK:
                interface_info["mac"] = addr.address.upper()

        # Получаем статистику трафика
        if interface_name in net_io:
            io_stats = net_io[interface_name]
            interface_info["bytes_sent"] = io_stats.bytes_sent
            interface_info["bytes_recv"] = io_stats.bytes_recv
            interface_info["sent_human"] = format_bytes(io_stats.bytes_sent)
            interface_info["recv_human"] = format_bytes(io_stats.bytes_recv)

        connections.append(interface_info)

    # Сортируем интерфейсы
    connections.sort(key=lambda x: (
        0 if x["status"] == "up" else 1,
        x["type"]
    ))

    return connections


if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("✨ ВЕРСИЯ С WINDOWS WIFI API")
    print("=" * 50)
    print("🌐 Откройте: http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)