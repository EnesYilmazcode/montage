# Montage: shared context for both agents

Read this first. It is the shared state. Keep it short and current. Contacts and keys never go in this repo (the repo is public).

## What we are building

A 3-minute demo video for HackOHI/O 2026. A real jump shot is placed inside a real scanned room, and a virtual camera flies an arc around it, with play, pause, and replay. The video is what judges see first.

## Clock (plan is in `montage-schedule.json`; the desktop widget shows it)

- Hacking: started Sat Oct 24, 10:00 AM. Ends Sun Oct 25, 10:00 AM.
- Judging: Sun Oct 25, 10:30 to 11:00 AM (virtual).
- Video submit: planned 09:30 AM Oct 25. **The real cutoff is not confirmed.** Confirm it.
- Record block: 90 minutes, 07:30 to 09:00 AM Oct 25.
- Freeze of features: 06:00 AM Oct 25.

## Scope (locked)

The smallest convincing demo, agreed with an independent review:

1. A real side-view jump clip, shown raw first.
2. The real room, as a static splat, with the shot placed at a marked floor point.
3. A hand-keyed ball trail (5 to 10 manual keyframes, gravity arc).
4. One restrained camera arc of 30 to 40 degrees around observed geometry. End on a higher room or ball view.
5. Labels: "REAL: phone footage" and "RENDERED: virtual camera over pose data". Show "pre-rendered from run [date]".

**Cut first, in order:** MoVieS / dynamic human splats, multi-phone capture, overhead view of the player, live Modal processing, PWA install and mobile deploy, scrubbing and toggles, automatic ball detection, multiple shots.

**Not in scope:** photoreal dynamic human, overhead view of the shooter, any claim that the render is live or measured.

## Pipeline contracts (both agents write to these; do not change without telling the other)

- `data/room/`: the room splat file (.ply or .spz), and `room_poses.json` (camera poses, scale check).
- `data/shot/`: `shot.mp4` (side-view clip, the one we use), `skeleton.json` (per frame: 3D joints in room frame, meters), `ball.json` (per frame: x, y, z in room frame, meters, plus `manual: true|false`).
- `data/align.json`: the four floor points (room frame and shot frame) and the resulting transform.
- `camera_path.json`: keyframes (time, position, look-at).
- Output: `out/montage-run-<date>.mp4` and its label text.

Units are meters, y-up, floor at y = 0. Any figure that is estimated, not measured, must say so in the label.

## Ownership (proposal, confirm with the friend)

- **Enes's agent:** room capture, Modal jobs, room splat, viewer, camera path, video edit.
- **Friend's agent:** shot capture logs, skeleton (pose run), ball keyframes, alignment.
- Both: the schedule, and any change to a file contract above.

## Repo rules

- Commit after every working change. Push at least once an hour, and before every hand-off.
- Before pushing: `git pull --rebase`, then `git push`.
- Small commits with plain messages. No AI attribution lines.
- Do not commit raw video or splat files. Use the Modal Volume or a shared drive, and record the path in this file.
- Research notes (`research-*.md`, `STACK.md`, and similar) stay local, as `.gitignore` says.

## Constraints

- Gym: not used. The location for capture is TBD. Pre-event scans must be disclosed as prior work. Judging counts only work done during the event.
- GVHMR and SMPL/SMPL-X: research-use licenses. Ship the output as rendered video only. No live endpoint that runs the body model.
- Atlas (World Labs): not reachable. Marble is self-serve if a generated view is needed. Label any generated pixels.

## Open requirements (owner in brackets)

1. Confirm the video submit cutoff and submission method (Discord form or Devpost). [Enes]
2. Create SMPL and SMPL-X accounts, accept their licenses, and get the model files to Modal. [Enes; the license must be accepted by a person]
3. Friend's GitHub username, to add as a collaborator. [Enes]
4. Capture location with permission, and the phone the friend uses. [Enes and friend]
5. Firebase project for the viewer, a new site (not a personal one). [Enes]
6. Confirm Modal GPU budget for the overnight renders. [Enes]

