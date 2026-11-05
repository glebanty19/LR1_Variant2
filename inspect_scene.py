#!/usr/bin/env python3
"""Первинний огляд геоприв'язаного знімка для ЛР1."""

import argparse
import math
from pathlib import Path
import sys


def parse_object(value):
    try:
        name, size_text = value.rsplit("=", 1)
        size = float(size_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"очікується формат «назва=розмір_м», отримано {value!r}"
        ) from exc
    if not name.strip() or not math.isfinite(size) or size <= 0:
        raise argparse.ArgumentTypeError(
            f"назва має бути непорожньою, а розмір — додатним числом: {value!r}"
        )
    return name.strip(), size


def get_pixel_size_m(src, override):
    if override is not None:
        if len(override) not in (1, 2):
            raise ValueError("--gsd приймає одне число або пару GSD_X GSD_Y")
        if any(not math.isfinite(value) or value <= 0 for value in override):
            raise ValueError("--gsd має містити додатні числа")
        gsd_x = override[0]
        gsd_y = override[-1]
        return gsd_x, gsd_y, "задано вручну"

    if src.crs is None:
        raise ValueError("у файлі немає CRS; задайте GSD параметром --gsd")

    res_x, res_y = src.res
    if src.crs.is_geographic:
        _, latitude = src.xy(src.height / 2, src.width / 2)
        gsd_x = abs(res_x) * 111320 * math.cos(math.radians(latitude))
        gsd_y = abs(res_y) * 110574
        return gsd_x, gsd_y, "приблизно (CRS географічна)"

    unit_name, unit_to_m = src.crs.linear_units_factor
    return abs(res_x) * unit_to_m, abs(res_y) * unit_to_m, unit_name


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Первинний огляд сцени для ЛР1")
    parser.add_argument("path", help="шлях до GeoTIFF або PNG")
    parser.add_argument(
        "--rgb",
        nargs=3,
        type=int,
        metavar=("R", "G", "B"),
        help="номери каналів R G B (1-based), наприклад 4 3 2 для Sentinel-2",
    )
    parser.add_argument(
        "--gsd",
        type=float,
        nargs="+",
        help="розмір пікселя у метрах: одне число або пара GSD_X GSD_Y",
    )
    parser.add_argument(
        "--objects",
        nargs="+",
        type=parse_object,
        default=[("малий будинок", 6.0), ("купа завалу", 3.0)],
        metavar="НАЗВА=РОЗМІР_М",
        help="об'єкти та їхні розміри у метрах",
    )
    args = parser.parse_args()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import rasterio
    except ImportError as exc:
        parser.error(
            "не встановлено залежності; виконайте "
            "`python -m pip install -r requirements.txt` "
            f"(деталі: {exc})"
        )

    try:
        with rasterio.open(args.path) as src:
            print("=" * 60)
            print("ПЕРВИННИЙ ОГЛЯД СЦЕНИ")
            print("=" * 60)
            print(f"Файл:              {args.path}")
            print(f"CRS:               {src.crs}")
            print(f"Розмір (пкс):      {src.width} x {src.height}")
            print(f"Кількість каналів: {src.count}")
            print(f"Тип даних:         {', '.join(src.dtypes)}")
            tags = src.tags()
            acquisition_date = tags.get("ACQUISITION_DATE") or tags.get("DATETIME")
            if acquisition_date:
                print(f"Дата знімання:     {acquisition_date}")
            elif tags.get("CAPTURE_DATE_AVAILABLE", "").lower().startswith("no"):
                print("Дата знімання:     не зазначена в метаданих джерела")

            gsd_x, gsd_y, gsd_source = get_pixel_size_m(src, args.gsd)
            gsd = math.sqrt(gsd_x * gsd_y)
            width_m = src.width * gsd_x
            height_m = src.height * gsd_y
            print(f"GSD X/Y:           {gsd_x:.3f} / {gsd_y:.3f} м ({gsd_source})")
            print(
                f"Розмір сцени:      {width_m / 1000:.2f} x "
                f"{height_m / 1000:.2f} км"
            )

            bands = args.rgb if args.rgb else (
                [1, 2, 3] if src.count >= 3 else [1]
            )
            invalid_bands = [band for band in bands if band < 1 or band > src.count]
            if invalid_bands:
                parser.error(
                    f"номери каналів мають бути в межах 1–{src.count}; "
                    f"некоректні: {invalid_bands}"
                )

            arrays = []
            for band in bands:
                masked = src.read(band, masked=True).astype(float)
                arrays.append(masked.filled(np.nan))

            with Path("scene_report.txt").open("w", encoding="utf-8") as report:
                report.write(f"Файл: {args.path}\n")
                report.write(f"CRS: {src.crs}\n")
                report.write(
                    f"GSD X/Y: {gsd_x:.3f} / {gsd_y:.3f} м ({gsd_source})\n"
                )
                report.write(
                    f"Розмір: {src.width}×{src.height} пкс / "
                    f"{width_m / 1000:.2f}×{height_m / 1000:.2f} км\n"
                )
                report.write(
                    f"Канали: {src.count}, тип: {', '.join(src.dtypes)}\n\n"
                )
                if acquisition_date:
                    report.write(f"Дата знімання: {acquisition_date}\n")
                elif tags.get("CAPTURE_DATE_AVAILABLE", "").lower().startswith("no"):
                    report.write(
                        "Дата знімання: не зазначена в метаданих джерела\n"
                    )
                if tags.get("SOURCE_IMAGE"):
                    report.write(f"Вихідне зображення: {tags['SOURCE_IMAGE']}\n")
                if tags.get("GEOREFERENCE_METHOD"):
                    report.write(
                        "Метод геоприв'язки: "
                        f"{tags['GEOREFERENCE_METHOD']}\n"
                    )
                report.write("\n")
                report.write("Об'єкти:\n")
                for name, size in args.objects:
                    pixel_size = size / gsd
                    report.write(
                        f"  {name}: {size:g} м -> {pixel_size:.1f} пкс\n"
                    )
                    print(f"  {name}: {size:g} м -> {pixel_size:.1f} пікселів")

            print("\nЗвіт збережено у scene_report.txt")

            if arrays:
                colors = ["red", "green", "blue"]
                plt.figure(figsize=(10, 4))
                for index, (band, array) in enumerate(zip(bands, arrays)):
                    values = array[np.isfinite(array)]
                    if values.size:
                        color = colors[index] if len(arrays) > 1 else "gray"
                        plt.hist(
                            values,
                            bins=100,
                            histtype="step",
                            color=color,
                            label=f"канал {band}",
                        )
                plt.xlabel("Значення каналу")
                plt.ylabel("Кількість пікселів")
                plt.legend()
                plt.title("Гістограми каналів")
                plt.tight_layout()
                plt.savefig("histograms.png", dpi=150)
                plt.close()
                print("Гістограму збережено у histograms.png")

    except (OSError, rasterio.errors.RasterioError, ValueError) as exc:
        parser.error(str(exc))

    print("=" * 60)
    print("Готово. Перенесіть отримані значення до таблиць 5.1–5.2 звіту.")


if __name__ == "__main__":
    main()
