"""Modal environment for UniWorld-View (PKU-YuanGroup, Apache-2.0).

Build the image, then download the weights into the montage-data volume:
    modal run pipeline/uniworld_app.py::fetch_weights
Then start the Gradio demo on an A100 80GB:
    modal serve pipeline/uniworld_app.py
"""

import os
import shutil
import subprocess

import modal

REPO = "/root/UniWorld-View"
VOL_CKPT = "/vol/ckpt"

vol = modal.Volume.from_name("montage-data", create_if_missing=True)

image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.10")
    .apt_install("git", "build-essential", "clang", "ninja-build", "ffmpeg", "libgl1", "libglib2.0-0", "libeigen3-dev")
    .env({"TORCH_CUDA_ARCH_LIST": "8.0;9.0", "FORCE_CUDA": "1"})
    .pip_install("torch==2.4.0", "torchvision==0.19.0", index_url="https://download.pytorch.org/whl/cu124")
    .run_commands(
        f"git clone https://github.com/PKU-YuanGroup/UniWorld-View.git {REPO}",
        f"git clone https://github.com/NIRVANALAN/STream3R.git {REPO}/extern/STream3R",
    )
    .workdir(REPO)
    .run_commands("pip install -r requirements.txt", "pip install carvekit --no-deps")
    .run_commands("bash extern/install_pytorch3d.sh")
)

app = modal.App("montage-uniworld", image=image)


@app.function(volumes={"/vol": vol}, timeout=4 * 60 * 60)
def fetch_weights():
    """Download checkpoints into the volume so they survive between runs."""
    src = f"{REPO}/checkpoints"
    os.makedirs(VOL_CKPT, exist_ok=True)
    # Keep the repo's download scripts, then point checkpoints/ at the volume.
    for name in os.listdir(src):
        path = os.path.join(src, name)
        if os.path.isfile(path):
            shutil.copy(path, VOL_CKPT)
    shutil.rmtree(src)
    os.symlink(VOL_CKPT, src)
    subprocess.run(["bash", "checkpoints/download_hf.sh", "--stream3r"], cwd=REPO, check=True)
    vol.commit()
    return sorted(os.listdir(VOL_CKPT))


@app.function(gpu="A100-80GB", volumes={"/vol": vol}, timeout=60 * 60)
@modal.web_server(7860, startup_timeout=900)
def demo():
    """Gradio demo: upload a clip and a camera path, get novel views back."""
    src = f"{REPO}/checkpoints"
    if os.path.islink(src):
        os.unlink(src)
    elif os.path.isdir(src):
        shutil.rmtree(src)
    os.symlink(VOL_CKPT, src)
    env = dict(os.environ, GRADIO_SERVER_NAME="0.0.0.0", GRADIO_SERVER_PORT="7860")
    subprocess.Popen(["bash", "run_app.sh"], cwd=REPO, env=env)


@app.function(gpu="A100-80GB", volumes={"/vol": vol}, timeout=2 * 60 * 60)
def run_test(clip: str = "inputs/test_clip.mp4", d_phi: int = 50):
    """Run UniWorld-View on one uploaded clip with an orbit of d_phi degrees.

    Uses the same flags as run_infer.sh, with the input and output on the volume.
    Output lands in /vol/outputs/<clip-name>-dphi<d_phi>/.
    """
    src = f"{REPO}/checkpoints"
    if os.path.islink(src):
        os.unlink(src)
    elif os.path.isdir(src):
        shutil.rmtree(src)
    os.symlink(VOL_CKPT, src)

    name = os.path.splitext(os.path.basename(clip))[0]
    out = f"/vol/outputs/{name}-dphi{d_phi}"
    os.makedirs(out, exist_ok=True)
    cmd = [
        "python", "inference.py",
        "--image_dir", f"/vol/{clip}",
        "--out_dir", out,
        "--mode", "dynamic_view",
        "--stride", "1",
        "--video_length", "81",
        "--device", "cuda:0",
        "--height", "480",
        "--width", "832",
        "--radius_scale", "1.0",
        "--traj_type", "custom",
        "--d_phi", str(d_phi),
        "--d_theta", "0",
        "--x_offset", "0",
        "--y_offset", "0",
        "--z_offset", "0",
        "--blip_path", "./checkpoints/blip2-opt-2.7b",
        "--transformer_path", "./checkpoints/UniView",
        "--model_name", "./checkpoints/Wan2.1-VACE-14B-diffusers",
        "--lora_path", "./checkpoints/loras/Wan21_CausVid_14B_T2V_lora_rank32_v2.safetensors",
        "--stream3r_path", "./checkpoints/STream3R",
        "--ddim_steps", "8",
        "--diffusion_guidance_scale", "4.0",
        "--prompt", "",
        "--geometry_backend", "stream3r",
    ]
    subprocess.run(cmd, cwd=REPO, check=True)
    vol.commit()
    return sorted(os.listdir(out))


@app.local_entrypoint()
def test(clip: str = "inputs/test_clip.mp4", d_phi: int = 50):
    print(run_test.remote(clip, d_phi))
