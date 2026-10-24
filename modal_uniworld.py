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
def prepare(video: bool = False):
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
    if video:
        print("Downloading STream3R video geometry weights", flush=True)
        snapshot_download("yslan/STream3R", local_dir=str(root / "STream3R"),
                          allow_patterns=["*.json", "*.safetensors"], max_workers=4)
        volume.commit()
    return "Weights and Python imports ready"


@app.function(image=image, gpu="A100-80GB", volumes={"/data": volume}, timeout=3600, cpu=8, memory=131072)
def generate(input_data: bytes | None, filename: str, frames: int, angle: float,
             x: float = 0.0, y: float = 0.0, z: float = 0.0,
             video: bool = False, fps: int = 16):
    import os
    import subprocess
    import sys
    import time

    os.chdir("/opt/uniworld")
    checkpoints = Path("checkpoints")
    if video:
        # Propagate one foreground object from all prompts in one pass.
        demo_path = Path("demo.py")
        demo_path.write_text(demo_path.read_text().replace(
            "for label_i in range(sam_labels.shape[0]):", "for label_i in range(1):"
        ).replace(
            "sam_points[label_i:label_i+1], sam_labels[label_i:label_i+1]",
            "sam_points, sam_labels",
        ))
    # The upstream low-memory loader imports a removed Diffusers helper. Use
    # PyTorch's supported assign=True loading and verify every checkpoint key.
    Path("inference_modal.py").write_text('''
import json
import runpy
import shutil
from pathlib import Path
import torch
from configs.infer_config import get_parser
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

import demo

def setup_stream3r(self):
    self.stream3r = None
    if self.opts.mode == "dynamic_view":
        print("Loading STream3R video geometry model", flush=True)
        self.stream3r = demo.STream3R.from_pretrained(self.opts.stream3r_path).eval()

original_geometry = demo.UniScene._estimate_geometry_stream3r
def estimate_geometry(self, frames_np):
    print(f"Estimating camera poses and depth for {len(frames_np)} frames", flush=True)
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        result = original_geometry(self, frames_np)
    self.stream3r.to("cpu")
    torch.cuda.empty_cache()
    return result

def run_sam2_video(self, video, state, points, labels, bboxes):
    self.sampredictor.add_new_points_or_box(
        state, frame_idx=0, obj_id=1, points=points, labels=labels, box=bboxes)
    masks, paintings = [], []
    for frame, _, logits in self.sampredictor.propagate_in_video(state):
        mask = (torch.sum(logits > 0.0, dim=0)[0] > 0.0).cpu().numpy()
        masks.append(mask)
        paintings.append(demo.mask_painter(video[frame], mask.astype("uint8"), 3, 0.7, 2, 5))
    return masks, paintings

demo.UniScene.setup_stream3r = setup_stream3r
demo.UniScene._estimate_geometry_stream3r = estimate_geometry
demo.UniScene.run_sam2_video = run_sam2_video
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
    original_source = source
    if video:
        source = Path("/tmp/uniworld-resampled.mp4")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(original_source),
            "-vf", f"fps={fps}", "-frames:v", str(frames), "-an", "-c:v", "libx264",
            "-crf", "18", str(source),
        ], check=True)
    name = f"{source.stem}-{int(time.time())}"
    command = [
        sys.executable, "inference_modal.py", "--image_dir", str(source),
        "--out_dir", "/data/outputs", "--exp_name", name,
        "--mode", "dynamic_view" if video else "single_view", "--video_length", str(frames),
        "--height", "480", "--width", "832", "--d_phi", str(angle),
        "--x_offset", str(x), "--y_offset", str(y), "--z_offset", str(z),
        "--render_method", "warp", "--ddim_steps", "8",
        "--diffusion_guidance_scale", "4.0", "--prompt", "",
    ]
    if video:
        command += ["--fps", str(fps), "--low_gpu_memory_mode", "true"]
    output = Path("/data/outputs") / name
    output.mkdir(parents=True, exist_ok=True)
    (output / ("source.mp4" if video else "input.png")).write_bytes(original_source.read_bytes())
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
         output: str = "outputs/uniworld", fps: int = 16):
    if frames < 5 or (frames - 1) % 4:
        raise ValueError("frames must be 4n+1 and at least 5")
    source = Path(input) if input else None
    video = source is not None and source.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    data = source.read_bytes() if source else None
    print(prepare.remote(video))
    artifacts = generate.remote(data, source.name if source else "", frames, angle, x, y, z, video, fps)
    destination = Path(output)
    for name, content in artifacts.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"Saved {path}")
