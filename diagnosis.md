# diagnosis.md

Сначала я должен был разобраться с покером, понять что я хочу сделать. 
В каждой раздаче есть последовательность решений:
preflop → flop → turn → river

Я работаю только с flop

Игрок всегда сталкивается с ситуацией 
- никто не поставил → можно поставить (bet)
- оппонент поставил → нужно реагировать (call / fold / raise)

stat = numerator / denominator - ключевая формула статистики. 

где:
denominator (opportunity) - когда игрок МОГ сделать действие
numerator (success) - когда он реально сделал это действие

# Что построил

Decision-based poker stats engine с честной выборкой, корректным denominator и сравнением population vs GTO.
Простой дешбордик который показывает посчитанную статистику

Стек: FastAPI backend + HTML фронтенд + Docker. База данных для данного MVP не нужна.

Пайплайн обработки данных: HH (текст) → Parser → NormalizedHand → StatEngine → API → HTML

Запуск приложения смотри в README.md. Сначала запускается скрипт, затем синхронно после скрипта запускается веб сервер

---

# Как понял данные и stat_catalog.json

`stat_catalog.json` — декларативное описание аналитических запросов. Не данные, а правила подсчёта.

Каждый стат содержит:
- `id`, `label`, `description` — идентификатор и описание для UI
- `state` — считаем или нет: `AVAILABLE` считаем, `NO_DATA` best-effort с честным показом, `NO_STAT` / `INVALID_CONTEXT` пропускаем
- `contextFilters` — фильтр раздач: spot (SRP/3BP), formation (BB_SB/BB_BTN), position (OOP/IP), role (PFR/PFC), street
- `opportunity` — знаменатель: когда игрок имел возможность совершить действие
- `success` — числитель: когда игрок совершил нужное действие
- `bindingMode` — способ фильтрации: `DIRECT_EXACT` — фильтруем напрямую, `CONTEXT_COMPOSED` — требует linePrefix / facingAction (не реализовано)
- `minSample` — порог низкой выборки

---

# Как считаю numerator / denominator

Один пайплайн:

```
ParsedHand → NormalizedHand → StatComputer.compute(stat, hands)
```

**Denominator** — количество NormalizedHand, прошедших все фильтры:
contextFilters (spot, formation, position, role, street) + opportunity (facingAction / canAct / maxActionIndex).

**Numerator** — из тех же рук, которые прошли в denominator, считаем те, где success.action совпал.

Если denominator = 0 → `NO_DATA`, не показываем fake 0%.
Если denominator < minSample → `LOW_SAMPLE`, показываем с предупреждением.

**Важное замечание про sample:**
Один hand_id из HH даёт **2 NormalizedHand** — для BB и для оппонента (BB_BTN или BB_SB). Поэтому sample в UI — это количество decision points, а не уникальных раздач. Это корректно для покерной статистики, но нужно понимать при интерпретации.

---

# Решения по ходу работы и почему

**Только флоп.** Normalizer создаёт NormalizedHand только для флопа. Turn и river статы всегда вернут null (0). Это архитектурное ограничение: расширение на другие улицы потребует отдельного прохода по turn/river actions. В рамках timebox — осознанное решение.

**2 NormalizedHand на раздачу.** Normalizer возвращает пару: BB-perspective и opponent-perspective. Это позволяет считать статистику для обеих сторон из одной раздачи без дублирования парсинга.

**StatComputer возвращает только (numerator, denominator).** Без UI-логики и без статусов. StatAggregator уже оборачивает в SourceResult с нужным статусом. Разделение ответственности.

**bindingMode != DIRECT_EXACT → возвращаем (0, 0).** CONTEXT_COMPOSED не реализован. Статы с этим режимом честно показывают null (0), не выдают broad unfiltered результат за filtered.

---

# Edge cases

- `numerator > denominator` → sanity check в логах с ошибкой, данные всё равно отображаются
- `denominator = 0` → `NO_DATA`, не делим на ноль
- `denominator < minSample` → `LOW_SAMPLE` с предупреждением
- `state IN (NO_STAT, INVALID_CONTEXT)` → сразу (0, 0), не тратим время на фильтрацию
- Форматы HH: GTO (PokerStars Game #), WPN PS (PokerStars Hand #), WPN HIS (Hand # -) — все три парсятся
- Позиции для HIS-формата определяются через offset от button seat, не из summary

---

# Как работает фронтенд и как его открыть

Весь UI — это простой Single Page Application (SPA), написанный на ванильном HTML/JS/CSS, который отдаётся FastAPI напрямую строкой (endpoint `/`). Никаких тяжеловесных фреймворков (React/Vue), чтобы не усложнять MVP.

  👉 **[http://localhost:8000](http://localhost:8000)** (или `http://127.0.0.1:8000`)

**Фикс:** debug должен собирать denom_ids и num_ids в одном цикле, где num_ids ⊆ denom_ids всегда.

---

# Что не успел

- Turn и river статистика (Normalizer только флоп)
- `CONTEXT_COMPOSED` bindingMode (linePrefix фильтрация)
- Amount-фильтр для overbet (сейчас overbet frequency = bet frequency, нет размерного фильтра)
- Фильтр по линии в UI (targetLine из каталога не используется как UI-фильтр)
- Breakdown matched hands в UI с деталями каждой раздачи

---

# Риски

- **CONTEXT_COMPOSED статы возвращают null.** Статы требующие linePrefix не считаются. Это честно, но неполно.
- **Sample = decision points, не уникальные раздачи.** Для интерпретации важно понимать это различие.
- **Population данные малые.** По ряду статов sample < 30 (LOW_SAMPLE). Выводы по population нужно делать осторожно.

---

# Ship decision

**GO with conditions**

✅ Корректный расчёт из реальных данных, не хардкод  
✅ sample / denominator показан явно  
✅ null (0) вместо fake 0%  
✅ LOW_SAMPLE маркируется  
✅ Population vs GTO разделены корректно  
✅ Debug breakdown с hand_id для проверки  

⚠️ Условия:  
- Задокументировать что только флоп работает  
- Пофиксить debug endpoint (num_ids должны быть подмножеством denom_ids)  
- Разобраться с overbet = bet  

---

# Как я использовал AI

Использовал Claude для:
- Составления рабочего роадмапа в html формате на этапе 0
- Проверки корректности чисел и диагностики debug данных
- Написания этого diagnosis.md

Весь расчётный код проверен вручную, написан с помощью клод кода. AI не генерировал готовые значения.
