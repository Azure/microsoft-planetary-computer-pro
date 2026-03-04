# Copilot Instructions for aurora_hackathon

## Critical: Large Notebook Handling

The main notebook `applications/storm_impact_assessment/hurricane_forecast_infra_impact.ipynb` is **1.57 MB / 19K JSON lines / 71 cells** with 1.07 MB of embedded outputs. This exceeds VS Code's diff editor limits and causes Copilot edit tools (`edit_notebook_file`, `replace_string_in_file`) to fail silently or produce corrupt edits.

### Rules for Editing the Notebook

1. **NEVER use VS Code's built-in notebook edit tools** (`edit_notebook_file`, `replace_string_in_file`) on `applications/storm_impact_assessment/hurricane_forecast_infra_impact.ipynb`. They will fail due to file size.

2. **ALWAYS use `python applications/storm_impact_assessment/scripts/nb_edit.py` commands in the terminal** (from the repo root) to read and modify the notebook. The script operates directly on the `.ipynb` JSON and auto-creates backups.

3. **For reading cell content:**
   ```bash
   python applications/storm_impact_assessment/scripts/nb_edit.py read <cell_index>                # full cell
   python applications/storm_impact_assessment/scripts/nb_edit.py read <cell_index> --lines 50-80  # specific lines
   ```

4. **For searching across all cells:**
   ```bash
   python applications/storm_impact_assessment/scripts/nb_edit.py search "function_name"
   ```

5. **For replacing text in a cell:**
   ```bash
   # Simple inline replacement
   python applications/storm_impact_assessment/scripts/nb_edit.py replace <cell_index> --old "old_text" --new "new_text"

   # Multiline replacement using temp files
   # Step 1: Write old text to a temp file
   # Step 2: Write new text to a temp file
   # Step 3: Run replacement
   python applications/storm_impact_assessment/scripts/nb_edit.py replace <cell_index> --old-file old.txt --new-file new.txt
   ```

6. **For replacing a range of lines in a cell:**
   ```bash
   # First read the lines to verify
   python applications/storm_impact_assessment/scripts/nb_edit.py read <cell_index> --lines 100-120
   # Write new content to a file, then replace
   python applications/storm_impact_assessment/scripts/nb_edit.py replace-lines <cell_index> --lines 100-120 --file new_content.py
   ```

7. **For inserting or deleting cells:**
   ```bash
   python applications/storm_impact_assessment/scripts/nb_edit.py insert <after_index> --type code --file content.py
   python applications/storm_impact_assessment/scripts/nb_edit.py delete <cell_index>
   ```

8. **For listing all cells:**
   ```bash
   python applications/storm_impact_assessment/scripts/nb_edit.py list
   ```

9. **For reducing file size (clear outputs):**
   ```bash
   python applications/storm_impact_assessment/scripts/nb_edit.py clear-outputs          # all cells
   python applications/storm_impact_assessment/scripts/nb_edit.py clear-outputs --cell 21  # specific cell
   ```

### Workflow for Multi-line Edits

When making complex edits with multiline old/new text:

```bash
# 1. Read the target area
python applications/storm_impact_assessment/scripts/nb_edit.py read <cell> --lines <start>-<end>

# 2. Create temp files with the old and new content
#    (use create_file tool to write old.txt and new.txt)

# 3. Apply the replacement
python applications/storm_impact_assessment/scripts/nb_edit.py replace <cell> --old-file old.txt --new-file new.txt

# 4. Verify the edit
python applications/storm_impact_assessment/scripts/nb_edit.py read <cell> --lines <start>-<end>

# 5. Clean up temp files
```

## Project Context

- This is an **Azure Aurora AI weather model** project for hurricane forecasting and infrastructure impact analysis.
- The notebook processes GRIB2/NetCDF weather data, runs Aurora model inference, and overlays infrastructure data from Microsoft Planetary Computer (STAC catalog) and Azure GeoCatalog.
- Key dependencies: `microsoft-aurora`, `xarray`, `pystac-client`, `geopandas`, `folium`, `azure-ai-inference`.
- Python environment is managed via `pyenv` (Python 3.13.0).

## Cell Index Reference (0-based) — 71 cells total

- Cells 0-3: Title, intro markdown, pre-requisites
- Cells 4-5: Environment setup (dotenv, Azure config)
- Cell 6: Markdown — Download Storm Data from IBTrACS
- Cell 7: Large helper/utility functions (1425 lines) — core data processing
- Cells 8-9: Markdown — Download Model Input Data, data availability check
- Cell 10: Data availability check code (461 lines)
- Cells 11-16: Download OPER/SCDA stream data, merge GRIB files (markdown + code)
- Cells 17-18: Open & combine GRIB/xarray datasets
- Cells 19-26: Upload to Azure GeoCatalog (blob storage, STAC ingest, render config, fallback URLs)
- Cells 27-28: Download ERA5 static variables
- Cells 29-39: Prepare Aurora Batch (surface, atmospheric, static vars, create batch, verify dims)
- Cell 30: Markdown — Build Unified Impact Zone (misplaced section header)
- Cells 40-41: Run Aurora Model Inference (markdown + code, 275 lines)
- Cells 42-45: Upload forecast results to GeoCatalog, configure visualization
- Cells 46-49: Visualize Hurricane Track (matplotlib, track extraction — cells 48-49 are large: 425/505 lines)
- Cells 50-52: Upload track & impact swath to GeoCatalog, fallback URLs
- Cells 53-56: Infrastructure Impact Analysis setup (markdown, package install, imports)
- Cells 57-58: Create Storm Cone of Uncertainty
- Cells 59-66: Query power infrastructure from OpenStreetMap (Overpass API, substations, power lines, summary)
- Cells 67-68: Ingest infrastructure data to GeoCatalog (cell 68: 683 lines)
- Cells 69-70: Animated storm & infrastructure map (cell 70: 1167 lines, STAC/endpoint fallback)
