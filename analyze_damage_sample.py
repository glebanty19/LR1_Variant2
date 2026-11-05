#!/usr/bin/env python3
"""Reproduce the annotated building measurements for the Rubizhne xBD sample."""

import csv
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.transform import Affine
from rasterio.warp import transform


ROOT = Path(__file__).resolve().parent
IMAGE_PATH = ROOT / "ukraine_sample" / "images" / "rubizhne_post_0003.png"
PRE_IMAGE_PATH = ROOT / "ukraine_sample" / "images" / "rubizhne_pre_0003.png"
LABEL_PATH = ROOT / "ukraine_sample" / "labels" / "rubizhne_post_0003.json"
MEASUREMENTS_PATH = ROOT / "damage_measurements.csv"
ANNOTATED_PATH = ROOT / "damage_annotations.png"
PAIR_PREVIEW_PATH = ROOT / "pre_post_comparison.png"
GEOREFERENCED_PATH = ROOT / "rubizhne_post_0003_georef.tif"
CRS = "EPSG:32637"


def parse_wkt_polygon(value):
    pairs = re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", value)
    if len(pairs) < 4:
        raise ValueError(f"Недостатньо координат у полігоні: {value[:80]}")
    return np.asarray([[float(x), float(y)] for x, y in pairs], dtype=float)


