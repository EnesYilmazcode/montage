# Montage

Drone footage without a drone.

A phone walks through a room to scan it. A friend films a jump shot on a second phone. The app places the shot inside the scanned room and flies a virtual camera around it, with play, pause, and replay.

## Status

Hackathon build, started October 24, 2026 (HackOHI/O 2026). Research is done; code is in progress.

## Plan

- Room scan: a 3D Gaussian splat built from a walk-around video.
- Shot: the shooter and ball are shown as 3D motion data placed in the room, so the camera can orbit them.
- Viewer: an installable web app with a scripted camera path and timeline controls.