## Status log

- Tested image pipeline: `modal_uniworld.py` runs the bundled UniWorld-View room image on an A100 80GB. Completed a 49-frame orbit (6.125s) and an 81-frame translated flight (10.125s), both 544x736. Generated examples are in `examples/`; full local artifacts are in `outputs/uniworld/` and `outputs/uniworld-flight/`. Weights persist in `uniworld-view-data` in the `colinl-code` Modal workspace, separate from `montage-data`. All test jobs are stopped. The CLI wrapper includes dependency pins and a repaired checkpoint loader. These tests cover single-image generation; real footage and dynamic-video inference remain untested by this runner.

- 10:10 AM Oct 24: repo public; schedule widget live; scope locked; capture not started.
- 10:40 AM Oct 24: candidate method found: World from Motion (arXiv 2607.01202; code github.com/GradientSpaces/World-from-Motion; weights on Hugging Face). Dynamic 4D Gaussians from monocular video, plus generated novel views. License and runtime not yet confirmed. Research fleet running (code audit, paper read, generator scout, room integration). No decision yet. Generated views must be labeled.
- Fleet result (all four reports in the montage folder, local only): World from Motion is a NO-GO for this hackathon. Its video pipeline needs a private weights bundle, and its own tests do not cover handheld or fast motion. Its generator invents views and was trained on synthetic data.
- Next candidate: TrajectoryCrafter, after its license is read. Fallback: real takes plus room splat, with any generated view labeled.
- Merge risk: the room and the subject must share one frame. Estimate a Sim(3) from marker and background points, and check the feet on the floor.
- 10:50 AM Oct 24: World from Motion weights are public (wfm-step-12500, 16.6 GB), but the checkpoint doesn't run on a new clip without the private bundle. New candidate: UniWorld-View (github.com/PKU-YuanGroup/UniWorld-View, Apache-2.0; weights at Drexubery/UniView on Hugging Face). It takes a raw video, handles pose and depth internally, and has a Gradio demo. Needs 60 GB+ VRAM (A100 80GB). The Modal build is in `pipeline/uniworld_app.py`, running in the background now. No documented CLI for a custom video, so test through the Gradio app.
- 11:11 AM Oct 24: Modal environment build finished. The weight download is now running on Modal (1 active task). Not yet confirmed complete.
- 12:20 PM Oct 24: first direct test failed. Cause: upstream `demo.py` comments out the STream3R load line, so the stream3r geometry path raises AttributeError. Fix in `run_test`: uncomment that one line inside the container, then rerun. Fallback if it still fails: the `mosca` geometry backend, which needs a precompute step first.
- 12:05 PM Oct 24: the Gradio demo kept restarting and timing out, so I stopped `modal serve` to stop GPU charges. Switched to a direct test: `run_test` in `pipeline/uniworld_app.py` runs the repo's `inference.py` with the same flags as `run_infer.sh`, on the 5-second basketball clip at `inputs/test_clip.mp4` in the volume, with a 50-degree orbit. Running now on an A100 80GB. Output goes to `outputs/` in the volume.
- 11:20 AM Oct 24: weights confirmed in the montage-data volume under `ckpt/` (UniView, Wan2.1-VACE-14B, BLIP2, SAM2, MoGe, tracer_b7, loras, STream3R). Starting the Gradio demo with `modal serve pipeline/uniworld_app.py` on an A100 80GB. Next: confirm it loads and test it on a sample clip. The laptop only streams logs. Team budget: about $4.30 on Enes's workspace; a test needs about $2, and a day of renders about $20. Friend has a separate Modal account with $30 in free credits. Open question: whether his credits can pay for our runs (see SETUP.md).
- Status: capture has not started. The capture block is starting now (schedule: 10:40 to 11:30 AM). Needs: a room, the friend's GitHub username, and a go on the real-take plan.
