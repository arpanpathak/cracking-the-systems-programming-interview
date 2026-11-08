#!/usr/bin/env python3
"""Paint the pictures behind the cover and the chapter-opener plates.

Each picture comes from DreamShaper 8, a Stable Diffusion 1.5 model, with the
LCM-LoRA adapter so that 8 denoising steps are enough. A picture took about 10
seconds on a Jetson Orin NX. The chosen picture for each plate is committed in
tools/paintings/, and tools/art.py lays the chapter's ribbon over it.

    pip install diffusers==0.35.2 transformers==4.57.1 peft==0.17.1
    python3 tools/paint.py ch03          # writes candidates to tools/paintings/candidates/
    python3 tools/paint.py               # every plate

The models are read from the Hugging Face cache: Lykon/dreamshaper-8 and
latent-consistency/lcm-lora-sdv1-5. PICKS records the seed chosen for each plate.
"""

import sys
from pathlib import Path

import torch
from diffusers import LCMScheduler, StableDiffusionPipeline

OUT = Path(__file__).resolve().parent / "paintings" / "candidates"
STYLE = ", cinematic photograph, dramatic lighting, highly detailed, realistic fur and feathers, depth of field, 35mm"
NEGATIVE = ("text, letters, words, watermark, logo, signature, blurry, deformed, extra limbs, extra heads, cartoon, "
            "childish, low quality, frame, border")

COVER = ("epic movie poster of a heroic raccoon wearing a dark blue cape standing at the helm of a container ship at "
         "night, stacked shipping containers glowing with green light, harbour lights, storm clouds, moonlight")
PLATES = {
    "intro": "a large white stork standing on a wooden dock in the foreground holding a cloth bundle in its long orange "
             "beak, a container ship with stacked shipping containers and cargo cranes behind it at dusk",
    "ch01": "a wise great horned owl wearing round spectacles sitting at an old wooden desk in a dim library at night, "
            "copying lines from a huge leather ledger into a small notebook, warm lamp light, glowing green server racks "
            "in the background",
    "ch01-1": "a beaver wearing a yellow hard hat in a workshop, placing a glowing green computer chip into an open steel "
              "shipping container, workbench with tools, warm light",
    "ch02": "macro photograph of honeybees working on a golden honeycomb, the comb cells glow green like a computer chip, "
            "circuit traces under the comb",
    "ch03": "a basset hound wearing a white doctor's coat and a stethoscope listening to a server rack in a data center, "
            "a heart rate monitor glowing on a screen, blue and green status lights",
    "ch04": "a raccoon wearing a police officer cap and reflective vest directing traffic at night on a wet street, orange "
            "traffic cones around a server rack with a red warning light, traffic light glowing",
    "ch05": "a red fox security guard in a uniform cap standing at a gate checkpoint at night, holding an identity badge, "
            "a modern data center building behind a barrier gate, floodlights",
    "ch06": "macro photograph of a hermit crab climbing out of an old shell into a larger new shell on a sandy beach at "
            "sunset, golden light",
    "ch07": "five colourful macaw parrots perched in a circle on a round wooden ring perch in a rainforest, passing a seed "
            "from beak to beak",
    "ch08": "a border collie sheepdog crouching in the foreground, herding a flock of five sheep through an open wooden "
            "gate into a pen, green grass hillside, warm golden sunset colours",
    "ch09": "three red squirrels sitting on a mossy tree branch in an autumn forest, each holding acorns, piles of acorns",
    "ch10": "a magpie perched on an antique wooden apothecary cabinet with many small labelled drawers, shiny coins and "
            "trinkets, dim warm room",
    "ch11": "a chameleon on a branch above three glowing laptop screens in a dark room, its skin shifting from green to "
            "blue to orange",
    "appendix": "a hedgehog on a workbench beside a small single-board computer with a glowing green chip, cables, macro "
                "photograph, soft light",
}
PICKS = {"cover": 12, "intro": 3, "ch01": 1, "ch01-1": 2, "ch02": 1, "ch03": 2, "ch04": 2, "ch05": 2, "ch06": 1,
         "ch07": 1, "ch08": 7, "ch09": 2, "ch10": 2, "ch11": 2, "appendix": 2}


def pipeline():
    pipe = StableDiffusionPipeline.from_pretrained("Lykon/dreamshaper-8", torch_dtype=torch.float16,
                                                   safety_checker=None, local_files_only=True).to("cuda")
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5", weight_name="pytorch_lora_weights.safetensors",
                           local_files_only=True)
    pipe.fuse_lora()
    pipe.enable_attention_slicing()
    pipe.set_progress_bar_config(disable=True)

    return pipe


def paint(pipe, name, seeds):
    prompt, (width, height) = (COVER, (576, 768)) if name == "cover" else (PLATES[name], (896, 384))

    for seed in seeds:
        generator = torch.Generator("cuda").manual_seed(seed)
        image = pipe(prompt + STYLE, negative_prompt=NEGATIVE, num_inference_steps=8, guidance_scale=1.5,
                     width=width, height=height, generator=generator).images[0]
        image.save(OUT / f"{name}-{seed}.png")
        print(f"  {name}-{seed}")


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    pipe = pipeline()

    for name in names or ["cover", *PLATES]:
        paint(pipe, name, [PICKS[name], PICKS[name] + 100])


if __name__ == "__main__":
    main(sys.argv[1:])
