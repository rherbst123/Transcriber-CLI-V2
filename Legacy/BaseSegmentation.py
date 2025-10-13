import os
import glob
import json
import cv2
import numpy as np
import base64
import threading
from openvino import Core


class Segmentation:

#       0: ac_number
#   1: barcode
#   2: labels
#   3: locator
#   4: scale
#   5: specimen
    # Statically define all classes the model was trained on
    all_possible_classes = ['ruler', 'barcode', 'colorcard', 'label', 'map', 'envelope', 'photo', 'attached_item', 'weights']

    def __init__(
        self,
        model_xml_path: str,
        segmentation_classes: list[str],
        engine: str = "gemini",
        hide_long_objects: bool = False,
        draw_overlay: bool = False,
        output_path: str | None = None,
    ):
        self.engine = engine
        self.hide_long_objects = hide_long_objects
        self.draw_overlay = draw_overlay
        self.output_path = output_path
        self.segmentation_classes = segmentation_classes

        self.core = Core()
        self.model = self.core.read_model(model=model_xml_path)
        self.compiled_model = self.core.compile_model(self.model, device_name="CPU")
        self.input_layer = self.compiled_model.input(0)
        self.output_layer = self.compiled_model.output(0)

        self.inference_lock = threading.Lock()

    # ───────────── Pre- and post-processing helpers ─────────────
    def preprocess_image(self, image):
        resized = cv2.resize(image, (640, 640))
        img = resized.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0).astype(np.float32) / 255.0
        return img

    def get_bounding_boxes(self, image_path):
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise ValueError(f"Image not found at {image_path}")
        original_height, original_width, _ = original_image.shape
        input_tensor = self.preprocess_image(original_image)

        with self.inference_lock:
            outputs = self.compiled_model([input_tensor])[self.output_layer]
        predictions = np.squeeze(outputs).T

        boxes, confidences, class_ids = [], [], []
        x_scale, y_scale = original_width / 640, original_height / 640

        for pred in predictions:
            box_coords, class_probs = pred[:4], pred[4:]
            class_id = np.argmax(class_probs)
            confidence = class_probs[class_id]
            if confidence > 0.25:
                cx, cy, w, h = box_coords
                x1 = int((cx - w / 2) * x_scale)
                y1 = int((cy - h / 2) * y_scale)
                x2 = int((cx + w / 2) * x_scale)
                y2 = int((cy + h / 2) * y_scale)
                boxes.append([x1, y1, x2 - x1, y2 - y1])
                confidences.append(float(confidence))
                class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.25, 0.45)
        final_boxes = {name: [] for name in self.all_possible_classes}
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                box = [x, y, x + w, y + h]
                class_name = self.all_possible_classes[class_ids[i]]
                final_boxes[class_name].append(box)
        return original_image, final_boxes

    def merge_overlapping_boxes(self, boxes):
        if not boxes:
            return []
        box_list = [list(b) for b in boxes]
        while True:
            merged_in_pass = False
            i = 0
            while i < len(box_list):
                j = i + 1
                while j < len(box_list):
                    box1, box2 = box_list[i], box_list[j]
                    if (
                        box1[0] < box2[2] and box1[2] > box2[0]
                        and box1[1] < box2[3] and box1[3] > box2[1]
                    ):
                        box_list[i] = [
                            min(box1[0], box2[0]),
                            min(box1[1], box2[1]),
                            max(box1[2], box2[2]),
                            max(box1[3], box2[3]),
                        ]
                        box_list.pop(j)
                        merged_in_pass = True
                        break
                    else:
                        j += 1
                if merged_in_pass:
                    break
                else:
                    i += 1
            if not merged_in_pass:
                break
        return box_list

    def partition_by_aspect_ratio(self, boxes_by_class, threshold=2.0):
        normal_boxes = {n: [] for n in self.all_possible_classes}
        long_boxes = {n: [] for n in self.all_possible_classes}
        for class_name, boxes in boxes_by_class.items():
            for box in boxes:
                w, h = box[2] - box[0], box[3] - box[1]
                ratio = w / h if h > 0 else float("inf")
                (long_boxes if ratio > threshold else normal_boxes)[class_name].append(
                    box
                )
        return normal_boxes, long_boxes

    # -- helpers for segmentation construction (unchanged) --
    def _create_condensed_segmentation_from_crops(self, crops):
        if not crops:
            return None, {name: [] for name in self.all_possible_classes}
        positions = {name: [] for name in self.all_possible_classes}
        rows = []

        crops.sort(key=lambda c: c["box"][1])  # sort top-to-bottom
        for crop in crops:
            placed = False
            y1, y2 = crop["box"][1], crop["box"][3]
            for row in rows:
                # overlap on y-axis → same row
                if max(row["y_min"], y1) < min(row["y_max"], y2):
                    row["crops"].append(crop)
                    row["y_min"] = min(row["y_min"], y1)
                    row["y_max"] = max(row["y_max"], y2)
                    placed = True
                    break
            if not placed:
                rows.append({"crops": [crop], "y_min": y1, "y_max": y2})

        # compute row dimensions
        row_dims, max_w, total_h = [], 0, 0
        for row in rows:
            row["crops"].sort(key=lambda c: c["box"][0])  # left-to-right
            rh = max(c["img"].shape[0] for c in row["crops"])
            rw = sum(c["img"].shape[1] for c in row["crops"])
            row_dims.append((rw, rh))
            max_w = max(max_w, rw)
            total_h += rh

        # build canvas
        canvas = np.zeros((total_h, max_w, 3), dtype=np.uint8)
        y_off = 0
        for i, row in enumerate(rows):
            x_off = 0
            for c in row["crops"]:
                h, w = c["img"].shape[:2]
                canvas[y_off : y_off + h, x_off : x_off + w] = c["img"]
                positions[c["class"]].append([x_off, y_off, x_off + w, y_off + h])
                x_off += w
            y_off += row_dims[i][1]
        return canvas, positions

    def _append_long_objects(self, base_segmentation, base_positions, long_crops):
        if not long_crops:
            return base_segmentation, base_positions
        long_strip, long_pos_relative = self._create_condensed_segmentation_from_crops(
            long_crops
        )
        base_h, base_w = (base_segmentation.shape[:2] if base_segmentation is not None else (0, 0))
        strip_h, strip_w = long_strip.shape[:2]

        final_w = max(base_w, strip_w)
        final_h = base_h + strip_h
        final_canvas = np.zeros((final_h, final_w, 3), dtype=np.uint8)
        if base_segmentation is not None:
            final_canvas[0:base_h, 0:base_w] = base_segmentation
        final_canvas[base_h:final_h, 0:strip_w] = long_strip

        final_positions = base_positions
        for class_name, bboxes in long_pos_relative.items():
            for box in bboxes:
                final_positions[class_name].append(
                    [box[0], box[1] + base_h, box[2], box[3] + base_h]
                )
        return final_canvas, final_positions

    def resize_for_engine(self, image):
        h, w = image.shape[:2]
        scale = 1.0
        if self.engine == "gemini":
            return image, scale
        elif self.engine == "claude":
            longest = max(h, w)
            if longest > 1568:
                scale = 1568 / longest
                image = cv2.resize(image, (int(w * scale), int(h * scale)))
        elif self.engine == "gpt":
            longest = max(h, w)
            if longest > 2048:
                scale = 2048 / longest
                image = cv2.resize(image, (int(w * scale), int(h * scale)))
                h, w = image.shape[:2]
            shortest = min(h, w)
            if shortest > 768:
                step2 = 768 / shortest
                scale *= step2
                image = cv2.resize(image, (int(w * step2), int(h * step2)))
        return image, scale

    # ───────────── Main entry point ─────────────
    def run(self, image_path: str, output_path_override: str | None = None):
        """Return JSON dict; save segmentation if an output path is supplied.

        You can pass `output_path_override` to change the destination on a
        per-image basis without re-instantiating the engine.
        """
        original_image, raw_boxes = self.get_bounding_boxes(image_path)
        merged_boxes = {
            c: self.merge_overlapping_boxes(b) for c, b in raw_boxes.items() if b
        }

        if self.hide_long_objects:
            normal_boxes, long_boxes = self.partition_by_aspect_ratio(merged_boxes)
        else:
            normal_boxes = merged_boxes
            long_boxes = {n: [] for n in self.all_possible_classes}

        final_output = {
            "position_original": merged_boxes,
            "position_segmentation": {},
            "base64image_text_segmentation": None,
        }

        # Build crops
        crops_for_segmentation = []
        
        for class_name in self.segmentation_classes:
            for box in normal_boxes.get(class_name, []):
                x1, y1, x2, y2 = map(int, box)
                crop_img = original_image[y1:y2, x1:x2]
                
                # Validate crop before processing
                if crop_img.size == 0:
                    continue
                
                crops_for_segmentation.append(
                    {
                        "img": crop_img,
                        "box": box,
                        "class": class_name,
                    }
                )
            if self.hide_long_objects:
                for box in long_boxes.get(class_name, []):
                    x1, y1, x2, y2 = map(int, box)
                    crop_img = original_image[y1:y2, x1:x2]
                    
                    # Validate crop before processing
                    if crop_img.size == 0:
                        continue
                    
                    crops_for_segmentation.append(
                        {
                            "img": crop_img,
                            "box": box,
                            "class": class_name,
                        }
                    )

        segmentation, positions = self._create_condensed_segmentation_from_crops(
            crops_for_segmentation
        )
        if segmentation is None:
            raise RuntimeError("No segmentation could be created.")

        segmentation, scale = self.resize_for_engine(segmentation)
        final_output["position_segmentation"] = {
            c: [[int(coord * scale) for coord in box] for box in bboxes]
            for c, bboxes in positions.items()
        }

        if self.draw_overlay:
            segmentation = self.draw_overlay_on_segmentation(segmentation, final_output["position_segmentation"])

        # Encode to JPG bytes
        success, jpg_array = cv2.imencode(".jpg", segmentation)
        if not success:
            raise RuntimeError("Failed to encode segmentation image to JPG.")
        jpg_bytes = jpg_array.tobytes()

        # Decide where to send bytes
        dest_path = output_path_override or self.output_path
        if dest_path:
            with open(dest_path, "wb") as f:
                f.write(jpg_bytes)
        else:
            final_output["base64image_text_segmentation"] = base64.b64encode(jpg_bytes).decode(
                "utf-8"
            )
        return final_output

    # ─────────────- Optional overlay (unchanged) -─────────────
    def draw_overlay_on_segmentation(self, image, positions):
        overlay = image.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        for class_name, bboxes in positions.items():
            for box in bboxes:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{class_name}: {x1},{y1},{x2},{y2}"
                (w, h), _ = cv2.getTextSize(label, font, 0.5, 1)
                cv2.rectangle(overlay, (x1, y1 - h - 4), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(overlay, label, (x1, y1 - 2), font, 0.5, (0, 0, 0), 1)
        return overlay



def process_images_segmentation(input_folder, output_folder, model_xml_path=None, classes_to_render=None):
    """
    Process images through segmentation pipeline
    
    Args:
        input_folder (str): Path to input images folder
        output_folder (str): Path to output folder for segmented segmentations
        model_xml_path (str): Path to OpenVINO model XML file
        classes_to_render (list): List of classes to render in segmentation
    
    Returns:
        tuple: (success_count, total_count)
    """
    # Default settings
    if model_xml_path is None:
        model_xml_path = r"helpers/SegmentationModels/RoboFlowModels/best.xml"
    
    if classes_to_render is None:
        classes_to_render = ["label", "barcode", "map"]
    
    # Validate model path
    if not os.path.exists(model_xml_path):
        raise FileNotFoundError(f"Model XML file not found at: {model_xml_path}")
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"\n=== Starting Image Segmentation ===")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Classes to render: {classes_to_render}")
    
    # Instantiate the engine once
    try:
        engine = Segmentation(
            model_xml_path=model_xml_path,
            segmentation_classes=classes_to_render,
            engine="gemini",
            output_path=None  # we will override per-image below
        )
    except Exception as e:
        print(f"Error initializing segmentation {e}")
        return 0, 0
    
    # Process every supported image in the folder
    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
    img_paths = [
        p for p in glob.glob(os.path.join(input_folder, "*"))
        if p.lower().endswith(IMAGE_EXTS)
    ]
    
    if not img_paths:
        print(f"No images with extensions {IMAGE_EXTS} found in {input_folder}")
        return 0, 0
    
    print(f"\nFound {len(img_paths)} images to process")
    
    success_count = 0
    for i, img_path in enumerate(sorted(img_paths), 1):
        basename = os.path.splitext(os.path.basename(img_path))[0]
        segmentation_path = os.path.join(output_folder, f"{basename}_segmentation.jpg")
        
        try:
            print(f"Processing {i}/{len(img_paths)}: {os.path.basename(img_path)}")
            result_json = engine.run(img_path, output_path_override=segmentation_path)
            
            print(f"✓ Processed {os.path.basename(img_path)} → {os.path.basename(segmentation_path)}")
            success_count += 1
        except Exception as exc:
            print(f"✗ Failed on {img_path}: {exc}")
    
    print(f"\n=== Segmentation Complete ===")
    print(f"Successfully processed: {success_count}/{len(img_paths)} images")
    
    return success_count, len(img_paths)


