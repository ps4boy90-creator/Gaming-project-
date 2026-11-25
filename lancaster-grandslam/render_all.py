#!/usr/bin/env python3
"""Bake the explosion and render every shot of the Lancaster / Grand Slam segment, then build the video.

    python render_all.py <frames_root> <sim_root> [out.mp4] [--only shot,shot,...] [--res 1280x720] [--spp N] [--bake out:224:250]

The models, the depot, the simulation and the shots are those of the Tallboy segment (../lancaster-tallboy), which
draws the larger bomb, the Lancaster B.I (Special) and the larger burst when LANC_BOMB=grandslam is set; this script
sets it and runs that segment's driver with this segment's captions (spost.py).  Options and requirements are the same.
"""
import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["LANC_BOMB"] = "grandslam"
spec = importlib.util.spec_from_file_location("tallboy_render_all", os.path.join(HERE, "..", "lancaster-tallboy", "render_all.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
base.POST = os.path.join(HERE, "spost.py"); base.OUT_NAME = "lancaster_grandslam.mp4"

if __name__ == "__main__":
    base.main()
