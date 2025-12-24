from __future__ import annotations
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union, IO, Dict, Tuple, Optional
import logging

# Basic configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # You can add FileHandler, SMTPHandler, etc.
    ]
)

logger = logging.getLogger(__name__)


JsonFile = Union[str, Path, IO[str]]


def format_column_header(header: str) -> str:
    """
    Format column headers by adding line breaks between words.
    e.g., 'BleachingEnergy' -> 'Bleaching\nEnergy'
    """
    import re
    # Insert line break before each capital letter that follows a lowercase letter
    # or before a capital letter that follows another capital letter and is followed by a lowercase letter
    formatted = re.sub(r'([a-z])([A-Z])|([A-Z])([A-Z][a-z])', r'\1\3\n\2\4', header)
    return formatted


def format_dict_headers(data_dict: dict) -> dict:
    """
    Format all keys in a dictionary by adding line breaks between words.
    """
    return {format_column_header(key): value for key, value in data_dict.items()}


def add_blank_lines_between_run_cycles(block_rows: list[dict]) -> list[dict]:
    """
    Add blank lines between different run cycles in the block rows.
    """
    if not block_rows:
        return block_rows
    
    result = []
    prev_run_cycle = None
    
    for row in block_rows:
        current_run_cycle = row.get(format_column_header("RunCycleNumber"), "")
        
        # If this is a new run cycle (and not the first row), add a blank line
        if (prev_run_cycle is not None and 
            current_run_cycle != "" and 
            current_run_cycle != prev_run_cycle and
            prev_run_cycle != ""):
            
            # Create a blank row with the same keys but empty values
            blank_row = {key: "" for key in row.keys()}
            result.append(blank_row)
        
        result.append(row)
        
        # Update previous run cycle number if this row has one
        if current_run_cycle != "":
            prev_run_cycle = current_run_cycle
    
    return result


def get_input_path() -> Path:
    parser = argparse.ArgumentParser(description="MACSima JSON parser")
    parser.add_argument("json_path", nargs="?", type=Path, help="Path to input JSON file")
    args = parser.parse_args()

    if args.json_path and args.json_path.exists():
        return args.json_path

    # fallback: prompt the user
    path_str = input("Enter path to input JSON file: ").strip()
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    return path

def load_json(json_file: JsonFile) -> Any:
    """
    Load data from a JSON file.

    Parameters
    ----------
    json_file : str | pathlib.Path | IO[str]
        Path to a *.json* file (or an already‑opened text file handle).

    Returns
    -------
    Any
        Whatever `json.load` produces—usually `dict[str, Any]` or
        `list[Any]`, depending on the file’s contents.
    """
    # If a path‑like object was supplied, open it; otherwise assume it's a file‑like object
    if isinstance(json_file, (str, Path)):
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:                                   # file handle already open
        return json.load(json_file)
    

# --------------------------------------------------
# Experiment info helper functions
# --------------------------------------------------

def get_experiment_name(experiment: dict[str, Any]) -> str:
    """Returns the experiment name."""
    # NOTE: assume only one experiment in the file
    return experiment.get("name", "Unknown experiment")


def get_procedure_name(procedure: dict[str, Any]) -> str:
    """Returns the procedure name."""
    return procedure.get("comment", "Unknown procedure")


def sanitise_sheet_name(name: str, max_length: int = 31) -> str:
    """
    Sanitise a string for use as an Excel sheet name.

    Excel sheet names have these restrictions:
    - Maximum 31 characters
    - Cannot contain: \\ / ? * [ ] :
    - Cannot be blank

    Parameters
    ----------
    name : str
        The raw name to sanitise.
    max_length : int
        Maximum length for the sheet name (default 31).

    Returns
    -------
    str
        A valid Excel sheet name.
    """
    if not name or not name.strip():
        return "Procedure"

    # Remove invalid characters
    invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
    sanitised = name
    for char in invalid_chars:
        sanitised = sanitised.replace(char, '_')

    # Trim to max length
    if len(sanitised) > max_length:
        sanitised = sanitised[:max_length]

    return sanitised.strip() or "Procedure"

def get_rack_name(rack: list[dict[str, Any]]) -> str:
    """Returns the rack name."""
    return rack.get("name", "Unknown rack")