def get_segmentation_settings():
    """Get segmentation settings from user"""
    print("\n=== Segmentation Configuration ===")
    
    # Use fixed model path
    model_path = os.path.expanduser("~/Documents/GitHub/Transcriber-CLI-V2/Transcriber-CLI-V2/helpers/SegmentationModels/RoboFlowModels/best.xml")
    print(f"Using model: {model_path}")
    
    # Classes to render
    default_classes = ["label","map"]
    print(f"\nDefault classes to render: {default_classes}")
    print("Available classes: ruler, barcode, colorcard, label, map, envelope, photo, attached_item, weights")
    
    custom_classes = input("Enter custom classes (comma-separated, or press Enter for default): ").strip()
    if custom_classes:
        classes_to_render = [c.strip() for c in custom_classes.split(',')]
    else:
        classes_to_render = default_classes
    
    return model_path, classes_to_render


if __name__ == "__main__":
    # This script is now integrated into the main pipeline
    # For standalone testing, you can modify these paths as needed
    print("")

    
    # Example paths - modify as needed for testing
    # MODEL_XML_PATH = r"/path/to/your/model.xml"
    # INPUT_FOLDER = r"/path/to/input/images"
    # OUTPUT_FOLDER = r"/path/to/output/folder"
    # CLASSES_TO_RENDER = ["label", "barcode", "map"]
    
    # Uncomment and modify the following lines for standalone testing:
    # try:
    #     success_count, total_count = process_images_segmentation(
    #         INPUT_FOLDER, 
    #         OUTPUT_FOLDER, 
    #         MODEL_XML_PATH, 
    #         CLASSES_TO_RENDER
    #     )
    #     print(f"\nProcessing completed: {success_count}/{total_count} images processed successfully")
    # except Exception as e:
    #     print(f"Error: {e}")
