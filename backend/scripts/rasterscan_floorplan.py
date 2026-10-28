"""
Run a floor plan image through the RasterScan Automated Floor Plan Digitalization
HuggingFace Space (https://huggingface.co/spaces/RasterScan/Automated-Floor-Plan-Digitalization).

Returns room polygons, walls, doors, area, and perimeter data.
"""

import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

FLOORPLAN_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'leo-copilot',
    'assets', 'images', 'rooms', 'floorplan-real.png'
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(FLOORPLAN_PATH):
        logger.error(f"Floor plan not found: {FLOORPLAN_PATH}")
        sys.exit(1)

    logger.info(f"Floor plan: {FLOORPLAN_PATH} ({os.path.getsize(FLOORPLAN_PATH)} bytes)")

    from gradio_client import Client, handle_file

    logger.info("Connecting to RasterScan HuggingFace Space...")
    client = Client("RasterScan/Automated-Floor-Plan-Digitalization")

    logger.info("Submitting floor plan for analysis...")
    result = client.predict(
        handle_file(FLOORPLAN_PATH),
        fn_index=0,
    )

    # result is a tuple: (output_image_path, json_data)
    output_image_path, json_data = result
    logger.info(f"Output image: {output_image_path}")
    logger.info(f"JSON data type: {type(json_data)}")

    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    # Save JSON output
    json_path = os.path.join(OUTPUT_DIR, 'floorplan_rasterscan.json')
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    logger.info(f"Saved JSON → {json_path}")

    # Copy output image
    import shutil
    img_out_path = os.path.join(OUTPUT_DIR, 'floorplan_rasterscan_output.png')
    shutil.copy2(output_image_path, img_out_path)
    logger.info(f"Saved output image → {img_out_path}")

    # Summary
    rooms = json_data.get('rooms', [])
    walls = json_data.get('walls', [])
    doors = json_data.get('doors', [])
    area = json_data.get('area', '?')
    perimeter = json_data.get('perimeter', '?')

    logger.info(f"RESULTS: {len(rooms)} rooms | {len(walls)} walls | {len(doors)} doors | area={area} | perimeter={perimeter}")
    for i, room in enumerate(rooms):
        room_type = room.get('type', room.get('label', '?'))
        room_area = room.get('area', '?')
        logger.info(f"  Room {i}: {room_type} ({room_area})")


if __name__ == "__main__":
    main()
