# Conversion and metadata

PDF pages are rendered with pypdfium2. PDF text is extracted for page search; scanned PDFs need supplied metadata because this project does not include OCR. Input images are naturally sorted by filename, oriented using EXIF and never cropped or upscaled for detail. Prefer zero-padded page filenames.

Default page long edges are 1600 and 2400 pixels, with 320-pixel thumbnails. Quality 88 is the initial WebP setting. Inspect small type and line art before increasing compression. Mixed ratios are padded onto a consistent page canvas. An odd leaf count receives a neutral final leaf by default; `--no-pad-even` keeps the exact count. Cover and final leaf are treated as hard covers.

## Already-designed spreads

A PDF may contain two pages on each landscape sheet. Confirm whether it is a reader spread or print imposition before splitting. For a normal spread, split on its exact gutter without changing artwork, order left then right, and handle the outside cover separately (back on the left, front on the right). Do not guess print signatures or book order. The builder treats every supplied PDF page as one leaf; split spreads before calling it.

## Optional metadata

```json
{
  "description": "A coordinated collection for retail buyers.",
  "pages": {
    "2": {
      "title": "School bags",
      "alt": "Three school bags with dimensions and fabric details",
      "searchText": "BAG-001 recycled polyester school backpack",
      "links": [{
        "x": 10, "y": 20, "width": 40, "height": 30,
        "url": "/product/example-backpack/",
        "label": "View BAG-001 backpack"
      }]
    }
  }
}
```

Keys are one-based source page numbers. Hotspot coordinates are percentages of the source artwork; the builder maps them through any padding for mixed-ratio sources. Only http/https and same-site root-relative links are allowed. The reader's zoom view also exposes product links so they remain usable on touch devices.

## Publication

This repository contains generated neutral sample pages only. Keep private catalogue inputs and generated company plugins outside the repository. Source PDF inclusion is opt-in because it increases download size and exposes the original document publicly.
