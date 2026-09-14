# Форк badigit/sauresha — регламент

Этот форк подключён к Home Assistant напрямую через HACS (custom repository).
Апстрим — `volshebniks/sauresha`. HACS предлагает обновление **только** когда
здесь опубликован новый GitHub release, поэтому правки форка не может затереть
ни обновление апстрима, ни случайное нажатие «Обновить» в HA.

## Ветки

- `dee` — рабочая и default. Содержит апстрим целиком плюс тонкий слой своих
  коммитов. Именно она ставится в Home Assistant.
- `upstream-master` — чистое зеркало апстрима, без своих коммитов. Из неё
  отпочковываются ветки под PR в апстрим.
- Теги `archive/*` — прежние линии разработки (`master-dee`, `ref-1`), на
  актуальную работу не влияют.

## Свои отличия от апстрима

- Поддержка ревизии контроллера R2 4.5 в `CONTROLLER_NAMES` (`api.py`).
- Версия сборки в `manifest.json` — своя, четвёртым сегментом: `2.1.6.1`.
  Четвёртый сегмент, а не суффикс `-dee`: суффикс HACS считает пре-релизом и
  прячет за флагом beta.

## Подтянуть апстрим

```powershell
git fetch upstream
git rebase upstream/master dee
```

Конфликт почти всегда один и тот же — `manifest.json`, строка `version`:
взять номер апстрима и дописать свой четвёртый сегмент заново (`2.2.0` → `2.2.0.1`).

Дальше — новый релиз, иначе HA ничего не увидит:

```powershell
git push --force-with-lease origin dee
gh release create <версия> --target dee --title <версия> --notes "…"
```

Форс-пуш здесь безопасен: HACS качает архив, история ему безразлична.

В Home Assistant после этого: HACS → SauresHA → Update.

## Отдать правку в апстрим

PR веди **не из `dee`** — уедет весь слой. Отдельной веткой от апстрима:

```powershell
git checkout -b feat/<название> upstream/master
git cherry-pick <коммит из dee>
git push -u origin feat/<название>
gh pr create --repo volshebniks/sauresha --base master
```

Приняли правку — при следующем `rebase` свой коммит отвалится сам как дубликат.
