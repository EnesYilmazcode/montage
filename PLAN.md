# Montage: plan (proposed, 2026-10-24, 10:40 AM)

Status: proposal. Needs a go from both people before the schedule changes.

## The ideal, in one paragraph

A pre-scanned room. The friend films a shot on one phone. The virtual camera flies around while the real shot plays, and the room is real. No white space, no visible 3D models of people, nothing that looks like a render of a person. Real pixels wherever we can get them.

## What we learned from the research

- **Shape of Motion** (MIT code, ICCV 2025): rebuilds a moving subject in 3D from one video. It needs a lot of preprocessing: depth, masks, camera poses (MegaSaM), and tracks. The page gives no runtime or hardware numbers. Its demos show a white background, and the page doesn't say why. Likely the method outputs only the moving subject. Its output is a 3D reconstruction, which is the "fake-looking" part we want to avoid.
- **The white background is the problem we don't need to solve.** A room scan gives us the background. Filling white space with a generative model is unnecessary, and it would put invented pixels in front of the judges.
- **Robust Video Matting** (GPL-3.0): cuts the person out of each frame without a trimap. The repo reports about 170 fps at HD on an RTX 3090. Fast enough for every take. GPL-3.0 applies if we copy its code into the repo. We can call it as a separate tool and not vendor it. Check before shipping.

## The plan: real pixels, placed in a real room

1. **Room:** a walk-around scan with no people, locked exposure, and tilt-up passes for the ceiling. Build a splat. This is the background, rendered as the camera flies.
2. **Shooter:** matte the shooter out of each real take with RVM. Place each take's matte as a flat card at the marked floor point, scaled to real height. Use the hoop (3.05 m) or a marker as the scale check.
3. **Multiple takes:** the friend shoots the same shot from 6 to 8 floor spots in a half-circle. Sync the takes on the ball's release frame. Each take is one real viewpoint.
4. **Camera:** the virtual camera stays inside the arc the takes cover. When it moves, show the take closest to its angle, with a short crossfade between neighbors. This uses only real pixels and avoids inventing a back or top of the body.
5. **Ball:** crop the real ball and place it on the tracked path. Hand-click the keyframes. The ball is small, so use hand keying, not detection.
6. **Shadow:** project the matte onto the floor, blurred and darkened. This is an approximation. The judges will see it, so keep the room lighting the same across takes.
7. **Output:** a pre-rendered 3-minute video, labeled. Raw takes shown first, then the room, then the fly-around. Label any generated or approximated element, such as the shadow.

## Why not the other options

- **Full 4D reconstruction (Shape of Motion):** the most angles, but the highest risk. Preprocessing is heavy, fast jumps are hard, and the output looks like a 3D model. Stretch goal only.
- **Generative background fill:** not needed with a room scan. It adds invented pixels that we'd have to explain.
- **Generative re-camera of one clip:** angles are generated, not captured. Useful as an extra, not the core.

## Limits (say these in the video)

- Angles are only as good as the takes. Beyond the covered arc, we don't show the shooter.
- A card looks flat when viewed from far off its angle. Estimate: keep the camera within about 30 to 40 degrees of a take.
- The shadow and the matte edges are approximate.

## Capture checklist

- Room: empty, locked exposure, same lighting for every take.
- Takes: 6 to 8 spots marked on the floor, same shot each time, the ball released in frame, hold 1 second at release.
- Scale: one visible marker and the hoop in the frame.
- Audio optional: a clap, to help sync.

## Pipeline steps

| Step | Tool | Output | License note |
|---|---|---|---|
| Room scan | Phone video, Modal | Room splat | Own footage |
| Matte | Robust Video Matting | Alpha + foreground per frame | GPL-3.0; call as a separate tool |
| Sync | Ball release frame | Offset per take | None |
| Scale check | Hoop, marker | Meters per pixel | None |
| Camera path | Keyframes | `camera_path.json` | None |
| Render | Splat renderer + cards | Frames | Check renderer license |
| Video | Remotion, ffmpeg | 3-minute mp4 | Music: pick a license |

## Schedule impact (not applied yet)

- Remove: pose run (GVHMR), skeleton JSON, the body-model downloads.
- Add: matting per take, card placement, multi-take sync.
- The capture block needs 6 to 8 takes instead of 10 jumps.

## Decisions needed

1. Go on the multi-take real-pixel plan above.
2. Confirm the room. Capture needs a room you can film in, with no people.
3. The friend's phone and his GitHub username.

## Current plan (updated 1:50 PM Oct 24)

What changed: Marble Developer API access works. `images2PosedRGBD` returns a camera pose and a depth map for each frame, from ordinary photos. That gives us room geometry without LiDAR. The Studio tool "Atlas Preview" makes generated views. Generated views stay labeled. The real path stays the core.

Steps, in order:
1. **Room walk-around (you).** 30 to 60 seconds, slow, chest height, no people, tilt up for the ceiling. Also measure one wall length with a tape. We use it as the scale check.
2. **Shot clip (you and friend).** About 10 seconds from the side, the shooter in frame, same room.
3. **Frames.** Pull about 40 to 80 frames from the walk-around, one per second. Pull 10 to 20 frames from the shot clip.
4. **Geometry test.** Send 8 frames through the API first to check the limits. Then run the full set in one job, room and shot frames together. If they share one coordinate frame, registration is solved. Check the scale against the tape measure.
5. **Room splat.** Build the room splat on Modal, using the API poses and depths as the starting points.
6. **Shooter.** Cut the shooter out of the shot frames with SAM2 (its weights are already on the volume). Place the cutout on the floor spot from the registered shot cameras.
7. **Camera path.** A scripted fly-through, staying inside the observed views. Keep the orbit within about 30 to 40 degrees of the shot camera.
8. **Optional generated extra.** Run an Atlas Preview view on a room photo for one wider shot. Label it GENERATED on screen.
9. **Video.** About 3 minutes, in Remotion. Raw footage first, then the room, then the fly-through. Label REAL and GENERATED. Credits and a short honesty note at the end.
10. **Publish.** Host the final mp4 on Firebase Hosting (free). Submit by the deadline.

Deadline reference: submit by 9:30 AM Oct 25, not yet confirmed.

## Correction (3:40 PM Oct 24)

- Atlas is an API. It needs no weight download. Geometry (camera pose and depth per frame) comes from it, and so do generated views (Atlas Preview or the API), labeled as generated.
- The 60 GB UniWorld-View weights and the PyTorch3D build are NOT needed. They were for the open-source generator. Stopped on okawau2024. Partial files may remain in that workspace's `montage-data` volume; delete them later.
- Remaining GPU work is small: train the room splat (gsplat, minutes), cut out the shooter (SAM2, small weights), and render the camera path. These need a small image without PyTorch3D.
- Depth links from the 47-frame job are valid for 24 hours from 12:10 PM EDT Oct 24. Download them before then.
