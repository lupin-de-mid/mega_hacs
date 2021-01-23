import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import aiohttp
import typing
import re
import json

from bs4 import BeautifulSoup
from homeassistant.components import mqtt
from homeassistant.const import DEVICE_CLASS_TEMPERATURE, DEVICE_CLASS_HUMIDITY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import TEMP, HUM
from .exceptions import CannotConnect

TEMP_PATT = re.compile(r'temp:([01234567890\.]+)')
HUM_PATT = re.compile(r'hum:([01234567890\.]+)')
PATTERNS = {
    TEMP: TEMP_PATT,
    HUM: HUM_PATT,
}
UNITS = {
    TEMP: '°C',
    HUM: '%'
}
CLASSES = {
    TEMP: DEVICE_CLASS_TEMPERATURE,
    HUM: DEVICE_CLASS_HUMIDITY
}

class MegaD:
    """MegaD Hub"""

    def __init__(
            self,
            hass: HomeAssistant,
            loop: asyncio.AbstractEventLoop,
            host: str,
            password: str,
            mqtt: mqtt.MQTT,
            lg: logging.Logger,
            id: str,
            mqtt_id: str = None,
            scan_interval=60,
            port_to_scan=0,
            inverted: typing.List[int] = None,
            **kwargs,
    ):
        """Initialize."""
        self.loop: asyncio.AbstractEventLoop = None
        self.hass = hass
        self.host = host
        self.sec = password
        self.mqtt = mqtt
        self.id = id
        self.lck = asyncio.Lock()
        self.cnd = asyncio.Condition()
        self.online = True
        self.entities: typing.List[Entity] = []
        self.poll_interval = scan_interval
        self.subs = None
        self.lg: logging.Logger = lg.getChild(self.id)
        self._scanned = {}
        self.sensors = []
        self.port_to_scan = port_to_scan
        self.last_update = datetime.now()
        self._callbacks: typing.DefaultDict[int, typing.List[typing.Callable[[dict], typing.Coroutine]]] = defaultdict(list)
        self._loop = loop
        self.values = {}
        self.last_port = None
        self.updater = DataUpdateCoordinator(
            hass,
            self.lg,
            name="sensors",
            update_method=self.poll,
            update_interval=timedelta(seconds=self.poll_interval) if self.poll_interval else None,
        )
        if not mqtt_id:
            _id = host.split(".")[-1]
            self.mqtt_id = f"megad/{_id}"
        else:
            self.mqtt_id = mqtt_id

    async def start(self):
        self.loop = asyncio.get_event_loop()
        self.subs = await self.mqtt.async_subscribe(
            topic=f"{self.mqtt_id}/+",
            msg_callback=self._process_msg,
            qos=0,
        )

    async def stop(self):
        self.subs()
        for x in self._callbacks.values():
            x.clear()

    async def add_entity(self, ent):
        async with self.lck:
            self.entities.append(ent)

    async def get_sensors(self):
        self.lg.debug(self.sensors)
        for x in self.sensors:
            await self.get_port(x)

    @property
    def is_online(self):
        return (datetime.now() - self.last_update).total_seconds() < (self.poll_interval + 10)

    def _warn_offline(self):
        if self.online:
            self.lg.warning('mega is offline')
            self.hass.states.async_set(
                f'mega.{self.id}',
                'offline',
            )
            self.online = False

    def _notify_online(self):
        if not self.online:
            self.hass.states.async_set(
                f'mega.{self.id}',
                'online',
            )
            self.online = True

    async def poll(self):
        """
        Send get port 0 every poll_interval. When answer is received, mega.<id> becomes online else mega.<id> becomes
        offline
        """
        self.lg.debug('poll')
        if len(self.sensors) > 0:
            await self.get_sensors()
        else:
            await self.get_port(self.port_to_scan)
        return self.values

    async def get_mqtt_id(self):
        async with aiohttp.request(
            'get', f'http://{self.host}/{self.sec}/?cf=2'
        ) as req:
            data = await req.text()
            data = BeautifulSoup(data, features="lxml")
            _id = data.find(attrs={'name': 'mdid'})
            if _id:
                _id = _id['value']
            return _id or 'megad/' + self.host.split('.')[-1]

    async def send_command(self, port=None, cmd=None):
        if port:
            url = f"http://{self.host}/{self.sec}/?pt={port}&cmd={cmd}"
        else:
            url = f"http://{self.host}/{self.sec}/?cmd={cmd}"
        self.lg.debug('run command: %s', url)
        async with self.lck:
            async with aiohttp.request("get", url=url) as req:
                if req.status != 200:
                    self.lg.warning('%s returned %s (%s)', url, req.status, await req.text())
                    return False
                else:
                    return True

    async def save(self):
        await self.send_command(cmd='s')

    async def get_port(self, port):
        """Запрос состояния порта. Блокируется пока не придет какое-нибудь сообщение от меги или таймаут"""
        async with self.cnd:
            await self.mqtt.async_publish(
                topic=f'{self.mqtt_id}/cmd',
                payload=f'get:{port}',
                qos=2,
                retain=False,
            )
            await asyncio.wait_for(self.cnd.wait(), timeout=15)
            await asyncio.sleep(0.05)

    async def get_all_ports(self):
        for x in range(37):
            await self.get_port(x)

    async def reboot(self, save=True):
        await self.save()

    async def _notify(self, port, value):
        async with self.cnd:
            self.last_update = datetime.now()
            self.values[port] = value
            self.last_port = port
            self.cnd.notify_all()

    def _process_msg(self, msg):
        try:
            d = msg.topic.split('/')
            port = d[-1]
        except ValueError:
            self.lg.warning('can not process %s', msg)
            return

        if port == 'cmd':
            return
        try:
            port = int(port)
        except:
            self.lg.warning('can not process %s', msg)
            return
        self.lg.debug(
            'process incomming message: %s', msg
        )
        value = None
        try:
            value = json.loads(msg.payload)
            for cb in self._callbacks[port]:
                cb(value)
        except Exception as exc:
            self.lg.warning(f'could not parse json ({msg.payload}): {exc}')
            return
        finally:
            asyncio.run_coroutine_threadsafe(self._notify(port, value), self.loop)

    def subscribe(self, port, callback):
        port = int(port)
        self.lg.debug(
            f'subscribe %s %s', port, callback
        )
        self._callbacks[port].append(callback)

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        async with aiohttp.request("get", url=f"http://{self.host}/{self.sec}") as req:
            if "Unauthorized" in await req.text():
                return False
            else:
                if req.status != 200:
                    raise CannotConnect
                return True

    async def get_port_page(self, port):
        url = f'http://{self.host}/{self.sec}/?pt={port}'
        self.lg.debug(f'get page for port {port} {url}')
        async with aiohttp.request('get', url) as req:
            return await req.text()

    async def scan_port(self, port):
        async with self.lck:
            if port in self._scanned:
                return self._scanned[port]
            url = f'http://{self.host}/{self.sec}/?pt={port}'
            self.lg.debug(
                f'scan port %s: %s', port, url
            )
            async with aiohttp.request('get', url) as req:
                html = await req.text()
            tree = BeautifulSoup(html, features="lxml")
            pty = tree.find('select', attrs={'name': 'pty'})
            if pty is None:
                return
            else:
                pty = pty.find(selected=True)
                if pty:
                    pty = pty['value']
                else:
                    return
            if pty in ['0', '1']:
                m = tree.find('select', attrs={'name': 'm'})
                if m:
                    m = m.find(selected=True)['value']
                self._scanned[port] = (pty, m)
                return pty, m
            elif pty == '3':
                m = tree.find('select', attrs={'name': 'd'})
                if m:
                    m = m.find(selected=True)['value']
                self._scanned[port] = (pty, m)
                return pty, m

    async def scan_ports(self,):
        for x in range(38):
            ret = await self.scan_port(x)
            if ret:
                yield [x, *ret]

    async def get_config(self):
        ret = defaultdict(lambda: defaultdict(list))
        async for port, pty, m in self.scan_ports():
            if pty == "0":
                ret['binary_sensor'][port].append({})
            elif pty == "1" and m in ['0', '1']:
                ret['light'][port].append({'dimmer': m == '1'})
            elif pty == '3':
                try:
                    await self.get_port(port)
                    values = self.values.get(port)
                except asyncio.TimeoutError:
                    self.lg.warning(f'timout on port {port}')
                    continue
                self.lg.debug(f'values: %s', values)
                if values is None:
                    self.lg.warning(f'port {port} is of type sensor but response is None, skipping it')
                    continue
                if isinstance(values, dict) and 'value' in values:
                    values = values['value']
                if isinstance(values, str) and TEMP_PATT.search(values):
                    values = {TEMP: values}
                elif not isinstance(values, dict):
                    values = {None: values}
                for key in values:
                    self.lg.debug(f'add sensor {key}')
                    ret['sensor'][port].append(dict(
                        key=key,
                        unit_of_measurement=UNITS.get(key, UNITS[TEMP]),
                        device_class=CLASSES.get(key, CLASSES[TEMP]),
                        id_suffix=key,
                    ))
        return ret


