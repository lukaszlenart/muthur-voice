# Examples

Each folder is a ready intro: a Polish `intro.txt`, a `muthur.toml` and a `background.jpg`.

| Folder | Scene | Shows |
|---|---|---|
| `wake-up` | hibernation pods, crew wakes up | the defaults (Zofia through the intercom) |
| `corridor` | ship corridor, systems alert | Marek at `-15%`, `-10Hz` |
| `orbit` | planet from orbit, arrival | `voice_fx = "echo"` |
| `signal` | freighter silhouette, distress signal | `upper = false`, `wrap = 46` |
| `cold-start` | reactor core, ship powers up | a [boot sequence](../README.md#boot-sequence) before the narration, `boot_type_speed = 26`, `boot_hold = 2.5` |

```fish
uv run muthur render examples/orbit/intro.txt --config examples/orbit/muthur.toml
uv run muthur render examples/orbit/intro.txt --config examples/orbit/muthur.toml --no-tts   # silent preview
```

The video is written next to the intro (`examples/orbit/intro.mp4`). Paths in a config are
relative to that config, so `image = "background.jpg"` always means the file beside it; copy a
folder to start your own.

The backgrounds are drawn by `make_backgrounds.py` (Pillow only, fixed seed). After changing it:

```fish
uv run python examples/make_backgrounds.py
```
