# Video script: "Your data stays on your Mac" (about 80 seconds)

Style: 3Blue1Brown-like. Dark background, one idea per scene. Narration is in STE.
Source: `scene.py` (Manim). Not rendered yet. See "Status" below.

| # | Time | On screen | Narration |
|---|---|---|---|
| 1 | 0:00-0:08 | A question box appears: "Can I afford a holiday?" | You ask a question about your money. |
| 2 | 0:08-0:20 | A shield checks the question. A bad question ("ignore all rules") bounces off. | First, the Prompt Guard checks your words. It blocks attempts to trick the assistant. |
| 3 | 0:20-0:34 | Three small tools feed a box labelled "Verified data": bank rate, your spending, your credit. | Next, the assistant gets facts. It reads your own accounts. It also reads live bank rates. |
| 4 | 0:34-0:48 | The box moves to the AI Gateway. An arrow goes to a laptop icon. A cloud icon is greyed out. | Then the Gateway sends the question to a model on your Mac. Your data does not go to the cloud. |
| 5 | 0:48-0:60 | The Gateway goes red. A direct arrow to the laptop turns green. | If the Gateway stops, the app calls the local model directly. You still get an answer. |
| 6 | 0:60-0:80 | The answer appears: "£3,700 left. Runway: 62 days." | The answer uses only your verified numbers. It does not guess. |

## Status

- Rendered: `gateway-story.mp4` (80 s, 480p, H.264 + AAC, 0.8 MB). I checked six frames by eye. I did not watch or listen to the full video.
- Tools installed for this: `ffmpeg`, `cairo`, `pango`, `pkg-config` (Homebrew). Manim runs through `uv run --with manim`, so nothing was added to the project.
- Narration uses the macOS `say` voice Samantha. It is a basic voice. Each line is much shorter than its scene (2 to 6 s in a 8 to 20 s slot), so the video has long silent gaps. Fix this by shortening the scene lengths in `SCENE_ENDS` in `scene.py`, or by adding more narration.
- Render again: `uv run --with manim manim -ql docs/explain/video/scene.py GatewayStory`. Use `-qh` for 1080p.
- For better audio, put an ElevenLabs key in the `ELEVENLABS_API_KEY` environment variable. Never write it into a file.
