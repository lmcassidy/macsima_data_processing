from flask import Flask, request, send_file, render_template, jsonify
import os
import tempfile
from pathlib import Path
import logging

# Import your existing parser
from src.macsima_parser import (
    load_json,
    build_bucket_lookup,
    process_experiment,
    process_rois,
    process_sample,
    process_all_procedures,
    get_rack_name,
)
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this to a random secret key
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_friendly_error_message(exception, filename):
    """Convert technical exceptions into user-friendly error messages"""
    error_str = str(exception).lower()
    exception_type = type(exception).__name__

    # Check exception type first for more accurate detection
    if exception_type == 'JSONDecodeError' or 'json' in error_str and ('decode' in error_str or 'parse' in error_str or 'expecting' in error_str):
        return f"The file '{filename}' is not valid JSON. Please check that the file contains properly formatted JSON data with correct syntax (matching braces, commas, quotes)."

    elif exception_type == 'KeyError' or 'key' in error_str and ('error' in error_str or 'missing' in error_str):
        # Try to determine which field is missing
        missing_field = str(exception).strip("'\"")
        if 'experiments' in missing_field:
            return f"The JSON file '{filename}' is missing the required 'experiments' field. Your JSON must contain an 'experiments' array with experiment data."
        elif 'procedures' in missing_field:
            return f"The JSON file '{filename}' is missing the required 'procedures' field. Your JSON must contain a 'procedures' array with processing steps."
        elif 'racks' in missing_field:
            return f"The JSON file '{filename}' is missing the required 'racks' field. Your JSON must contain a 'racks' array with rack information."
        elif 'rois' in missing_field:
            return f"The JSON file '{filename}' is missing the required 'rois' field. Your JSON must contain an 'rois' array with region of interest data."
        elif 'samples' in missing_field:
            return f"The JSON file '{filename}' is missing the required 'samples' field. Your JSON must contain a 'samples' array with sample information."
        else:
            return f"The JSON file '{filename}' is missing required data fields. Your JSON must contain these top-level fields: 'experiments', 'procedures', 'racks', 'rois', and 'samples'."

    elif 'memory' in error_str or 'size' in error_str:
        return f"The file '{filename}' is too large or complex to process. Please try with a smaller file or contact support."

    elif 'permission' in error_str or 'access' in error_str:
        return "Unable to process the file due to system permissions. Please try again or contact support."

    elif 'timeout' in error_str:
        return f"Processing '{filename}' took too long and timed out. Please try with a smaller file."

    elif 'isoformat' in error_str or 'date' in error_str:
        return f"The file '{filename}' contains invalid date/time formats. Please ensure all datetime fields use ISO format (e.g., '2025-01-01T10:00:00Z')."

    elif 'attribute' in error_str and 'get' in error_str:
        return f"The file '{filename}' has incorrect data types or structure. Please verify that objects contain the expected fields and data types."

    else:
        # For unknown errors, provide a generic but helpful message
        return f"An unexpected error occurred while processing '{filename}'. The file may be corrupted or in an unsupported format. Please check the JSON structure and data types."


def process_json_to_excel(json_file_path):
    """Process JSON file and return Excel file path"""
    logger.info(f"Processing JSON file: {json_file_path}")

    # Load and process the JSON data
    data = load_json(json_file_path)
    bucket_lookup = build_bucket_lookup(data)

    # Gather rows for shared sheets
    exp_rows = [process_experiment(e) for e in data["experiments"]]
    rack_rows = [{"RackName": get_rack_name(r)} for r in data["racks"]]
    roi_rows = [process_rois(r) for r in data["rois"]]
    sample_rows = [process_sample(s) for s in data["samples"]]

    # Process all procedures into a dictionary keyed by procedure name
    procedures_dict = process_all_procedures(data, bucket_lookup)

    # Create Excel file
    excel_path = Path(json_file_path).with_suffix(".xlsx")

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as xls:
        pd.DataFrame(exp_rows).to_excel(xls, sheet_name="Experiment", index=False)
        pd.DataFrame(rack_rows).to_excel(xls, sheet_name="Racks", index=False)
        pd.DataFrame(roi_rows).to_excel(xls, sheet_name="ROIs", index=False)
        pd.DataFrame(sample_rows).to_excel(xls, sheet_name="Samples", index=False)

        # Write each procedure to its own sheet
        for proc_name, block_rows in procedures_dict.items():
            pd.DataFrame(block_rows).to_excel(xls, sheet_name=proc_name, index=False)

    logger.info(f"Excel report created successfully: {excel_path}")
    return str(excel_path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            'error': True,
            'message': 'No file selected'
        }), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({
            'error': True,
            'message': 'No file selected'
        }), 400

    if file and allowed_file(file.filename):
        temp_json_path = None
        excel_path = None
        try:
            # Create temporary file for uploaded JSON
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_json:
                temp_json_path = temp_json.name
                file.save(temp_json_path)

            # Process the JSON file
            excel_path = process_json_to_excel(temp_json_path)

            # Send the Excel file to user
            response = send_file(
                excel_path,
                as_attachment=True,
                download_name=f"{Path(file.filename).stem}_report.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # Schedule cleanup after response is sent
            @response.call_on_close
            def cleanup():
                try:
                    if temp_json_path and os.path.exists(temp_json_path):
                        os.unlink(temp_json_path)
                    if excel_path and os.path.exists(excel_path):
                        os.unlink(excel_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary files: {e}")

            return response

        except Exception as e:
            # Cleanup on error
            try:
                if temp_json_path and os.path.exists(temp_json_path):
                    os.unlink(temp_json_path)
                if excel_path and os.path.exists(excel_path):
                    os.unlink(excel_path)
            except Exception:
                pass

            # Provide user-friendly error messages
            error_message = get_user_friendly_error_message(e, file.filename)
            logger.error(f"Processing error for {file.filename}: {str(e)}")

            # Always return JSON error response for upload endpoint
            return jsonify({
                'error': True,
                'message': error_message
            }), 400
    else:
        # Return JSON error for invalid file type
        return jsonify({
            'error': True,
            'message': 'Invalid file type. Please upload a JSON file.'
        }), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
