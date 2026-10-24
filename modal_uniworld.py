"""Run UniWorld-View on Modal: modal run modal_uniworld.py.

Weights and outputs persist in the uniworld-view-data Modal Volume.
"""
from pathlib import Path
import modal

app = modal.App("montage-uniworld-view")
volume = modal.Volume.from_name("uniworld-view-data", create_if_missing=True)
REVISION = "660212c48bff7c91a2ea5c7d5f3785af581100e2"
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.4.0", "torchvision==0.19.0", index_url="https://download.pytorch.org/whl/cu124")
    .run_commands(
        "git clone https://github.com/PKU-YuanGroup/UniWorld-View.git /opt/uniworld",
        f"git -C /opt/uniworld checkout {REVISION}",
        "git clone --depth 1 https://github.com/NIRVANALAN/STream3R.git /opt/uniworld/extern/STream3R",
    )
    .pip_install(
        "diffusers==0.35.0", "transformers==4.48.3", "accelerate==1.10.1",
        "huggingface-hub==0.34.4", "tokenizers==0.21.0", "timm==1.0.14",
        "hydra-core==1.3.2", "omegaconf==2.3.0", "fvcore==0.1.5.post20221221",
        "einops==0.8.1", "numpy==1.26.4", "scipy==1.15.1", "Pillow==10.4.0",
        "opencv-python==4.11.0.86", "imageio==2.37.0", "imageio-ffmpeg==0.6.0",
        "trimesh==4.6.2", "kornia==0.8.2", "decord", "scikit-image", "av==12.0.0",
        "ftfy", "peft==0.14.0", "loguru==0.7.2", "iopath==0.1.10", "portalocker==2.8.2",
        "matplotlib", "transforms3d", "easydict", "roma", "sentencepiece",
        "protobuf", "gdown", "efficientnet-pytorch", "lightning", "huggingface-hub[hf_xet]==0.34.4",
        "git+https://github.com/EasternJournalist/utils3d.git",
    )
    .pip_install("carvekit", extra_options="--no-deps")
    .pip_install("peft==0.17.1")
    .pip_install("git+https://github.com/EasternJournalist/utils3d.git@d790d337638ce478972da01e42d7ee255796f7b4", extra_options="--no-deps")
    .pip_install("plyfile==1.0.3", "numpy==1.26.4")
    .pip_install("safetensors==0.5.3")
    .env({"HF_HOME": "/data/huggingface", "PYTHONUNBUFFERED": "1"})
)


@app.function(image=image, volumes={"/data": volume}, timeout=7200, cpu=8, memory=32768)
def prepare():
    """Download on CPU so weight transfer does not consume GPU time."""
    import os
    import sys
    from huggingface_hub import snapshot_download, hf_hub_download

    os.chdir("/opt/uniworld")
    sys.path.insert(0, os.getcwd())
    import demo  # Validate imports before allocating a GPU.
    import utils3d
    assert callable(utils3d.torch.depth_to_points)
    assert callable(utils3d.torch.image_uv)

    root = Path("/data/checkpoints")
    root.mkdir(parents=True, exist_ok=True)
    for repo, subdir, patterns in [
        ("Drexubery/UniView", "UniView", None),
        ("Wan-AI/Wan2.1-VACE-14B-diffusers", "Wan2.1-VACE-14B-diffusers",
         ["vae/*", "tokenizer/*", "text_encoder/*", "scheduler/*", "model_index.json"]),
        ("Salesforce/blip2-opt-2.7b", "blip2-opt-2.7b",
         ["*.json", "*.safetensors", "*.txt", "*.model"]),
    ]:
        print(f"Downloading {repo}", flush=True)
        snapshot_download(repo, local_dir=str(root / subdir), allow_patterns=patterns, max_workers=4)
        volume.commit()
    for repo, name, subdir in [
        ("Ruicheng/moge-2-vitl-normal", "model.pt", "moge"),
        ("facebook/sam2-hiera-large", "sam2_hiera_large.pt", "sam2"),
        ("Carve/tracer_b7", "tracer_b7.pth", ""),
        ("Kijai/WanVideo_comfy", "Wan21_CausVid_14B_T2V_lora_rank32_v2.safetensors", "loras"),
    ]:
        hf_hub_download(repo, name, local_dir=str(root / subdir))
        volume.commit()
    return "Weights and Python imports ready"


