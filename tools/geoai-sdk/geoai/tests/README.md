# GeoAI SDK Test Suite

Comprehensive unit tests for core SDK functionality.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_chipmaker.py           # Chip generation and grid logic
│   ├── test_detection_merger.py   # NMS and detection deduplication
│   ├── test_constraint.py          # Multi-AOI iteration and geometry handling
│   ├── test_spec_validator.py      # Model spec validation
│   └── test_geometry_utils.py      # Coordinate conversions and bbox operations
└── integration/             # Integration tests (optional - not implemented yet)
```

## Running Tests

### First-time setup:

Install the SDK with dev dependencies (includes pytest):
```bash
pip install -e ".[dev]"
```

### Run all tests:
```bash
pytest tests/
```

Or use Python module syntax:
```bash
python -m pytest tests/
```

### Run specific test file:
```bash
pytest tests/unit/test_chipmaker.py -v
```

### Run tests with coverage:
```bash
pytest tests/ --cov=geoai --cov-report=html
```

Coverage report will be in `htmlcov/index.html`

## What's Tested

### ✅ Core Logic (Unit Tests)

**ChipMaker** (`test_chipmaker.py`)
- Chip grid generation for various AOI sizes
- Overlap calculation with different stride values
- Coordinate transformation (Web Mercator ↔ WGS84)
- Edge cases (single chip, small AOIs)

**DetectionMerger** (`test_detection_merger.py`)
- NMS logic for polygon features
- IoU-based clustering
- Different label handling
- Line geometry merging
- AOI clipping

**Constraint** (`test_constraint.py`)
- Single vs multi-AOI mode detection
- GeoDataFrame and GeoParquet loading
- AOI iteration and property preservation
- STAC search pass-through
- Validation and error handling

**SpecValidator** (`test_spec_validator.py`)
- Required field validation
- Schema conformance checking
- Error and warning collection
- File and dict input handling

**GeometryUtils** (`test_geometry_utils.py`)
- Bbox to geometry conversion
- Geometry to bbox extraction
- Bbox union operations
- Coordinate roundtripping

## Integration Tests (Future)

Integration tests would verify end-to-end workflows with real services:
- STAC search against Planetary Computer
- Model inference with real endpoints
- GeoCatalog publishing
- Blob storage operations

## Test Coverage

Current focus: **Core business logic** with high confidence

Areas covered:
- ✅ Chip generation and grid math
- ✅ Detection merging and NMS
- ✅ Multi-AOI handling
- ✅ Spec validation
- ✅ Geometry utilities

## Dependencies

Required for tests:
```bash
pytest>=7.0
pytest-asyncio>=0.21
pytest-cov>=4.0  # For coverage reports (optional)
```

Install dev dependencies:
```bash
pip install -e ".[dev]"
```
