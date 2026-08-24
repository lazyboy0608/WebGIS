## SEG-Y Processing Service

Backend service for processing raw 2D SEG-Y files and persisting derived seismic
data to PostgreSQL/PostGIS.

### Processing flow

1. `POST /api/segy-files` creates the parent SEG-Y file record.
2. `POST /api/segy-files/{file_id}/process` resolves the stored file.
3. The application use case reads metadata and traces, normalizes SP/X/Y
	coordinates, groups shot points, builds the seismic line, analyzes topology,
	and transforms the line to WGS84.
	order so trace relationships can reference the generated database IDs.
1. `POST /api/segy-files/upload` accepts a multipart SEG-Y file and an optional
	`source_crs` form field. If the field is omitted, the service reads the
	`EPSG:<code>` value from the SEG-Y textual header. It stores the file, reads
	its metadata, creates the parent record, processes the file, and persists the
	result in WGS84 (`EPSG:4326`).
2. `POST /api/segy-files/upload/batch` accepts multiple multipart files using
	the `files` field and processes them sequentially in one transaction. If one
	file fails, the database changes and stored files for the whole request are
	rolled back/removed.
3. `POST /api/segy-files` can still create a parent SEG-Y file record manually.
4. `POST /api/segy-files/{file_id}/process` resolves a file already stored in
	`storage/segy` and processes it using the record's `source_crs`.
5. The application use case reads metadata and traces, normalizes SP/X/Y
	coordinates, groups shot points, builds the seismic line, analyzes topology,
	and transforms the line to WGS84.
5. Persistence stores the seismic line, shot points, and traces in dependency
	order so trace relationships can reference the generated database IDs.
	It also stores the processed line as a `MULTILINESTRING` in
	`segy_files.geometry` using WGS84 (`EPSG:4326`).

### Processed data API

Processed geometries are exposed as GeoJSON in WGS84 (`EPSG:4326`) for Backend
2 or a WebGIS client:

- `GET /api/segy-files/{file_id}/processed/summary`
- `GET /api/segy-files/{file_id}/processed/line`
- `GET /api/segy-files/{file_id}/processed/lines`
- `GET /api/segy-files/{file_id}/processed/shot-points?offset=0&limit=1000`
- `GET /api/segy-files/{file_id}/processed/traces?offset=0&limit=1000`

The singular line endpoint returns the first GeoJSON `Feature` for backwards
compatibility. The plural lines endpoint returns every line as a GeoJSON
`FeatureCollection`. Shot points and traces return GeoJSON `FeatureCollection` responses. Shot points and traces are paginated;
the maximum page size is 10,000.

The current WebGIS test fixture is `data/input/slb1.sgy` with source CRS
`EPSG:26782`. The service persists derived 2D geometries in WGS84 (`EPSG:4326`);
SEG-Y amplitude samples are not loaded or persisted yet.

### Multi-line grouping

Traces are grouped before Polyline construction using the SEG-Y
`original_field_record_number` header value as the line-group key. Each group
becomes a separate `seismic_lines` record, and traces/Shot Points reference the
corresponding line. Files without distinct values in this field produce one
line, as with `slb1.sgy`. The API endpoint `/processed/lines` returns all lines
for a file as a GeoJSON `FeatureCollection`.
### Package boundaries

- `app/api`: HTTP routes, dependency injection, and request/response schemas.
- `app/application`: use cases and orchestration services.
- `app/domain`: models, repository contracts, and file storage contracts.
- `app/infrastructure`: SEG-Y reader, local storage, SQLAlchemy models, and
  PostgreSQL/PostGIS repositories.
- `alembic`: database migrations.

The former `app.services` import paths remain compatibility facades for callers
that have not migrated to `app.application.services` yet.

### Run

Set `DATABASE_URL`, install `requirements-dev.txt`, then run:

```powershell
python -m pytest tests -v
uvicorn app.main:app --reload
```
