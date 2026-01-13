# Test Suite Documentation

This document describes the test infrastructure for the Timesketch browser frontend.

## Test Structure

Tests are organized into three main categories:

### 1. JavaScript Tests (Vitest)
Located in `src/__tests__/` - tests for frontend functionality

### 2. Python Tests (pytest)
Located in `src/pyparser/` - tests for data parsing and processing

### 3. Test Data
Sample files for each platform should be placed in `test-data/` directory

---

## JavaScript Tests

### Running JS Tests

```bash
# Run all tests
npm test

# Run specific test file
npm test -- schemaValidation.test.js

# Run with coverage
npm test -- --coverage

# Watch mode (re-run on file changes)
npm test -- --watch
```

### Test Files

#### `schemaValidation.test.js`
Tests schema validation against YAML files in `/schemas`:
- Validates all platform schemas (google.yaml, discord.yaml, etc.)
- Checks required fields and structure
- Tests schema_validation.yaml itself

**Status:** Ready to run  
**Dependencies:** Schema files must exist in `/schemas`

#### `database.test.js`
Tests IndexedDB CRUD operations:
- Sketch creation, retrieval, update, delete
- Timeline management
- Event creation and querying
- Tags and annotations
- Response format validation

**Status:** Scaffolded, needs mock database setup  
**Dependencies:** BrowserDB instance, test database isolation

#### `upload.test.js`
Tests file upload and data import pipeline:
- ZIP file validation
- Platform schema matching
- JSON/JSONL/CSV parsing
- Data insertion
- Error handling
- Progress tracking

**Status:** Scaffolded with placeholders  
**Dependencies:** Mock files, processUpload implementation

---

## Python Tests

### Running Python Tests

```bash
# Run all parser tests
pytest src/pyparser/test_parser.py -v

# Run specific test class
pytest src/pyparser/test_parser.py::TestSchemaLoading -v

# Run with output
pytest src/pyparser/test_parser.py -v -s

# Run with coverage
pytest src/pyparser/test_parser.py --cov=src/pyparser
```

### Test File

#### `test_parser.py`
Tests data parsing and transformation:
- Schema loading and validation
- Timestamp parsing (ISO8601, Unix, custom formats)
- JSON parsing (simple and nested)
- JSONL parsing (including large files >1MB)
- CSV parsing with delimiters
- Data normalization to standard event format
- Platform-specific parsers
- Error handling and validation

**Status:** Fully scaffolded with pytest.skip() placeholders  
**Dependencies:** Parser implementation (in progress)

### Test Data Organization

Create test data files in `test-data/` directory:

```
test-data/
├── google/
│   ├── sample_1.json
│   ├── sample_2.jsonl
│   └── large_sample.jsonl
├── discord/
│   └── messages.json
├── apple/
│   └── sms_backup.csv
└── README.md
```

When you're ready to implement parser tests, provide these sample files and I'll update the tests to use them.

---

## Implementation Checklist

### JavaScript Tests
- [ ] `schemaValidation.test.js` - Ready to run now
- [ ] `database.test.js` - Needs test database mock setup
- [ ] `upload.test.js` - Needs file fixtures and implementation

### Python Tests
- [ ] `test_parser.py` - Waiting for:
  - Parser module implementation
  - Sample test data files
  - Fixture files (sample JSON, JSONL, CSV)

### Test Data
- [ ] Provide sample Google Takeout structure (JSON files)
- [ ] Provide Discord export sample
- [ ] Provide Apple iCloud backup sample
- [ ] Provide Instagram export sample
- [ ] Provide Facebook export sample
- [ ] Create large JSONL test file (>1MB)

---

## Running Tests in CI/CD

To add to your CI pipeline, add to `package.json` scripts:

```json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:python": "pytest src/pyparser/ -v"
  }
}
```

---

## Next Steps

1. **Schema Validation** - Run `npm test -- schemaValidation.test.js` now to validate your schema files

2. **Database Tests** - Need to:
   - Set up test database instance (isolated from production)
   - Mock Dexie for unit tests or use actual IndexedDB in test environment
   - Implement database method mocks

3. **Parser Tests** - When ready:
   - Provide sample data files for each platform
   - Implement pyparser modules
   - Uncomment test code

4. **Upload Tests** - When parser is working:
   - Create mock ZIP files with test data
   - Implement upload workflow
   - Test end-to-end flow

---

## Notes

- All JavaScript tests use **Vitest** (configured in vitest.config.js)
- Python tests use **pytest** (install with `pip install pytest`)
- Tests are **fully isolated** - no shared state between tests
- Failed tests should provide clear error messages for debugging
- Use `pytest.skip()` for unimplemented tests (they're counted but not failed)
