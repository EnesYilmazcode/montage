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

## Net steps, in order (updated 11:05 AM Oct 24)

Cost estimates: an A100 80GB is about $2.50 per hour on Modal. Current balance is about $4.30. The test run needs about $2. A day of renders needs about $20.

1. **[Agent] Finish the UniWorld-View build and weight download.** Build is running; a clang fix is in. Done when the weights sit in the `montage-data` volume.
2. **[Agent] Test the demo on a sample clip from the repo.** One A100 80GB run, about $1 to $2. Done when a camera-path output comes back.
3. **[You] Top up Modal.** Tell me the amount first. You add it on the billing page yourself, since I can't add payment details.
4. **[You] Capture the room.** Walk the empty room with the phone, locked exposure, 3 to 5 minutes, with tilt-up passes for the ceiling. Send the file or the folder path.
5. **[You and friend] Capture the shot.** 3 to 6 clean jump shots from side and front spots, the ball in frame, a hoop or marker visible. Send the files.
6. **[Agent] Upload and process the room.** Build the background splat on Modal, about $1 to $2.
7. **[Agent] Run UniWorld-View on the real shot,** with a camera path around the shooter. Compare the output against the source frames.
8. **[Agent] Decide the composite.** Either the generated flyaround already shows the room, or we merge it with the room splat, which needs the frame alignment step.
9. **[Agent] Build the video.** Remotion, with clear labels: REAL footage, and GENERATED views. About 3 minutes.
10. **[You] Review and approve** the cut, then submit it on the hackathon form.

Deadlines to hit: the first test result by 6 PM, the first full render by 11 PM, scope freeze at 6 AM, record 7:30 to 9:00 AM, submit by 9:30 AM Oct 25.

## Friend's Modal account: options (unverified; the billing docs do not say)

- Credits and volumes are most likely per workspace, so his $30 pays only for jobs run from his workspace. Check his Modal dashboard before relying on this.
- Model weights come from Hugging Face. His workspace can download them directly, in parallel, without waiting on ours. That costs his storage and build time.
- Simplest option: keep all GPU runs in one workspace, topped up by card. If he wants to use his credits, he runs the same app under his own login. Nobody shares tokens.
- Do not share Modal tokens, keys, or login details here or in chat.

## Agent steps (done by the agent, not you)

- Create the Modal volume and upload the SMPL files, after Step 1.
- Build the room-splat Modal job, and test it on the first room clip.
- Build the viewer on Firebase, then deploy it to `montage-hack-2026`.
- Keep `CONTEXT.md` and `montage-schedule.json` current, and push after each change.

## SMPL license limits (from the SMPL-Model License text)

- Research, education, and artistic use only, non-commercial. The license is personal to the person who downloads the files.
- The files may not be shared or redistributed to a third party. Keep the SMPL files only in the Modal volume (`montage-data`) or on the laptop.
- Your friend should download his own copy on his own account, if his agent runs the body model.
- Ship only rendered output (video or images), never the model files and never a live service that runs the body model.

## Rules for this repo

- Public repo. No secrets, no contacts, no raw video, no splat files.
- Commit and push after each working change. Pull with rebase before pushing.
- Shared contacts: share them in a private message, not in this repo.
