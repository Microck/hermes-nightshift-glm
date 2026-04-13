---
name: optimo
description: Optimize and convert images and videos using format-specific compression pipelines on top of ImageMagick and FFmpeg. Use when users need to reduce image or video file sizes, batch-optimize a media directory, convert between formats (JPEG, PNG, WebP, AVIF, HEIC, JXL, MP4, WebM, MOV), resize media by percentage/dimensions/target file size, strip audio tracks from videos, or output optimized images as data URLs.
---

# optimo

`optimo` reduces media size with format-specific compression pipelines.

## Prerequisites

`optimo` resolves compressors from `PATH` and throws if required binaries are missing.

Required by format:
- all ImageMagick-backed formats: `magick`
- SVG pipeline: `svgo`
- JPEG second pass: `mozjpegtran` or `jpegtran`
- GIF second pass: `gifsicle`
- video pipeline: `ffmpeg`

## Quick Start (CLI)

Use `npx` for one-off runs:

```bash
npx -y optimo public/media
```

Optimize a single file:

```bash
npx -y optimo public/media/banner.png
```

Preserve image EXIF metadata:

```bash
npx -y optimo public/media/banner.jpg --preserve-exif  # long version
npx -y optimo public/media/banner.jpg -p              # short version
```

Run a dry run (no file changes):

```bash
npx -y optimo public/media/banner.png --dry-run  # long version
npx -y optimo public/media/banner.png -d         # short version
```

Enable lossy mode:

```bash
npx -y optimo public/media/banner.jpg --lossy  # long version
npx -y optimo public/media/banner.jpg -l       # short version
```

Convert and optimize to a new format:

```bash
npx -y optimo public/media/banner.png --format jpeg  # long version
npx -y optimo public/media/banner.png -f jpeg         # short version
```

Optimize a video:

```bash
npx -y optimo public/media/clip.mp4
```

Convert video format:

```bash
npx -y optimo public/media/clip.mov --format webm
```

Mute video audio tracks (default is already muted):

```bash
npx -y optimo public/media/clip.mp4 --mute          # explicit true
npx -y optimo public/media/clip.mp4 --mute false     # keep audio
```

Resize by percentage:

```bash
npx -y optimo public/media/banner.png --resize 50%  # long version
npx -y optimo public/media/banner.png -r 50%         # short version
```

Resize to a target max file size (images only):

```bash
npx -y optimo public/media/banner.png --resize 100kB  # long version
npx -y optimo public/media/banner.png -r 100kB         # short version
```

Resize by width:

```bash
npx -y optimo public/media/banner.png --resize w960  # long version
npx -y optimo public/media/banner.png -r w960         # short version
```

Resize by height:

```bash
npx -y optimo public/media/banner.png --resize h480  # long version
npx -y optimo public/media/banner.png -r h480         # short version
```

Output optimized image as data URL (single image file only):

```bash
npx -y optimo public/media/banner.png --data-url  # long version
npx -y optimo public/media/banner.png -u          # short version
```

Enable verbose debugging:

```bash
npx -y optimo public/media/banner.heic --dry-run --verbose  # long version
npx -y optimo public/media/banner.heic -d -v                  # short version
```

## Pipelines

`optimo` selects a pipeline by output format:

- `.png` -> `magick.png`
- `.svg` -> `svgo.svg`
- `.jpg/.jpeg` -> `magick.jpg/jpeg` + `mozjpegtran.jpg/jpeg` (lossless JPEG without resize or conversion skips magick and runs only mozjpegtran)
- `.gif` -> `magick.gif` + `gifsicle.gif`
- other image formats (`webp`, `avif`, `heic`, `heif`, `jxl`, etc.) -> `magick.<format>`
- video formats (`mp4`, `m4v`, `mov`, `webm`, `mkv`, `avi`, `ogv`) -> `ffmpeg.<format>`

Mode behavior:
- default: lossless-first pipeline
- default image behavior strips metadata/EXIF for smaller files
- `--lossy` / `-l`: lossy + lossless pass where supported
- `--mute` / `-m`: remove audio tracks from videos (default: `true`; pass `--mute false` to keep audio)
- `--preserve-exif` / `-p`: keep image EXIF metadata in outputs

## Recommended Workflow

1. Start with `--dry-run` to confirm target files.
2. Run optimization on one file first, then scale to directories.
3. Use `--format` only when conversion is intended.
4. Use `--resize` only when explicit dimension/size control is required.
5. For videos, note `--resize 100kB` is not supported; use `50%`, `w960`, or `h480`.
6. Use `--verbose` when diagnosing unsupported files or binary/flag issues.
7. Verify outputs in version control before committing.

## CLI Options

- `-d`, `--dry-run`: Show what would change without writing files.
- `-f`, `--format`: Convert output format (`jpeg`, `webp`, `avif`, etc.).
- `-l`, `--lossy`: Enable lossy + lossless pass.
- `-m`, `--mute`: Remove audio tracks from videos (default: `true`; use `--mute false` to keep audio).
- `-p`, `--preserve-exif`: Preserve image EXIF metadata (default: `false`).
- `-r`, `--resize`: Resize using percentage (`50%`), max file size (`100kB`, images only), width (`w960`), or height (`h480`).
- `-s`, `--silent`: Suppress per-file logs.
- `-u`, `--data-url`: Return optimized image as data URL (single image file only).
- `-v`, `--verbose`: Print debug logs (pipeline selection, command execution, and errors).

## Programmatic API

```js
const optimo = require('optimo')

await optimo.file('/absolute/path/image.jpg', {
  dryRun: false,
  lossy: false,
  preserveExif: false, // default
  format: 'webp',
  resize: '50%',
  onLogs: console.log
})

await optimo.file('/absolute/path/image.jpg', {
  preserveExif: true, // keep EXIF metadata
  onLogs: console.log
})

await optimo.file('/absolute/path/image.jpg', {
  resize: '100kB',
  onLogs: console.log
})

await optimo.file('/absolute/path/image.jpg', {
  resize: 'w960',
  onLogs: console.log
})

const { dataUrl } = await optimo.file('/absolute/path/image.png', {
  dataUrl: true,
  onLogs: console.log
})
// dataUrl is a base64 data URL string (images only, single file)

await optimo.file('/absolute/path/video.mp4', {
  lossy: false,
  mute: false,  // true by default for videos
  format: 'webm',
  resize: 'w1280',
  onLogs: console.log
})

const result = await optimo.dir('/absolute/path/images')
console.log(result)
// { originalSize, optimizedSize, savings }

// Utility export
const { formatBytes } = require('optimo')
console.log(formatBytes(1024))
// '1 kB'
```

## Behavior Notes

- For non-conversion runs, if the optimized file is not smaller, the original file is kept.
- During conversion, output uses the new extension and the original source file is removed (unless `--dry-run`).
- Hidden files and folders (names starting with `.`) are skipped in directory mode.
- Unsupported files are reported as `[unsupported]` and ignored.
- Video defaults are tuned for web compatibility (`yuv420p`, fast-start MP4 where applicable).
- Image outputs strip EXIF metadata by default; use `--preserve-exif` or `preserveExif: true` to keep it.
- `--data-url` is only supported for single image files (throws for videos or directory mode).
