# Montage: setup, access, and steps

Public repo. Nothing here is a secret: no keys, passwords, tokens, phone numbers, or personal emails. Contacts are shared privately, not in this file.

Last updated: 10:50 AM Oct 24, 2026.

## What we are using

| Layer | Tool | Why |
|---|---|---|
| Room scan | iPhone video, ARKit poses logged | No LiDAR on iPhone 14, so no depth sensor |
| Room splat | gsplat / Nerfstudio splatfacto, on Modal GPU | Standard, runs headless |
| Depth check | MoGe-2 (MIT) | Metric depth on a clean license |
| Camera poses | VGGT (commercial checkpoint) | Poses from unordered video |
| Body pose | GVHMR (SMPL / SMPL-X models) | Global trajectory from one video. Research license |
| Ball | Hand-keyed keyframes, gravity arc fit | Fast, reliable; no detector to train |
| Viewer | Spark (three.js, WebGL2) | Mobile-friendly splat rendering |
| Viewer hosting | Firebase Hosting | Installable web app, one new project |
| Compute | Modal (GPU functions, Volume `montage-data`) | Heavy jobs off the laptop |
| Video | Remotion, ffmpeg | Frame-exact overlays; quick trims |
| Schedule | `montage-schedule.json` + desktop widget | Shows today's blocks |
| Repo | GitHub, public | Shared state for both agents |

## Access status

| Item | Status | Notes |
|---|---|---|
| GitHub (repo `EnesYilmazcode/montage`) | DONE | Pushed. Public |
| Modal | DONE | Logged in (workspace `galaxyenocan`). Volume `montage-data` exists |
| Firebase CLI login | DONE | Logged in as the account owner |
| Firebase project | DONE | Project ID `montage-hack-2026`. Viewer goes here |
| Gemini / fal.ai / Hugging Face keys | NOT NEEDED | Pipeline models are public. Revisit only for the pitch |
| SMPL and SMPL-X model files | TODO (human) | Needs a person to accept the license. Step 1 below |
| GVHMR checkpoints | No key needed | Downloaded from the authors' public Google Drive folder inside the Modal job |
| Friend's GitHub username | TODO (human) | Needed to add him as a collaborator |
| Video submit cutoff and method | TODO (human) | Confirm on the Discord or Devpost page |
| Hack OHIO organizer confirmation | TODO (human) | Confirm a pre-event scan counts as disclosed prior work |
| Capture location and phone | TODO (human) | Room with permission, and the phone your friend uses |

## Steps for you, one at a time

Do them in this order. Each step says when it's done.

**Step 1. SMPL and SMPL-X accounts.**
1. Open https://smpl.is.tue.mpg.de and create an account. Accept the license.
2. Download "SMPL for Python" (the `.pkl` files for neutral, male, and female).
3. Open https://smplx.is.tue.mpg.de, create or log in to the same kind of account, accept the license, and download the SMPL-X models (`SMPLX_NEUTRAL.npz` at least).
4. Put the files in one folder, for example `Downloads\smpl-files`.
5. Done when the folder has the `.pkl` and `.npz` files. Tell me the folder path. I will upload them to the Modal volume.

**Step 2. Confirm the video deadline.**
1. Open the hackathon Discord or the submission page.
2. Find the video submit cutoff and the submission method (Google Form, Devpost, or other).
3. Done when you can tell me the exact cutoff time. I will update the widget's countdown.

**Step 3. Friend's GitHub username.**
1. Give me his GitHub username. Do not paste it with any other personal details.
2. I will add him as a collaborator and he accepts the invite on GitHub.

**Step 4. Confirm the capture place and phone.**
1. Pick a room you have permission to film in, with a clear floor and at least one side view of a jump.
2. Tell me which phone your friend will use.
3. Done when both are settled.

**Step 5. Email the organizers (optional, but safer).**
1. I can draft a two-line email asking whether a pre-event room scan counts as disclosed prior work.
2. You approve the draft. I do not send it until you say so.

## Agent steps (done by the agent, not you)

- Create the Modal volume and upload the SMPL files, after Step 1.
- Build the room-splat Modal job, and test it on the first room clip.
- Build the viewer on Firebase, then deploy it to `montage-hack-2026`.
- Keep `CONTEXT.md` and `montage-schedule.json` current, and push after each change.

## Rules for this repo

- Public repo. No secrets, no contacts, no raw video, no splat files.
- Commit and push after each working change. Pull with rebase before pushing.
- Shared contacts: share them in a private message, not in this repo.