@app.function(image=image, gpu="A100-80GB", volumes={"/data": volume}, timeout=3600, cpu=8, memory=131072)
def generate(input_data: bytes | None, filename: str, frames: int, angle: float,
             x: float = 0.0, y: float = 0.0, z: float = 0.0):
    import os
    import subprocess
    import sys
    import time

    os.chdir("/opt/uniworld")
    checkpoints = Path("checkpoints")
    # The upstream low-memory loader imports a removed Diffusers helper. Use
    # PyTorch's supported assign=True loading and verify every checkpoint key.
    Path("inference_modal.py").write_text('''
import json
import runpy
import shutil
from pathlib import Path
import torch
from accelerate import init_empty_weights
from safetensors.torch import load_file
from model.uniview_transformer import WanVACETransformer3DModel

@classmethod
def load_transformer(cls, pretrained_model_path, subfolder=None,
                     transformer_additional_kwargs=None, torch_dtype=torch.bfloat16, **kwargs):
    source = Path(pretrained_model_path)
    if subfolder:
        source = source / subfolder
    config = json.loads((source / "config.json").read_text())
    with init_empty_weights():
        model = cls.from_config(config, **(transformer_additional_kwargs or {}))
    remaining = set(model.state_dict())
    for checkpoint in sorted(source.glob("*.safetensors")):
        # Sequentially copy to local SSD before memory-mapping tensor storage.
        local = Path("/tmp") / checkpoint.name
        print(f"Staging transformer shard {checkpoint.name}", flush=True)
        shutil.copyfile(checkpoint, local)
        state = load_file(str(local))
        state = {k: v.to(dtype=torch_dtype) if v.is_floating_point() else v for k, v in state.items()}
        _, unexpected = model.load_state_dict(state, strict=False, assign=True)
        if unexpected:
            raise RuntimeError(f"Unexpected checkpoint keys: {unexpected}")
        remaining.difference_update(state)
        print(f"Loaded shard; {len(remaining)} keys remaining", flush=True)
        del state
    if remaining:
        raise RuntimeError(f"Missing checkpoint keys: {sorted(remaining)}")
    return model

WanVACETransformer3DModel.from_pretrained = load_transformer
runpy.run_path("inference.py", run_name="__main__")
''')
    # Keep the upstream download helpers; symlink each weight bundle separately.
    for item in Path("/data/checkpoints").iterdir():
        target = checkpoints / item.name
        if not target.exists():
            target.symlink_to(item, target_is_directory=item.is_dir())
    if input_data is None:
        source = Path("test/images/seva_room1.png")
    else:
        source = Path("/tmp") / Path(filename).name
        source.write_bytes(input_data)
    name = f"{source.stem}-{int(time.time())}"
    command = [
        sys.executable, "inference_modal.py", "--image_dir", str(source),
        "--out_dir", "/data/outputs", "--exp_name", name,
        "--mode", "single_view", "--video_length", str(frames),
        "--height", "480", "--width", "832", "--d_phi", str(angle),
        "--x_offset", str(x), "--y_offset", str(y), "--z_offset", str(z),
        "--render_method", "warp", "--ddim_steps", "8",
        "--diffusion_guidance_scale", "4.0", "--prompt", "",
    ]
    output = Path("/data/outputs") / name
    output.mkdir(parents=True, exist_ok=True)
    (output / "input.png").write_bytes(source.read_bytes())
    try:
        with (output / "run.log").open("w") as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            if process.wait():
                raise RuntimeError(f"Inference failed; see {output}/run.log")
        return {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*")
                if p.is_file() and p.suffix in {".mp4", ".png", ".json", ".log"}}
    finally:
        volume.commit()


@app.local_entrypoint()
def main(input: str = "", frames: int = 49, angle: float = 35.0,
         x: float = 0.0, y: float = 0.0, z: float = 0.0,
         output: str = "outputs/uniworld"):
    if frames < 5 or (frames - 1) % 4:
        raise ValueError("frames must be 4n+1 and at least 5")
    source = Path(input) if input else None
    data = source.read_bytes() if source else None
    print(prepare.remote())
    artifacts = generate.remote(data, source.name if source else "", frames, angle, x, y, z)
    destination = Path(output)
    for name, content in artifacts.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"Saved {path}")
