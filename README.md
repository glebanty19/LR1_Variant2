# ЛР1 — Варіант 2: оцінювання пошкоджень будівель у Рубіжному

Навчальний проєкт для формалізації оцінювання пошкоджень будівель кварталу
після обстрілів і первинного огляду українського супутникового фрагмента.

## Структура

```text
lab1/
├── .gitignore
├── README.md
├── requirements.txt
├── passport.yaml
├── inspect_scene.py
├── analyze_damage_sample.py
├── aoi.geojson
├── ukraine_sample/         # знімки Rubizhne та JSON-анотації
├── rubizhne_post_0003_georef.tif
├── damage_measurements.csv
├── damage_annotations.png
├── pre_post_comparison.png
├── scene_report.txt
├── histograms.png
└── LR1_Variant2_Final.docx
```

`LR1_Variant2_Final.docx` — виправлена копія звіту; початковий DOCX залишився
локально без змін і до репозиторію не додається.

## Приклад знімка

Основний фрагмент — `ukraine_sample/images/rubizhne_post_0003.png` з парою
pre/post та полігональними мітками у `ukraine_sample/labels/`. Джерело:
[xBD Ukraine Destruction Analysis](https://huggingface.co/datasets/sda-kr/xbd-ukraine).
Картка набору декларує ліцензію MIT. У PNG/JSON є координати вершин і класи
пошкоджень, але немає точної дати знімання; у звіті це обмеження зазначено,
дату не домислено.

Файл `rubizhne_post_0003_georef.tif` — похідний GeoTIFF, геоприв'язку якого
відновлено афінним перетворенням за парами вершин піксельних і lon/lat-анотацій.
Отримано EPSG:32637, GSD X/Y ≈ 0,575/0,874 м/піксель; RMS залишок апроксимації
0,0048 м. Це відновлення для навчального огляду, а не оригінальний GeoTIFF.
У фрагменті 85 анотацій будівель після події: 75 без пошкоджень, 3 minor,
4 major, 3 destroyed; окремих міток куп завалу немає. CSV містить виміри
п'яти анотованих будівель, а `damage_annotations.png` показує межі цих полігонів.

## Встановлення та запуск

```bash
python -m pip install -r requirements.txt
python analyze_damage_sample.py
python inspect_scene.py rubizhne_post_0003_georef.tif --rgb 1 2 3
```

The first command recreates the derived GeoTIFF and measurement/figure files;
the second creates `scene_report.txt` and `histograms.png`. Per-building
measurements are in `damage_measurements.csv`, and class counts are printed by
the analysis script.

Для іншого Sentinel-2 GeoTIFF із каналами 4, 3 і 2:

```bash
python inspect_scene.py scene.tif --rgb 4 3 2 --objects "малий будинок=6" "купа завалу=3" "будівля 15м=15"
```

Для PNG-чіпа без геоприв'язки вкажіть розмір пікселя:

```bash
python inspect_scene.py chip.png --gsd 0.5 --objects "будинок=12" "завал=6"
```

`--gsd` приймає одне значення або окремі розміри пікселя по X і Y.
`analyze_damage_sample.py` відновлює геоприв'язку з міток, рахує виміри,
створює GeoTIFF для QGIS та ілюстрації. Точна дата знімання у джерелі відсутня.

Скрипт створює в поточній директорії `scene_report.txt` і `histograms.png`.
Для GeoTIFF із проєктованою CRS GSD береться з розміру пікселя та одиниць CRS;
для географічної CRS розрахунок приблизний. Параметр `--gsd` задає однаковий
розмір пікселя по обох осях і має використовуватися для незареєстрованих зображень.

## Дані й обмеження

Картка xBD Ukraine декларує MIT; перевірте умови й атрибуцію оригінальних
зображень перед повторним використанням поза навчальною роботою. Геоприв'язка
основного PNG відновлена з анотацій, а не прочитана з оригінального растра;
точна дата знімання не вказана. `aoi.geojson` окреслює прямокутне покриття
навчального фрагмента, а не адміністративну межу кварталу. Мітки набору не є
незалежною наземною валідацією. Sentinel-2 із роздільністю 10 м зберігається
лише як приклад скринінгу, непридатний для вимірювання окремих будівель.

Репозиторій проєкту: https://github.com/glebanty19/LR1_Variant2. Перед здачею
заповніть кафедру й викладача на титульній сторінці. Для повної відповідності
вимозі про дату потрібне джерело з повними метаданими знімання; у цьому
навчальному фрагменті точну дату встановити не вдалося.