def main():
    labels = json.loads(LABEL_PATH.read_text(encoding="utf-8"))
    pixel_points = []
    map_points = []
    annotations = []

    geo_features = labels["features"]["lng_lat"]
    pixel_features = labels["features"]["xy"]
    if len(geo_features) != len(pixel_features):
        raise ValueError("Кількість географічних і піксельних анотацій не збігається")

    class_counts = Counter()
    for geographic, pixel in zip(geo_features, pixel_features):
        geographic_polygon = parse_wkt_polygon(geographic["wkt"])
        pixel_polygon = parse_wkt_polygon(pixel["wkt"])
        if len(geographic_polygon) != len(pixel_polygon):
            raise ValueError("Вершини географічної та піксельної анотацій не збігаються")

        east, north = transform(
            "EPSG:4326",
            CRS,
            geographic_polygon[:, 0].tolist(),
            geographic_polygon[:, 1].tolist(),
        )
        pixel_points.extend(pixel_polygon)
        map_points.extend(zip(east, north))
        annotations.append((geographic["properties"], pixel_polygon))
        class_counts[geographic["properties"]["subtype"]] += 1

    pixels = np.asarray(pixel_points)
    map_coordinates = np.asarray(map_points)
    design = np.column_stack((pixels, np.ones(len(pixels))))
    affine, _, _, _ = np.linalg.lstsq(design, map_coordinates, rcond=None)
    residuals = map_coordinates - design @ affine
    gsd_x, gsd_y = np.linalg.norm(affine[0]), np.linalg.norm(affine[1])
    rms_residual = float(np.sqrt(np.mean(residuals**2)))
    if rms_residual > 0.1:
        raise ValueError(f"Перетворення анотацій неузгоджене: RMS={rms_residual:.3f} м")

    with rasterio.open(IMAGE_PATH) as source:
        image_data = source.read()
        profile = source.profile.copy()
        profile.update(
            driver="GTiff",
            crs=CRS,
            transform=Affine(
                affine[0, 0],
                affine[1, 0],
                affine[2, 0],
                affine[0, 1],
                affine[1, 1],
                affine[2, 1],
            ),
            compress="deflate",
        )
        with rasterio.open(GEOREFERENCED_PATH, "w", **profile) as output:
            output.write(image_data)
            output.update_tags(
                SOURCE_IMAGE=IMAGE_PATH.name,
                GEOREFERENCE_METHOD=(
                    "Least-squares affine fit from matching pixel and lon/lat "
                    "building annotation vertices"
                ),
                CAPTURE_DATE_AVAILABLE="no; not present in the source metadata",
            )

    selected_ids = {
        "0485feb5-4133-4eb9-9047-532da7bc1397",
        "d96cd91e-b6d7-4dd1-93c6-a62f92826794",
        "c97a9209-360f-46c9-8bb9-abe1e6da7d46",
        "e3b0f225-024d-4f1b-aa5c-7cfec853a44e",
        "e91cb31c-c78b-476b-9d61-eef242350afe",
    }
    class_names = {
        "minor-damage": "minor",
        "major-damage": "major",
        "destroyed": "destroyed",
    }
    rows = []
    for properties, polygon in annotations:
        uid = properties["uid"]
        if uid not in selected_ids:
            continue
        x_min, y_min = polygon.min(axis=0)
        x_max, y_max = polygon.max(axis=0)
        width_px, height_px = x_max - x_min, y_max - y_min
        rows.append(
            {
                "uid": uid,
                "damage_class": class_names[properties["subtype"]],
                "width_px": width_px,
                "height_px": height_px,
                "width_m_approx": width_px * gsd_x,
                "height_m_approx": height_px * gsd_y,
                "polygon": polygon,
            }
        )

    if len(rows) != len(selected_ids):
        raise ValueError("Не всі обрані анотації знайдено")

    with MEASUREMENTS_PATH.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "uid",
                "damage_class",
                "width_px",
                "height_px",
                "width_m_approx",
                "height_m_approx",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: value for key, value in row.items() if key != "polygon"}
            )
    image = Image.open(IMAGE_PATH).convert("RGB")
    image = Image.open(IMAGE_PATH).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    colors = {"minor": "#00a6ff", "major": "#ffd400", "destroyed": "#ff3b30"}
    for index, row in enumerate(rows, start=1):
        polygon = [tuple(point) for point in row["polygon"]]
        draw.line(polygon + [polygon[0]], fill=colors[row["damage_class"]], width=3)
        x_min = min(point[0] for point in polygon)
        y_min = min(point[1] for point in polygon)
        draw.text(
            (x_min, max(0, y_min - 14)),
            f"{index}: {row['damage_class']}",
            fill="white",
            font=font,
            stroke_width=2,
            stroke_fill="black",
        )
    annotated_canvas = Image.new("RGB", (image.width, image.height + 48), "white")
    annotated_canvas.paste(image, (0, 48))
    annotated_draw = ImageDraw.Draw(annotated_canvas)
    annotated_draw.text(
        (12, 8),
        "Rubizhne post-event sample | annotated building footprints",
        fill="black",
        font=font,
    )
    annotated_draw.text(
        (12, 28),
        "Blue: minor | Yellow: major | Red: destroyed (labels 1-5)",
        fill="black",
        font=font,
    )
    annotated_canvas.save(ANNOTATED_PATH)

    before = Image.open(PRE_IMAGE_PATH).convert("RGB")
    after = Image.open(IMAGE_PATH).convert("RGB")
    pair = Image.new("RGB", (before.width * 2, before.height + 48), "white")
    pair.paste(before, (0, 48))
    pair.paste(after, (before.width, 48))
    pair_draw = ImageDraw.Draw(pair)
    pair_draw.text((12, 8), "Rubizhne pre-event sample (exact date unavailable)", fill="black", font=font)
    pair_draw.text((before.width + 12, 8), "Rubizhne post-event sample (exact date unavailable)", fill="black", font=font)
    pair.save(PAIR_PREVIEW_PATH)

    with rasterio.open(IMAGE_PATH) as source:
        rgb = source.read([1, 2, 3])
        masks = source.read_masks(1)
        print(f"Image: {source.width} x {source.height} px, {source.count} bands")
        print(f"CRS: {CRS} (reconstructed from annotation coordinates)")
        print(f"GSD X/Y: {gsd_x:.3f} / {gsd_y:.3f} m/px")
        print(
            f"Footprint: {source.width * gsd_x / 1000:.3f} x "
            f"{source.height * gsd_y / 1000:.3f} km"
        )
        print(f"Affine-fit RMS residual: {rms_residual:.4f} m")
        print(f"Derived georeferenced raster: {GEOREFERENCED_PATH.name}")
        print(f"Invalid/transparent pixels: {(masks == 0).sum()} / {masks.size}")
        print(f"Post-event annotation counts: {dict(sorted(class_counts.items()))}")
        for band_index, band in enumerate(rgb, start=1):
            print(
                f"Band {band_index}: min={int(band.min())}, "
                f"max={int(band.max())}, valid pixels={int((masks > 0).sum())}"
            )
    print("Measurements (axis-aligned annotation bounds; not field survey):")
    for index, row in enumerate(rows, start=1):
        print(
            f"{index}. {row['damage_class']}: "
            f"{row['width_px']:.1f} x {row['height_px']:.1f} px "
            f"(approx. {row['width_m_approx']:.1f} x "
            f"{row['height_m_approx']:.1f} m)"
        )
    print(
        f"Saved {MEASUREMENTS_PATH.name}, {ANNOTATED_PATH.name}, "
        f"{PAIR_PREVIEW_PATH.name}, and {GEOREFERENCED_PATH.name}"
    )


if __name__ == "__main__":
    main()
