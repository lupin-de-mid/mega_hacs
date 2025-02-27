# MegaD HomeAssistant integration
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://yoomoney.ru/to/410013955329136)
<a class="github-button" href="https://github.com/andvikt/mega_hacs" data-icon="octicon-star" data-show-count="true" aria-label="Star andvikt/mega_hacs on GitHub">Star</a>

[Сообщить о проблеме](https://github.com/andvikt/mega_hacs/issues/new?assignees=&labels=&template=bug-report.md&title=){ .md-button .md-button--primary }
[Предложение об улучшении](https://github.com/andvikt/mega_hacs/issues/new?assignees=&labels=enhancement&template=enhance.md&title=){ .md-button .md-button--primary }

Интеграция с [MegaD-2561, MegaD-328](https://www.ab-log.ru/smart-house/ethernet/megad-2561)


Если вам понравилась интеграция, не забудьте поставить звезду на гитхабе - вам не сложно, а мне приятно ) А если
интеграция очень понравилась - еще приятнее, если вы воспользуетесь кнопкой доната )

Обновление прошивки MegaD можно делать прямо из HA с помощью [аддона](https://github.com/andvikt/mega_addon.git)

## Основные особенности {: #mains }
- Настройка в [веб-интерфейсе](settings.md) + [yaml](yaml.md)
- Все порты автоматически добавляются как устройства (для обычных релейных выходов создается 
  `light`, для шим - `light` с поддержкой яркости, для цифровых входов `binary_sensor`, для датчиков
  `sensor`)
- Поддержка rgb+w лент как с использованием диммеров, так и адресных лент на чипах ws28xx и подобных, 
  [подробнее про rgbw](yaml.md#rgb)
- Плавное диммирование для любых диммируемых объектов (в том числе с аппаратной поддержкой и без),
  [подробнее про smooth](smooth.md)
- Возможность работы с несколькими megad
- Обратная связь по [http](http.md)
- Автоматическое восстановление состояний выходов после перезагрузки контроллера
- Автоматическое добавление/изменение объектов после перезагрузки контроллера
- [События](events.md) на двойные/долгие нажатия
- Команды выполняются друг за другом без конкурентного доступа к ресурсам megad, это дает гарантии надежного исполнения
  большого кол-ва команд (например в сценах). Каждая следующая команда отправляется только после получения ответа о
  выполнении предыдущей.
- поддержка [ds2413](https://www.ab-log.ru/smart-house/ethernet/megad-2w) в том числе несколько шиной (начиная с версии 0.4.1)
- поддержка расширителей MegaD-16I-XT, MegaD-16R-XT, MegaD-16PWM (начиная с версии 0.5.1)
- поддержка всех возможных датчиков в режиме I2C-ANY, полный список поддерживаемых датчиков 
  [по ссылке](i2c.md) (начиная с версии 0.6.1)

## Установка {: #install}
Если вы уже раньше устанавливали HACS, то просто поищите в списке интеграций HACS MegaD, если нет, то сначла необходимо
установить HACS - это витрина сторонних интеграций. [Инструкция по установке](https://hacs.xyz/docs/installation/installation)

Далее внутри интерфейса HACS ищем MegaD: `HACS - Integrations - Explore`, в поиске ищем MegaD. 

На этом установка не закончена, вам потребуется прописать настройки каждого контроллера, [подробнее](settings.md)

!!! note "Альтернативный способ установки"
    Откройте терминал (стандартный аддон Terminal & SSH, если у вас есть supervisor, если нет то терминал вашей системы)
    ```shell
    # из папки с конфигом
    wget -q -O - https://raw.githubusercontent.com/andvikt/mega_hacs/master/install.sh | bash -
    ```
    Не забываем перезагрузить HA

## Обновления
Обновления выполняются так же в меню HACS. 
Информация об обновлениях приходит с некоторым интервалом, чтобы вручную проверить наличие обновлений
нажмите три точки возле интеграции в меню HACS и нажмите `обновить информацию`

Чтобы включить возможность использования бета-версий, зайдите в HACS, найдите интеграцию MegaD, нажмите три точки, 
там кнопка "переустановить" или reinstall, дальше нужно нажать галку "показывать бета-версии"

## Зависимости {: #deps }
Для максимальной скорости реакции на команды сервера, рекомендуется выключить `имитацию http-ответа` в 
настройках интеграции и настроить proxy_pass к HA, самый простой способ сделать это - воспользоваться 
[специальным аддоном](https://github.com/andvikt/mega_addon/tree/master/mega-proxy)

Обновить ваш контроллер до последней версии, обновление прошивки MegaD можно делать 
из HA с помощью [аддона](https://github.com/andvikt/mega_addon.git)