def get_start_time(experiment: dict) -> str:
    """Return the experiment's start time as an RFC 3339 string with 'Z'."""
    # assuming the raw string is already in ISO‑8601 / RFC 3339 form
    raw: str = experiment.get("executionStartDateTime", "Unknown end time")

    # Parse it so you know it’s valid
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))

    # Force UTC and format with a literal 'Z'
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_end_time(experiment: dict[str]) -> str:
    """Returns the experiment end time."""
    raw: str = experiment.get("executionEndDateTime", "Unknown end time")

    # Parse it so you know it’s valid
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))

    # Force UTC and format with a literal 'Z'
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def convert_seconds_to_hms(seconds)-> Tuple[int, int, int]:
    """Convert total seconds to (hours, minutes, seconds)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec_left = seconds % 60
    return hours, minutes, sec_left

def get_running_time(experiment: dict[str, Any]) -> str:
    """
    Returns the experiment's actual running time from the actualRunningTime field.

    This is the machine-reported runtime which may exclude pauses.
    Returns a warning string if the field is missing or zero.
    """
    actual_running_time_s = experiment.get('actualRunningTime')
    if actual_running_time_s is None:
        logger.warning("actualRunningTime field is missing from experiment data")
        return "N/A (missing)"
    if actual_running_time_s == 0:
        logger.warning("actualRunningTime is zero - this may indicate missing data")
        return "0h 0m 0s (check data)"
    h, m, s = convert_seconds_to_hms(actual_running_time_s)
    runtime_str = f"{h}h {m}m {s}s"
    return runtime_str


def get_elapsed_time(experiment: dict[str, Any]) -> str:
    """
    Calculate elapsed wall-clock time from executionStartDateTime to executionEndDateTime.

    This is the total time from start to end, including any pauses.
    Returns a warning string if either datetime field is missing or invalid.
    """
    start_raw = experiment.get('executionStartDateTime')
    end_raw = experiment.get('executionEndDateTime')

    if not start_raw:
        logger.warning("executionStartDateTime field is missing from experiment data")
        return "N/A (missing start)"
    if not end_raw:
        logger.warning("executionEndDateTime field is missing from experiment data")
        return "N/A (missing end)"

    try:
        start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))

        elapsed_seconds = int((end_dt - start_dt).total_seconds())
        if elapsed_seconds < 0:
            logger.warning("Negative elapsed time calculated - end time is before start time")
            return "N/A (invalid times)"

        h, m, s = convert_seconds_to_hms(elapsed_seconds)
        return f"{h}h {m}m {s}s"
    except (ValueError, AttributeError) as e:
        logger.warning(f"Error parsing datetime fields: {e}")
        return "N/A (parse error)"


def get_used_disk_space(experiment: dict) -> str:
    """
    Return the experiment's used‑disk‑space value as a string like '178.364 KB'.

    The JSON stores the size in bytes, so we convert to kilobytes (KiB = 1024 bytes)
    and round to three decimal places.
    """
    # raw number of **bytes**
    raw_bytes: int | float = experiment.get("usedDiskspace")

    kib: float = raw_bytes / 1000                       # → KiB
    kib_rounded: float = round(kib, 3)                  # keep 3 decimal places
    return f"{kib_rounded:.3f} KB"

# TODO: add a function to get the used disk space in GB

# --------------------------------------------------
# ROI helper functions
# --------------------------------------------------

def get_roi_name(roi: dict[str, Any]) -> str:
    """Returns the ROI name."""
    return roi.get("name", "Unknown ROI")

def get_roi_shape_type(roi: dict[str, Any]) -> str:
    """return the ROI shape type."""
    shape = roi.get("shape", "Unknown shape")
    shape_type = shape.get("Type", "Unknown shape type")
    # remove prefix "ShapeType_"
    shape_type = shape_type.replace("ShapeType_", "")
    return shape_type

def get_roi_shape_height(roi):
    """Returns the ROI shape height."""
    try:
        shape_data_str = roi.get('shape', {}).get('Data', '{}')
        shape_data = json.loads(shape_data_str)
        
        # Handle different shape data formats
        if isinstance(shape_data, dict):
            # Rectangle ROI - has Height and Width keys
            height = shape_data.get('Height')
            if height is None:
                height = "N/A"
        elif isinstance(shape_data, list):
            # Polygon ROI - list of points, calculate bounding box height
            if not shape_data:
                height = "N/A"
            else:
                # Extract Y coordinates and calculate bounding box height
                y_coords = []
                for point in shape_data:
                    if isinstance(point, dict):
                        # Handle both {"X": x, "Y": y} and {"x": x, "y": y} formats
                        y = point.get('Y') or point.get('y')
                        if y is not None:
                            y_coords.append(float(y))
                    elif isinstance(point, (int, float)):
                        # Handle flat list format [x1, y1, x2, y2, ...]
                        # This is more complex, skip for now
                        pass
                
                if y_coords:
                    height = max(y_coords) - min(y_coords)
                else:
                    height = "N/A"
        else:
            height = "N/A"
            
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        height = "Unknown height"
        logger.warning(f"Error decoding JSON or accessing height: {e}")
    return str(height)

def get_roi_shape_width(roi):
    """Returns the ROI shape width."""
    try:
        shape_data_str = roi.get('shape', {}).get('Data', '{}')
        shape_data = json.loads(shape_data_str)
        
        # Handle different shape data formats
        if isinstance(shape_data, dict):
            # Rectangle ROI - has Height and Width keys
            width = shape_data.get('Width')
            if width is None:
                width = "N/A"
        elif isinstance(shape_data, list):
            # Polygon ROI - list of points, calculate bounding box width
            if not shape_data:
                width = "N/A"
            else:
                # Extract X coordinates and calculate bounding box width
                x_coords = []
                for point in shape_data:
                    if isinstance(point, dict):
                        # Handle both {"X": x, "Y": y} and {"x": x, "y": y} formats
                        x = point.get('X') or point.get('x')
                        if x is not None:
                            x_coords.append(float(x))
                    elif isinstance(point, (int, float)):
                        # Handle flat list format [x1, y1, x2, y2, ...]
                        # This is more complex, skip for now
                        pass
                
                if x_coords:
                    width = max(x_coords) - min(x_coords)
                else:
                    width = "N/A"
        else:
            width = "N/A"
            
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        width = "Unknown width"
        logger.warning(f"Error decoding JSON or accessing width: {e}")
    return str(width)

def get_autofocus_method(roi: dict[str, Any]) -> str:
    """Returns the autofocus method."""
    autofocus_method = roi.get("autoFocus", "Unknown autofocus method").get("method", "Unknown autofocus method")
    autofocus_method = autofocus_method.replace("AutofocusMethod_", "")
    return autofocus_method


# --------------------------------------------------
# Sample helper functions
# --------------------------------------------------

def get_sample_name(sample: dict[str, Any]) -> str:
    """Return sample name."""
    return sample.get("name", "Unknown sample")

def get_sample_species(sample: dict[str, Any]) -> str:
    """Return sample species."""
    return sample.get("species", "Unknown species")

def get_sample_type(sample: dict[str, Any]) -> str:
    """Return sample type."""
    sample_type = sample.get("sampleType", "Unknown sample type")
    # remove prefix "SampleType_"
    sample_type = sample_type.replace("SampleType_", "")
    return sample_type

def get_sample_organ(sample: dict[str, Any]) -> str:
    """Return sample organ."""
    return sample.get("organ", "Unknown organ")

def get_sample_fixation_method(sample: dict[str, Any]) -> str:
    """Return sample fixation method."""
    return sample.get("fixationMethod", "Unknown fixation method")

# --------------------------------------------------
# Procedure block functions
# --------------------------------------------------

def add_numbers_to_run_cycles(blocks: dict[str, Any]) -> dict[str, Any]:
    """Add numbers to run cycles."""
    run_cycle_number = 0
    updated_blocks = []
    for i, block in enumerate(blocks):
        if block.get("blockType") == "ProtocolBlockType_RunCycle":
            run_cycle_number += 1
            logger.debug(f"Adding run cycle number {run_cycle_number} to block {i}")
            block["runCycleNumber"] = run_cycle_number
        updated_blocks.append(block)
    return updated_blocks

def get_run_cycle_number(block: dict[str, Any]) -> int:
    """Return the run cycle number."""
    logger.debug(f"Block keys: {block.keys()}")
    return block.get("runCycleNumber", "Unknown run cycle number")

def get_block_type(block: dict[str, Any]) -> str:
    """Return the block type."""
    block_type = block.get("blockType", "Unknown block type")
    # remove prefix "ProtocolBlockType_"
    if block_type.startswith("ProtocolBlockType_"):
        block_type = block_type.replace("ProtocolBlockType_", "")
    return block_type

def get_block_name(block: dict[str, Any]) -> str:
    """Return the block name."""
    return block.get("name", "Unknown block name")

def get_block_magnification(block: dict[str, Any]) -> str:
    """Return the block magnification with 'Magnification_' prefix removed."""
    logger.debug(f"Block keys: {block.keys()}")
    magnification = block.get("magnification", "N/A")
    if magnification is not None and magnification != "N/A" and magnification.startswith("Magnification_"):
        return magnification.replace("Magnification_", "")
    return magnification if magnification is not None else "N/A"

def get_erase_bleaching_energy(block: dict[str, Any]) -> list[dict[str, Any]] | str:
    if block.get("blockType") != "ProtocolBlockType_Erase":
        return "N/A"
    
    results = []
    channels = block.get("photos", {})
    
    for channel in channels.values():
        fluor = channel.get("fluorochromeType")
        energy = channel.get("bleachingEnergy")
        enabled = channel.get("isEnabled", False)
        
        if enabled and fluor and fluor != "FluorochromeType_None" and energy:
            label = fluor.split("_")[-1]  # FluorochromeType_APC → APC
            results.append({"Channel": label, "bleachingEnergy": energy})
    
    return results if results else "N/A"

def get_erase_channel_info(block: dict[str, Any]) -> list[dict]:
    """
    Return a list like
        [
          {"Channel": "FITC", "ChannelInfo": {"BleachingEnergy": 1980}},
          {"Channel": "PE",   "ChannelInfo": {"BleachingEnergy": 840}},
          ...
        ]
    Only channels where *isEnabled* is true are listed.
    """
    out = []
    for dc in block.get("photos", {}).values():
        if (
            dc.get("isEnabled") 
            and dc.get("fluorochromeType") != "FluorochromeType_None"
        ):
            label = dc["fluorochromeType"].split("_")[-1]   # …_APC → APC
            out.append(
                {
                    "Channel": label,
                    "ChannelInfo": {"BleachingEnergy": dc.get("bleachingEnergy", "")},
                }
            )
    return out

  
def get_run_cycle_channel_info(block: dict, bucket_lookup: dict) -> list[dict]:
    """
    Build a run-cycle channel summary for one ProtocolBlockType_RunCycle block.
    Returns a list ordered DAPI ▸ FITC ▸ PE ▸ APC ▸ Vio780.
    """
    channel_order = [
        ("DetectionChannel_1", "DAPI"),
        ("DetectionChannel_2", "FITC"),
        ("DetectionChannel_3", "PE"),
        ("DetectionChannel_4", "APC"),
        ("DetectionChannel_5", "Vio780"),
    ]
    # Full field set (add more as needed)
    FIELDNAMES = [
        "Antigen", "Clone", "DilutionFactor", "IncubationTime", "ReagentExposureTime",
        "ExposureCoefficient", "ActualExposureTime", "ErasingMethod", "BleachingEnergy", "BleachingTime", "ValidatedFor",
        "Antibody", "AntibodyType", "HostSpecies", "Isotype", "Manufacturer", "Name", "OrderNumber", "Species"
    ]

    out: list[dict] = []
    dct_reagents = block.get("reagents", {})
    if not dct_reagents:
        logger.warning("No reagents found in RunCycle block")
        return out

    for key, chan_name in channel_order:
        dc = dct_reagents.get(key, {})
        chan_dict = {"Channel": chan_name}
        # Build a dict with all keys, defaulting to ""
        chan_info = {f: "" for f in FIELDNAMES}
        bucket_id = dc.get("bucketId", "")
        if bucket_id:
            reagent = bucket_lookup.get(bucket_id, {})
            # Fill from dc and reagent as before
            chan_info.update({
                "Antigen": reagent.get("antigen", ""),
                "Clone": reagent.get("clone", ""),
                "DilutionFactor": dc.get("dilutionFactor", ""),
                "IncubationTime": dc.get("incubationTime", ""),
                "ReagentExposureTime": reagent.get("exposureTime", ""),
                "ExposureCoefficient": dc.get("exposureTimeAndCoefficient", {}).get("timeCoefficient", ""),
                "ActualExposureTime": (
                    reagent.get("exposureTime", 0) * dc.get("exposureTimeAndCoefficient", {}).get("timeCoefficient", 0) / 100
                    if reagent.get("exposureTime") and dc.get("exposureTimeAndCoefficient") else ""
                ),
                "ErasingMethod": dc.get("erasingMethod", "").split("_")[-1] if dc.get("erasingMethod") else "",
                "BleachingEnergy": dc.get("bleachingEnergy", ""),
                "BleachingTime": dc.get("bleachingTime", ""),
                "ValidatedFor": reagent.get("supportedFixationMethods", ""),
                "Antibody": reagent.get("Antibody", ""),
                "AntibodyType": reagent.get("AntibodyType", ""),
                "HostSpecies": reagent.get("HostSpecies", ""),
                "Isotype": reagent.get("Isotype", ""),
                "Manufacturer": reagent.get("Manufacturer", ""),
                "Name": reagent.get("Name", ""),
                "OrderNumber": reagent.get("OrderNumber", ""),
                "Species": reagent.get("Species", ""),
            })
        chan_dict["ChannelInfo"] = chan_info
        out.append(chan_dict)
    return out


def build_bucket_lookup(data: dict) -> Dict[str, Dict[str, Any]]:
    """
    Map bucketId  ->  reagent metadata (antigen, clone, exposureTime, …)
    """
    # map bucketId ➜ reagent UUID (comes from the procedure)
    bucket_to_reagent_id: Dict[str, str] = {}
    for proc in data.get("procedures", []):
        for link in proc.get("reagents", []):
            bid  = link.get("bucketId")
            rid  = link.get("reagentId", {}).get("itemId")
            if bid and rid:
                bucket_to_reagent_id[bid] = rid

    #  map reagent UUID ➜ metadata (comes from the global catalogue)
    catalogue: Dict[str, Dict[str, Any]] = {
        r["id"]: {
            "antigen":      r.get("antigen",  "Unknown"),
            "clone":        r.get("clone",    "N/A"),
            "exposureTime": r.get("exposureTime", 0),
            "supportedFixationMethods": r.get("supportedFixationMethods", ""),
            "Antibody":         r.get("antibody", ""),
            "AntibodyType":     r.get("antibodyType", ""),
            "HostSpecies":      r.get("hostSpecies", ""),
            "Isotype":          r.get("isotype", ""),
            "Manufacturer":     r.get("manufacturer", ""),
            "Name":             r.get("name", ""),
            "OrderNumber":      r.get("orderNumber", ""),
            "Species":          r.get("species", ""),
        }
        for r in data.get("reagents", [])
    }

    return {bid: catalogue.get(rid, {}) for bid, rid in bucket_to_reagent_id.items()}


# ------------------------------------------------------------------ #
#  Query helpers
# ------------------------------------------------------------------ #
def get_antigen_clone_by_bucket(bucket_id: str,
                                bucket_lookup: Dict[str, Dict[str, str]]
                               ) -> Optional[Tuple[str, str]]:
    """
    Fast O(1) lookup using the pre-built dictionary.
    Returns (antigen, clone)  or  None if the bucket is unknown.
    """
    info = bucket_lookup.get(bucket_id)
    if info is None:
        return None
    return info["Antigen"], info["Clone"]


def get_antigen_clone_by_reagent_id(reagent_uuid: str,
                                    data: dict
                                   ) -> Optional[Tuple[str, str]]:
    """
    Directly fetch antigen / clone when you already have the reagent UUID.
    Scans the global reagent catalogue only once per call.
    """
    for reagent in data.get("reagents", []):
        if reagent.get("id") == reagent_uuid:
            return reagent.get("antigen", "Unknown"), reagent.get("clone", "N/A")
    return None

def process_experiment(experiment: dict[str, Any]) -> dict[str, Any]:
    """
    Process experiment data and return formatted dictionary.

    RunningTime: Machine-reported runtime (may exclude pauses)
    ElapsedTime: Wall-clock time from start to end (includes pauses)
    """
    return format_dict_headers({
        "ExperimentName":  get_experiment_name(experiment),
        "StartTime":       get_start_time(experiment),
        "EndTime":         get_end_time(experiment),
        "RunningTime":     get_running_time(experiment),
        "ElapsedTime":     get_elapsed_time(experiment),
        "UsedDiskSpace":   get_used_disk_space(experiment),
    })

def process_rois(roi: dict[str, Any]) -> dict[str, Any]:
    return format_dict_headers({
        "ROIName":    get_roi_name(roi),
        "Shape":      get_roi_shape_type(roi),
        "Height":     get_roi_shape_height(roi),
        "Width":      get_roi_shape_width(roi),
        "Autofocus":  get_autofocus_method(roi),
    })

def process_sample(sample: dict[str, Any]) -> dict[str, Any]:
    return format_dict_headers({
        "SampleName":   get_sample_name(sample),
        "Species":      get_sample_species(sample),
        "Type":         get_sample_type(sample),
        "Organ":        get_sample_organ(sample),
        "Fixation":     get_sample_fixation_method(sample),
    })

def propagate_magnification(blocks):
    last_mag = None
    out = []
    for block in blocks:
        # If 'magnification' is present and not None/empty, update last_mag
        if block.get("magnification"):
            last_mag = block["magnification"]
        new_block = block.copy()
        new_block["magnification"] = last_mag
        out.append(new_block)
    return out

def process_block(block: dict[str, Any],
                  bucket_lookup: dict[str, Any]) -> list[dict[str, Any]]:
    
    def create_ordered_row(**values):
        """Create a row with columns in the desired order."""
        # Define the desired column order
        column_order = [
            "RunCycleNumber", "BlockType", "Antigen", "Channel", "Magnification",
            "Clone", "DilutionFactor", "IncubationTime", "ReagentExposure", 
            "Coefficient", "ActualExposure", "ErasingMethod", "BleachingEnergy", "BleachingTime",
            "ValidatedFor", "Antibody", "AntibodyType", "HostSpecies", "Isotype",
            "Manufacturer", "OrderNumber", "Species", "Name"
        ]
        
        # Create ordered dictionary with empty defaults
        ordered_row = {}
        for col in column_order:
            ordered_row[col] = values.get(col, "")
        
        return ordered_row
    
    # Common values for all block types
    block_type = get_block_type(block)
    magnification = get_block_magnification(block)
    run_cycle_number = get_run_cycle_number(block) if block_type == "RunCycle" else ""

    # ---------- ERASE blocks -----------------------------------
    if block_type == "Erase":
        rows = []
        for chan in get_erase_channel_info(block):
            row = create_ordered_row(
                RunCycleNumber=run_cycle_number,
                BlockType=block_type,
                Magnification=magnification,
                Channel=chan["Channel"],
                BleachingEnergy=chan["ChannelInfo"]["BleachingEnergy"],
            )
            rows.append(format_dict_headers(row))
        return rows                         # <- finished for Erase

    # ---------- Non-run-cycle  (Scan, DefineROIs, …) -------------
    if block_type != "RunCycle":
        row = create_ordered_row(
            RunCycleNumber=run_cycle_number,
            BlockType=block_type,
            Magnification=magnification,
        )
        return [format_dict_headers(row)]

    # ---------- RUN-CYCLE blocks --------------------------------
    rows = []
    for chan in get_run_cycle_channel_info(block, bucket_lookup):
        cc = chan["ChannelInfo"]
        row = create_ordered_row(
            RunCycleNumber=run_cycle_number,
            BlockType=block_type,
            Antigen=cc.get("Antigen", ""),
            Channel=chan["Channel"],
            Magnification=magnification,
            Clone=cc.get("Clone", ""),
            DilutionFactor=cc.get("DilutionFactor", ""),
            IncubationTime=cc.get("IncubationTime", ""),
            ReagentExposure=cc.get("ReagentExposureTime", ""),
            Coefficient=cc.get("ExposureCoefficient", ""),
            ActualExposure=cc.get("ActualExposureTime", ""),
            ErasingMethod=cc.get("ErasingMethod", ""),
            BleachingEnergy=cc.get("BleachingEnergy", ""),
            BleachingTime=cc.get("BleachingTime", ""),
            ValidatedFor=cc.get("ValidatedFor", ""),
            Antibody=cc.get("Antibody", ""),
            AntibodyType=cc.get("AntibodyType", ""),
            HostSpecies=cc.get("HostSpecies", ""),
            Isotype=cc.get("Isotype", ""),
            Manufacturer=cc.get("Manufacturer", ""),
            OrderNumber=cc.get("OrderNumber", ""),
            Species=cc.get("Species", ""),
            Name=cc.get("Name", "")
        )
        rows.append(format_dict_headers(row))
    return rows


def process_all_procedures(data: dict[str, Any], bucket_lookup: dict[str, Any]) -> Dict[str, list[dict]]:
    """
    Process all procedures and return a dictionary keyed by procedure name.

    Each procedure's blocks are processed and stored under a unique key.
    If multiple procedures have the same name, a numeric suffix is added.

    Parameters
    ----------
    data : dict
        The loaded JSON data containing procedures.
    bucket_lookup : dict
        The bucket-to-reagent lookup table.

    Returns
    -------
    Dict[str, list[dict]]
        A dictionary where keys are sanitised procedure names and values
        are lists of processed block rows.
    """
    procedures_dict: Dict[str, list[dict]] = {}
    name_counts: Dict[str, int] = {}

    for proc in data.get("procedures", []):
        # Get the procedure name
        raw_name = get_procedure_name(proc)
        base_name = sanitise_sheet_name(raw_name)

        # Handle duplicate names by adding a numeric suffix
        if base_name in name_counts:
            name_counts[base_name] += 1
            # Ensure the suffix fits within Excel's 31 char limit
            suffix = f" ({name_counts[base_name]})"
            max_base_len = 31 - len(suffix)
            unique_name = sanitise_sheet_name(base_name, max_base_len) + suffix
        else:
            name_counts[base_name] = 1
            unique_name = base_name

        # Process the procedure's blocks
        blocks = add_numbers_to_run_cycles(proc.get("blocks", []))
        blocks = propagate_magnification(blocks)

        block_rows: list[dict] = []
        for b in blocks:
            block_rows.extend(process_block(b, bucket_lookup))

        # Add blank lines between different run cycles
        block_rows = add_blank_lines_between_run_cycles(block_rows)

        procedures_dict[unique_name] = block_rows

    return procedures_dict


if __name__ == "__main__":
    json_path = get_input_path()
    logger.info(f"Loading JSON: {json_path}")
    data          = load_json(json_path)
    bucket_lookup = build_bucket_lookup(data)

    # ---------- gather rows ------------------------------------
    exp_rows    = [process_experiment(e) for e in data["experiments"]]
    rack_rows   = [{"RackName": get_rack_name(r)} for r in data["racks"]]
    roi_rows    = [process_rois(r)       for r in data["rois"]]
    sample_rows = [process_sample(s)     for s in data["samples"]]

    # Process all procedures into a dictionary keyed by procedure name
    procedures_dict = process_all_procedures(data, bucket_lookup)

    # ---------- to Excel ---------------------------------------
    out_xlsx = json_path.with_suffix(".xlsx")
    logger.info(f"Writing Excel report ➜ {out_xlsx}")

    import pandas as pd
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as xls:
        pd.DataFrame(exp_rows   ).to_excel(xls, sheet_name="Experiment", index=False)
        pd.DataFrame(rack_rows  ).to_excel(xls, sheet_name="Racks",      index=False)
        pd.DataFrame(roi_rows   ).to_excel(xls, sheet_name="ROIs",       index=False)
        pd.DataFrame(sample_rows).to_excel(xls, sheet_name="Samples",    index=False)

        # Write each procedure to its own sheet
        for proc_name, block_rows in procedures_dict.items():
            pd.DataFrame(block_rows).to_excel(xls, sheet_name=proc_name, index=False)

    logger.info("✅ Excel report created successfully.")
    logger.info(f"📊 Excel report saved to: {out_xlsx}")
