#!/usr/bin/env python3
"""Generate original, non-commercial sample page artwork with Pillow only.

No photographs, logos, company data, or external downloads are used. Illustrations
are diagrammatic examples, not product specifications or claims. Existing output
is never overwritten. Pass the resulting pages folder to the normal builder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SIZE = (1200, 1600)
INK = "#21362E"
PAPER = "#F4F0E7"
OLIVE = "#9DA579"
CLAY = "#B76F50"
MUTED = "#666C60"
PAGE_TITLES = ["Field Notes", "A quieter everyday", "Carry / Tote", "Carry / Details", "Desk / Journal", "Desk / Details", "Journey / Bottle", "Journey / Details", "Studio / Light", "Studio / Details", "Collection index", "Made for the everyday"]


def font(size: int, display: bool = False):
    candidates = (["C:/Windows/Fonts/georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "DejaVuSerif.ttf"] if display else ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"])
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def text(draw, xy, value, size=28, color=INK, display=False):
    draw.text(xy, value, font=font(size, display), fill=color, spacing=18)


def footer(draw, number, light=False):
    color = PAPER if light else INK
    draw.line((86, 1480, 1114, 1480), fill=color, width=1)
    text(draw, (86, 1510), "FIELD NOTES / SAMPLE COLLECTION", 18, color)
    text(draw, (1070, 1504), f"{number:02d}", 28, color)


def product(draw, kind, box, color=OLIVE):
    """Original simple vector-like objects, sized within an illustration panel."""
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    def rect(x1, y1, x2, y2):
        return (round(left + width*x1), round(top + height*y1), round(left + width*x2), round(top + height*y2))
    draw.ellipse(rect(.18, .90, .82, .97), fill="#D4D2C6")
    if kind == "tote":
        draw.rounded_rectangle(rect(.33, .06, .67, .44), radius=int(width*.17), outline=INK, width=max(2, int(width*.035)))
        draw.polygon([rect(.20,.29,.20,.29)[:2], rect(.80,.29,.80,.29)[:2], rect(.89,.89,.89,.89)[:2], rect(.11,.89,.11,.89)[:2]], fill=color)
        draw.line([rect(.25,.32,.25,.32)[:2], rect(.21,.86,.21,.86)[:2]], fill=PAPER, width=3)
        draw.line([rect(.75,.32,.75,.32)[:2], rect(.79,.86,.79,.86)[:2]], fill=PAPER, width=3)
        draw.rectangle(rect(.42,.56,.58,.62), fill=PAPER)
    elif kind == "journal":
        draw.rounded_rectangle(rect(.19,.13,.83,.90), radius=12, fill=INK)
        draw.rounded_rectangle(rect(.23,.12,.83,.87), radius=12, fill=PAPER, outline=INK, width=2)
        draw.rounded_rectangle(rect(.16,.08,.78,.84), radius=12, fill=color)
        draw.line(rect(.22,.10,.22,.82), fill=INK, width=5)
        draw.line(rect(.67,.08,.67,.84), fill=INK, width=max(3,int(width*.025)))
        draw.rectangle(rect(.30,.25,.58,.28), fill=PAPER)
    elif kind == "bottle":
        draw.rounded_rectangle(rect(.35,.11,.65,.25), radius=10, fill=INK)
        draw.rounded_rectangle(rect(.30,.23,.70,.91), radius=int(width*.09), fill=color)
        draw.rounded_rectangle(rect(.35,.30,.39,.81), radius=6, fill="#C7C9AB")
        draw.ellipse(rect(.39,.53,.61,.66), outline=PAPER, width=3)
    elif kind == "lamp":
        draw.ellipse(rect(.24,.84,.78,.93), fill=INK)
        draw.line([rect(.53,.38,.53,.38)[:2], rect(.53,.86,.53,.86)[:2]], fill=INK, width=max(4,int(width*.025)))
        draw.pieslice(rect(.18,.08,.88,.63), start=180, end=360, fill=color)
        draw.ellipse(rect(.18,.30,.88,.37), fill=CLAY)
        draw.ellipse(rect(.40,.31,.64,.36), fill="#F4DFAE")


def cover(number, back=False):
    image = Image.new("RGB", SIZE, INK)
    draw = ImageDraw.Draw(image)
    text(draw, (86, 84), "OBJECTS / SPACES / EVERYDAY RITUALS", 23, PAPER)
    if back:
        text(draw, (86, 310), "Made for\nthe everyday.", 102, PAPER, True)
        draw.ellipse((680, 790, 1280, 1390), fill=OLIVE)
        text(draw, (86, 1110), "A demonstration catalogue.\nOriginal geometric artwork.\nNo commercial product claims.", 27, PAPER)
    else:
        text(draw, (78, 248), "Field\nNotes", 176, PAPER, True)
        draw.rectangle((710, 220, 1110, 1120), fill=OLIVE)
        draw.ellipse((570, 860, 1110, 1400), fill=CLAY)
        text(draw, (86, 1070), "A considered collection\nfor a quieter everyday.", 36, PAPER)
        text(draw, (86, 1320), "SAMPLE EDITION / 01", 24, PAPER)
    footer(draw, number, True)
    return image


def introduction():
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    text(draw, (86, 90), "THE COLLECTION", 24, MUTED)
    text(draw, (80, 245), "A quieter\neveryday.", 108, INK, True)
    text(draw, (86, 600), "Four small chapters. One coherent collection.\nObjects drawn from simple shapes, soft colors,\nand the routines that make a day feel our own.", 32)
    entries = [("01", "Carry", "A place for what matters."), ("02", "Desk", "Space to think clearly."), ("03", "Journey", "Take the long way home."), ("04", "Studio", "A little pool of light.")]
    for index, (number, title, caption) in enumerate(entries):
        y = 865 + index*132
        draw.line((86, y-20, 1114, y-20), fill="#C8CABC", width=1)
        text(draw, (86, y), number, 24, MUTED)
        text(draw, (180, y-10), title, 48, INK, True)
        text(draw, (560, y), caption, 26, MUTED)
    footer(draw, 2)
    return image


def chapter(number, category, title, kind, color, code):
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    text(draw, (86, 80), f"{category.upper()} / COLLECTION", 24, MUTED)
    text(draw, (80, 166), title, 105, INK, True)
    draw.rectangle((86, 350, 1114, 1250), fill="#E7E6DA")
    product(draw, kind, (210, 380, 990, 1225), color)
    text(draw, (86, 1312), code, 24, MUTED)
    text(draw, (550, 1304), "Simple forms. Everyday utility.", 28)
    footer(draw, number)
    return image


def details(number, category, title, kind, color, code):
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    text(draw, (86, 80), f"{category.upper()} / DETAILS", 24, MUTED)
    text(draw, (80, 182), "Less, but better.", 80, INK, True)
    draw.rectangle((86, 365, 620, 1080), fill="#E7E6DA")
    product(draw, kind, (110, 400, 590, 1035), color)
    text(draw, (690, 435), title, 42, INK, True)
    text(draw, (690, 525), code, 23, MUTED)
    text(draw, (690, 640), "FORM\nA clean silhouette.\n\nPALETTE\nQuiet, earthy tones.\n\nPURPOSE\nAn everyday ritual.", 25, INK)
    draw.line((86, 1160, 1114, 1160), fill="#C8CABC", width=1)
    text(draw, (86, 1220), "A note on this sample", 33, INK, True)
    text(draw, (86, 1285), "Illustrations and descriptions demonstrate page layout only.\nReplace with your own approved product details before publishing.", 25, MUTED)
    footer(draw, number)
    return image


def index_page():
    image = Image.new("RGB", SIZE, OLIVE)
    draw = ImageDraw.Draw(image)
    text(draw, (86, 90), "AT A GLANCE", 24)
    text(draw, (80, 250), "Collection\nindex.", 112, INK, True)
    rows = [("FN-001", "Everyday tote", "03"), ("FN-002", "Pocket journal", "05"), ("FN-003", "Daily bottle", "07"), ("FN-004", "Studio light", "09")]
    for index, (code, title, page) in enumerate(rows):
        y = 695 + index * 150
        draw.line((86, y-25, 1114, y-25), fill=INK, width=1)
        text(draw, (86, y+6), code, 23)
        text(draw, (330, y), title, 40, INK, True)
        text(draw, (1060, y+2), page, 28)
    text(draw, (86, 1365), "EXPLORE / TURN / DISCOVER", 24)
    footer(draw, 11)
    return image


def generate(output: Path):
    if output.exists():
        raise ValueError("Demo output already exists; choose a new directory")
    output.mkdir(parents=True)
    pages_dir = output / "pages"
    pages_dir.mkdir()
    images = [cover(1), introduction()]
    items = [("Carry", "Everyday tote", "tote", OLIVE, "FN-001"), ("Desk", "Pocket journal", "journal", CLAY, "FN-002"), ("Journey", "Daily bottle", "bottle", OLIVE, "FN-003"), ("Studio", "Studio light", "lamp", "#D2B487", "FN-004")]
    for category, title, kind, color, code in items:
        images.append(chapter(len(images)+1, category, title, kind, color, code))
        images.append(details(len(images)+1, category, title, kind, color, code))
    images.extend([index_page(), cover(12, True)])
    pages = {}
    for number, image in enumerate(images, 1):
        image.save(pages_dir / f"page-{number:03d}.png", optimize=True)
        image.close()
        title = PAGE_TITLES[number-1]
        pages[str(number)] = {"title": title, "alt": f"Original demonstration catalogue: {title}", "searchText": title}
    for number, (_, title, _, _, code) in zip((3, 5, 7, 9), items):
        pages[str(number)]["searchText"] += f" {code} {title}"
    pages["11"]["links"] = [{"x": 7, "y": 84, "width": 68, "height": 6, "url": "https://example.com/", "label": "Open demonstration link (example.com)"}]
    metadata = {"description": "An original twelve-page sample catalogue. Artwork is geometric and contains no real company or product data.", "pages": pages}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = generate(args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Demo generation failed: {error}\n")
    print(f"Created 12 original pages in {output / 'pages'}")
    print(f"Metadata: {output / 'metadata.json'}")


if __name__ == "__main__":
    main()
