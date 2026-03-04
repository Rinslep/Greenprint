"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded

from api.dependencies import envelope, limiter
from api.v1 import v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from storage.database import init_db
    init_db()
    yield


app = FastAPI(
    title="Greenprint — Factorio Blueprint Analyser",
    version="0.1.0",
    description="REST API for querying analysed Factorio 1.1 blueprints.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.include_router(v1_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greenprint — Factorio Blueprint Analyser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17;
            color: #c8d6e5;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a2332 0%, #0d1821 100%);
            border-bottom: 1px solid #1e3a5f;
            padding: 2rem 0;
            text-align: center;
        }
        .header h1 {
            color: #4ade80;
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .header p {
            color: #7f8c9b;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        }
        .container {
            max-width: 900px;
            margin: 2rem auto;
            padding: 0 1.5rem;
        }
        .section {
            margin-bottom: 2rem;
        }
        .section h2 {
            color: #4ade80;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #1e2d3d;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 0.75rem;
        }
        .card {
            background: #111927;
            border: 1px solid #1e2d3d;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            text-decoration: none;
            color: inherit;
            transition: border-color 0.2s, background 0.2s;
        }
        .card:hover {
            border-color: #4ade80;
            background: #162030;
        }
        .card .method {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 2px 6px;
            border-radius: 3px;
            margin-right: 0.5rem;
        }
        .get { background: #1a3a2a; color: #4ade80; }
        .post { background: #3a2a1a; color: #f59e0b; }
        .card .path {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            color: #e2e8f0;
        }
        .card .desc {
            color: #7f8c9b;
            font-size: 0.8rem;
            margin-top: 0.4rem;
        }
        .docs-link {
            display: inline-block;
            background: #4ade80;
            color: #0a0e17;
            font-weight: 600;
            padding: 0.6rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9rem;
            transition: opacity 0.2s;
        }
        .docs-link:hover { opacity: 0.85; }
        .docs-bar {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .docs-bar span {
            color: #7f8c9b;
            margin: 0 0.75rem;
            font-size: 0.85rem;
        }
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #3e4c5e;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Greenprint</h1>
        <p>Factorio Blueprint Analyser &mdash; REST API v0.1.0</p>
    </div>
    <div class="container">
        <div class="docs-bar">
            <a class="docs-link" href="/blueprints/browse">Browse Blueprints</a>
            <span>&middot;</span>
            <a class="docs-link" href="/motifs/browse" style="background:#3b82f6;">Browse Motifs</a>
            <span>&middot;</span>
            <a class="docs-link" href="/docs" style="background:#64748b;">Swagger UI</a>
            <span>&middot;</span>
            <a class="docs-link" href="/redoc" style="background:#64748b;">ReDoc</a>
        </div>

        <div class="section">
            <h2>Blueprints</h2>
            <div class="grid">
                <a class="card" href="/v1/blueprints">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints</span>
                    <div class="desc">List all blueprints with filters &amp; pagination</div>
                </a>
                <a class="card" href="/docs#/blueprints/get_blueprint_blueprints__blueprint_id__get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints/{id}</span>
                    <div class="desc">Full blueprint record with flags &amp; summary</div>
                </a>
                <a class="card" href="/docs#/blueprints/get_blueprint_graph_blueprints__blueprint_id__graph_get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints/{id}/graph</span>
                    <div class="desc">Crafting graph: products, inputs, intermediates</div>
                </a>
                <a class="card" href="/docs#/blueprints/get_blueprint_ratios_blueprints__blueprint_id__ratios_get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints/{id}/ratios</span>
                    <div class="desc">Ratio analysis: ideal vs actual machine counts</div>
                </a>
                <a class="card" href="/docs#/blueprints/get_blueprint_throughput_blueprints__blueprint_id__throughput_get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints/{id}/throughput</span>
                    <div class="desc">Throughput: bottlenecks &amp; lane saturation</div>
                </a>
                <a class="card" href="/docs#/blueprints/get_blueprint_motifs_blueprints__blueprint_id__motifs_get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/blueprints/{id}/motifs</span>
                    <div class="desc">Motifs found in this blueprint</div>
                </a>
            </div>
        </div>

        <div class="section">
            <h2>Motifs</h2>
            <div class="grid">
                <a class="card" href="/v1/motifs">
                    <span class="method get">GET</span>
                    <span class="path">/v1/motifs</span>
                    <div class="desc">Browse the motif catalogue</div>
                </a>
                <a class="card" href="/docs#/motifs/get_motif_motifs__motif_id__get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/motifs/{id}</span>
                    <div class="desc">Full motif with canonical entities</div>
                </a>
                <a class="card" href="/docs#/motifs/get_motif_blueprints_motifs__motif_id__blueprints_get">
                    <span class="method get">GET</span>
                    <span class="path">/v1/motifs/{id}/blueprints</span>
                    <div class="desc">Blueprints containing this motif</div>
                </a>
            </div>
        </div>

        <div class="section">
            <h2>Recipes</h2>
            <div class="grid">
                <a class="card" href="/v1/recipes?per_page=20">
                    <span class="method get">GET</span>
                    <span class="path">/v1/recipes</span>
                    <div class="desc">Vanilla 1.1 recipe reference data</div>
                </a>
                <a class="card" href="/v1/recipes/electronic-circuit">
                    <span class="method get">GET</span>
                    <span class="path">/v1/recipes/{name}</span>
                    <div class="desc">Single recipe lookup</div>
                </a>
            </div>
        </div>

        <div class="section">
            <h2>Analysis</h2>
            <div class="grid">
                <a class="card" href="/v1/analysis/stats">
                    <span class="method get">GET</span>
                    <span class="path">/v1/analysis/stats</span>
                    <div class="desc">Dataset-level aggregate statistics</div>
                </a>
                <a class="card" href="/docs#/analysis/compare_blueprints_analysis_compare_post">
                    <span class="method post">POST</span>
                    <span class="path">/v1/analysis/compare</span>
                    <div class="desc">Side-by-side blueprint comparison</div>
                </a>
                <a class="card" href="/docs#/analysis/search_similar_analysis_search_post">
                    <span class="method post">POST</span>
                    <span class="path">/v1/analysis/search</span>
                    <div class="desc">Find similar blueprints by motif overlap</div>
                </a>
            </div>
        </div>

        <div class="section">
            <h2>Review Queue</h2>
            <div class="grid">
                <a class="card" href="/v1/review-queue">
                    <span class="method get">GET</span>
                    <span class="path">/v1/review-queue</span>
                    <div class="desc">Unresolved recipe inference items</div>
                </a>
                <a class="card" href="/docs#/review-queue/resolve_review_item_review_queue__item_id__post">
                    <span class="method post">POST</span>
                    <span class="path">/v1/review-queue/{id}</span>
                    <div class="desc">Submit a resolution</div>
                </a>
            </div>
        </div>
    </div>
    <div class="footer">Greenprint v0.1.0 &mdash; Factorio 1.1.110</div>
</body>
</html>"""


@app.get("/motifs/browse", response_class=HTMLResponse, include_in_schema=False)
async def motif_browser():
    """Interactive motif browser with SVG rendering."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greenprint — Motif Browser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17; color: #c8d6e5; min-height: 100vh;
        }
        .header { background: linear-gradient(135deg, #1a2332 0%, #0d1821 100%);
            border-bottom: 1px solid #1e3a5f; padding: 1.5rem 0; text-align: center; }
        .header h1 { color: #4ade80; font-size: 1.5rem; }
        .header p { color: #7f8c9b; margin-top: 0.3rem; font-size: 0.85rem; }
        .nav { text-align: center; padding: 0.75rem 0; background: #0d1117; border-bottom: 1px solid #1e2d3d; }
        .nav a { color: #7f8c9b; text-decoration: none; font-size: 0.8rem; margin: 0 1rem;
            transition: color 0.15s; }
        .nav a:hover, .nav a.active { color: #4ade80; }
        .container { max-width: 1200px; margin: 1.5rem auto; padding: 0 1.5rem; }
        .motif-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }
        .motif-card { background: #111927; border: 1px solid #1e2d3d; border-radius: 8px; padding: 1rem; position: relative; }
        .motif-card h3 { color: #e2e8f0; font-size: 0.85rem; margin-bottom: 0.5rem; }
        .card-actions { position: absolute; top: 0.5rem; right: 0.5rem; display: flex; gap: 4px; z-index: 1; }
        .card-btn { background: #1e2d3d; border: 1px solid #2d3d4d;
            color: #7f8c9b; font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; cursor: pointer;
            transition: all 0.15s; }
        .card-btn:hover { background: #2d3d4d; color: #e2e8f0; }
        .card-btn.copied { background: #1a3a2a; color: #4ade80; border-color: #4ade80; }
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8);
            z-index: 100; justify-content: center; align-items: center; }
        .modal-overlay.active { display: flex; }
        .modal-content { background: #111927; border: 1px solid #1e3a5f; border-radius: 12px;
            padding: 1.5rem; max-width: 90vw; max-height: 90vh; position: relative; }
        .modal-content h3 { color: #e2e8f0; font-size: 1.1rem; margin-bottom: 0.5rem; }
        .modal-content .meta { color: #7f8c9b; font-size: 0.85rem; margin-bottom: 1rem; }
        .modal-content svg { background: #0d1117; border-radius: 6px; width: 100%; max-height: 70vh; }
        .modal-close { position: absolute; top: 0.75rem; right: 0.75rem; background: #1e2d3d; border: 1px solid #2d3d4d;
            color: #c8d6e5; font-size: 1.2rem; width: 28px; height: 28px; border-radius: 4px;
            cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .modal-close:hover { background: #2d3d4d; }
        .motif-card .meta { color: #7f8c9b; font-size: 0.75rem; margin-bottom: 0.75rem; }
        .motif-card svg { background: #0d1117; border-radius: 4px; width: 100%; }
        .badge { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 2px 6px;
            border-radius: 3px; margin-right: 4px; }
        .badge-direct { background: #3a2a1a; color: #f59e0b; }
        .badge-simple { background: #1a3a2a; color: #4ade80; }
        .badge-underground { background: #2a1a3a; color: #a78bfa; }
        .badge-split { background: #1a2a3a; color: #60a5fa; }
        .badge-merged { background: #3a1a2a; color: #f472b6; }
        #loading { text-align: center; padding: 3rem; color: #7f8c9b; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Motif Browser</h1>
        <p>Common connection patterns between machines</p>
    </div>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/blueprints/browse">Blueprints</a>
        <a href="/motifs/browse" class="active">Motifs</a>
    </div>
    <div class="container">
        <div id="loading">Loading motifs...</div>
        <div id="motif-grid" class="motif-grid"></div>
    </div>
    <div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>
    <script>
        const ENTITY_SIZES = {
            'assembling-machine-1': [3,3], 'assembling-machine-2': [3,3], 'assembling-machine-3': [3,3],
            'chemical-plant': [3,3], 'oil-refinery': [5,5], 'electric-furnace': [3,3],
            'stone-furnace': [2,2], 'steel-furnace': [2,2], 'lab': [3,3],
            'big-electric-pole': [2,2], 'substation': [2,2],
            'small-electric-pole': [1,1], 'medium-electric-pole': [1,1],
            'splitter': [2,1], 'fast-splitter': [2,1], 'express-splitter': [2,1],
            'rocket-silo': [9,9], 'centrifuge': [3,3], 'beacon': [3,3],
        };

        function getColor(name) {
            if (name.includes('assembling') || name.includes('chemical') || name.includes('refinery'))
                return '#60a5fa';
            if (name.includes('furnace')) return '#4ade80';
            if (name.includes('pole') || name.includes('substation')) return '#fbbf24';
            if (name.includes('inserter')) return '#f472b6';
            if (name.includes('splitter')) return '#a78bfa';
            if (name.includes('belt') || name.includes('underground')) return '#fbbf24';
            if (name.includes('chest')) return '#94a3b8';
            return '#64748b';
        }

        function getSize(name) {
            return ENTITY_SIZES[name] || [1, 1];
        }

        function renderMotifSVG(entities, tile) {
            if (!entities || !entities.length) return '<svg viewBox="0 0 100 50"></svg>';
            const TILE = tile || 20;
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            for (const e of entities) {
                const [w, h] = getSize(e.entity_type);
                minX = Math.min(minX, e.x - w/2);
                minY = Math.min(minY, e.y - h/2);
                maxX = Math.max(maxX, e.x + w/2);
                maxY = Math.max(maxY, e.y + h/2);
            }
            const pad = 1;
            minX -= pad; minY -= pad; maxX += pad; maxY += pad;
            const svgW = (maxX - minX) * TILE;
            const svgH = (maxY - minY) * TILE;
            let rects = '';
            for (const e of entities) {
                const [w, h] = getSize(e.entity_type);
                const px = (e.x - w/2 - minX) * TILE;
                const py = (e.y - h/2 - minY) * TILE;
                const color = getColor(e.entity_type);
                rects += `<rect x="${px}" y="${py}" width="${w*TILE-2}" height="${h*TILE-2}" `
                    + `rx="2" fill="${color}" opacity="0.85"><title>${e.entity_type}</title></rect>`;
            }
            return `<svg viewBox="0 0 ${svgW} ${svgH}" height="${Math.min(svgH, 200)}">${rects}</svg>`;
        }

        function badgeClass(cat) {
            return 'badge badge-' + (cat || 'simple').toLowerCase();
        }

        async function loadMotifs() {
            try {
                const resp = await fetch('/v1/motifs?per_page=100');
                const json = await resp.json();
                const motifs = json.data || [];
                motifs.sort((a, b) => (b.occurrence_count || 0) - (a.occurrence_count || 0));
                _motifs = motifs;
                document.getElementById('loading').style.display = 'none';
                const grid = document.getElementById('motif-grid');
                for (const m of motifs) {
                    const card = document.createElement('div');
                    card.className = 'motif-card';
                    const idx = motifs.indexOf(m);
                    card.innerHTML = `
                        <div class="card-actions">
                            <button class="card-btn" onclick="expandMotif(${idx})">Expand</button>
                            <button class="card-btn" onclick="copyId(this, '${m.id}')">Copy ID</button>
                        </div>
                        <h3><span class="${badgeClass(m.category)}">${m.category || 'SIMPLE'}</span>
                            ${m.canonical_hash ? m.canonical_hash.slice(0, 12) : ''}...</h3>
                        <div class="meta">${m.occurrence_count || 0} occurrences
                            &middot; ${m.entity_count || 0} entities</div>
                        ${renderMotifSVG(m.canonical_entities)}`;
                    grid.appendChild(card);
                }
            } catch (err) {
                document.getElementById('loading').textContent = 'Failed to load motifs: ' + err.message;
            }
        }
        let _motifs = [];
        function copyId(btn, id) {
            navigator.clipboard.writeText(id).then(() => {
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => { btn.textContent = 'Copy ID'; btn.classList.remove('copied'); }, 1500);
            });
        }
        function expandMotif(idx) {
            const m = _motifs[idx];
            if (!m) return;
            const body = document.getElementById('modal-body');
            body.innerHTML = `
                <h3><span class="${badgeClass(m.category)}">${m.category || 'SIMPLE'}</span>
                    ${m.canonical_hash || ''}</h3>
                <div class="meta">${m.occurrence_count || 0} occurrences &middot; ${m.entity_count || 0} entities &middot; ID: ${m.id}</div>
                ${renderMotifSVG(m.canonical_entities, 80)}`;
            document.getElementById('modal').classList.add('active');
        }
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        loadMotifs();
    </script>
</body>
</html>"""


@app.get("/blueprints/browse", response_class=HTMLResponse, include_in_schema=False)
async def blueprint_browser():
    """Interactive blueprint browser."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greenprint — Blueprint Browser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17; color: #c8d6e5; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a2332 0%, #0d1821 100%);
            border-bottom: 1px solid #1e3a5f; padding: 1.5rem 0; text-align: center; }
        .header h1 { color: #4ade80; font-size: 1.5rem; }
        .header p { color: #7f8c9b; margin-top: 0.3rem; font-size: 0.85rem; }
        .nav { text-align: center; padding: 0.75rem 0; background: #0d1117; border-bottom: 1px solid #1e2d3d; }
        .nav a { color: #7f8c9b; text-decoration: none; font-size: 0.8rem; margin: 0 1rem;
            transition: color 0.15s; }
        .nav a:hover, .nav a.active { color: #4ade80; }
        .container { max-width: 1200px; margin: 1.5rem auto; padding: 0 1.5rem; }
        .bp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1rem; }
        .bp-card { background: #111927; border: 1px solid #1e2d3d; border-radius: 8px; padding: 1rem;
            cursor: pointer; transition: border-color 0.2s, background 0.2s; text-decoration: none;
            display: block; color: inherit; }
        .bp-card:hover { border-color: #4ade80; background: #162030; }
        .bp-card h3 { color: #e2e8f0; font-size: 0.85rem; margin-bottom: 0.4rem; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; }
        .bp-card .meta { color: #7f8c9b; font-size: 0.75rem; margin-bottom: 0.5rem; }
        .bp-card .products { margin-top: 0.5rem; }
        .bp-card .product-tag { display: inline-block; font-size: 0.65rem; background: #1a2a3a;
            color: #60a5fa; padding: 2px 6px; border-radius: 3px; margin: 2px 2px 0 0; }
        .bp-card .input-tag { display: inline-block; font-size: 0.65rem; background: #2a1a2a;
            color: #f472b6; padding: 2px 6px; border-radius: 3px; margin: 2px 2px 0 0; }
        .flag-tag { display: inline-block; font-size: 0.6rem; font-weight: 700; padding: 2px 5px;
            border-radius: 3px; margin-right: 3px; }
        .flag-HIGH { background: #3a1a1a; color: #f87171; }
        .flag-MEDIUM { background: #3a2a1a; color: #f59e0b; }
        .flag-LOW { background: #1a2a3a; color: #60a5fa; }
        .flag-INFO { background: #1a2a1a; color: #4ade80; }
        .pagination { display: flex; justify-content: center; gap: 0.5rem; margin: 1.5rem 0; }
        .page-btn { background: #1e2d3d; border: 1px solid #2d3d4d; color: #c8d6e5; padding: 6px 14px;
            border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
        .page-btn:hover { background: #2d3d4d; }
        .page-btn.active { background: #4ade80; color: #0a0e17; border-color: #4ade80; }
        .page-btn:disabled { opacity: 0.4; cursor: default; }
        #loading { text-align: center; padding: 3rem; color: #7f8c9b; }
        .stats-bar { text-align: center; color: #7f8c9b; font-size: 0.8rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Blueprint Browser</h1>
        <p>Browse analysed Factorio 1.1 blueprints</p>
    </div>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/blueprints/browse" class="active">Blueprints</a>
        <a href="/motifs/browse">Motifs</a>
    </div>
    <div class="container">
        <div id="stats" class="stats-bar"></div>
        <div id="loading">Loading blueprints...</div>
        <div id="bp-grid" class="bp-grid"></div>
        <div id="pagination" class="pagination"></div>
    </div>
    <script>
        let currentPage = 1;
        const perPage = 30;

        function flagClass(severity) { return 'flag-tag flag-' + (severity || 'INFO'); }

        async function loadBlueprints(page) {
            currentPage = page;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('bp-grid').innerHTML = '';
            try {
                const resp = await fetch(`/v1/blueprints?page=${page}&per_page=${perPage}`);
                const json = await resp.json();
                const bps = json.data || [];
                const total = json.meta?.total || 0;
                const totalPages = Math.ceil(total / perPage);
                document.getElementById('stats').textContent = `${total} blueprints total`;
                document.getElementById('loading').style.display = 'none';
                const grid = document.getElementById('bp-grid');
                for (const bp of bps) {
                    const card = document.createElement('a');
                    card.className = 'bp-card';
                    card.href = `/blueprints/${bp.id}`;
                    const cg = bp.summary?.crafting_graph || {};
                    const finals = (cg.final_products || []).slice(0, 6);
                    const raws = (cg.raw_inputs || []).slice(0, 4);
                    const flags = (bp.flags || []).filter(f => f.severity === 'HIGH' || f.severity === 'MEDIUM');
                    let flagsHtml = flags.map(f =>
                        `<span class="${flagClass(f.severity)}">${f.flag}</span>`
                    ).join('');
                    let productsHtml = finals.map(p =>
                        `<span class="product-tag">${p}</span>`
                    ).join('');
                    if ((cg.final_products || []).length > 6)
                        productsHtml += `<span class="product-tag">+${cg.final_products.length - 6}</span>`;
                    let inputsHtml = raws.map(r =>
                        `<span class="input-tag">${r}</span>`
                    ).join('');

                    card.innerHTML = `
                        <h3>${bp.game_version || 'unknown'} &mdash; ${bp.id.slice(0, 8)}...</h3>
                        <div class="meta">
                            ${bp.source_site || ''} &middot;
                            ${bp.scraped_at ? new Date(bp.scraped_at).toLocaleDateString() : ''}
                            ${flagsHtml ? ' &middot; ' + flagsHtml : ''}
                        </div>
                        <div class="products">
                            ${productsHtml ? '<strong style="font-size:0.65rem;color:#60a5fa;">Products:</strong> ' + productsHtml : ''}
                            ${inputsHtml ? '<br><strong style="font-size:0.65rem;color:#f472b6;">Inputs:</strong> ' + inputsHtml : ''}
                        </div>`;
                    grid.appendChild(card);
                }
                renderPagination(totalPages);
            } catch (err) {
                document.getElementById('loading').textContent = 'Failed to load: ' + err.message;
            }
        }

        function renderPagination(totalPages) {
            const div = document.getElementById('pagination');
            div.innerHTML = '';
            if (totalPages <= 1) return;
            const prev = document.createElement('button');
            prev.className = 'page-btn'; prev.textContent = 'Prev';
            prev.disabled = currentPage <= 1;
            prev.onclick = () => loadBlueprints(currentPage - 1);
            div.appendChild(prev);
            const start = Math.max(1, currentPage - 3);
            const end = Math.min(totalPages, currentPage + 3);
            for (let i = start; i <= end; i++) {
                const btn = document.createElement('button');
                btn.className = 'page-btn' + (i === currentPage ? ' active' : '');
                btn.textContent = i;
                btn.onclick = () => loadBlueprints(i);
                div.appendChild(btn);
            }
            const next = document.createElement('button');
            next.className = 'page-btn'; next.textContent = 'Next';
            next.disabled = currentPage >= totalPages;
            next.onclick = () => loadBlueprints(currentPage + 1);
            div.appendChild(next);
        }
        loadBlueprints(1);
    </script>
</body>
</html>"""


@app.get("/blueprints/{blueprint_id}", response_class=HTMLResponse, include_in_schema=False)
async def blueprint_detail_page(blueprint_id: str):
    """Blueprint detail page showing associated motifs."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Greenprint — Blueprint Detail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e17; color: #c8d6e5; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a2332 0%, #0d1821 100%);
            border-bottom: 1px solid #1e3a5f; padding: 1.5rem 0; text-align: center; }
        .header h1 { color: #4ade80; font-size: 1.5rem; }
        .header p { color: #7f8c9b; margin-top: 0.3rem; font-size: 0.85rem; }
        .nav { text-align: center; padding: 0.75rem 0; background: #0d1117; border-bottom: 1px solid #1e2d3d; }
        .nav a { color: #7f8c9b; text-decoration: none; font-size: 0.8rem; margin: 0 1rem;
            transition: color 0.15s; }
        .nav a:hover { color: #4ade80; }
        .container { max-width: 1200px; margin: 1.5rem auto; padding: 0 1.5rem; }
        .info-panel { background: #111927; border: 1px solid #1e2d3d; border-radius: 8px;
            padding: 1.25rem; margin-bottom: 1.5rem; }
        .info-panel h2 { color: #e2e8f0; font-size: 1rem; margin-bottom: 0.75rem; }
        .info-row { display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
        .info-label { color: #7f8c9b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }
        .info-value { color: #e2e8f0; font-size: 0.85rem; margin-top: 2px; }
        .tag { display: inline-block; font-size: 0.65rem; padding: 2px 6px; border-radius: 3px;
            margin: 2px 2px 0 0; }
        .tag-product { background: #1a2a3a; color: #60a5fa; }
        .tag-input { background: #2a1a2a; color: #f472b6; }
        .tag-intermediate { background: #1a2a1a; color: #4ade80; }
        .flag-tag { display: inline-block; font-size: 0.6rem; font-weight: 700; padding: 2px 5px;
            border-radius: 3px; margin-right: 3px; }
        .flag-HIGH { background: #3a1a1a; color: #f87171; }
        .flag-MEDIUM { background: #3a2a1a; color: #f59e0b; }
        .flag-LOW { background: #1a2a3a; color: #60a5fa; }
        .flag-INFO { background: #1a2a1a; color: #4ade80; }
        .section-title { color: #4ade80; font-size: 0.85rem; text-transform: uppercase;
            letter-spacing: 1.5px; margin: 1.5rem 0 1rem; padding-bottom: 0.5rem;
            border-bottom: 1px solid #1e2d3d; }
        .motif-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
        .motif-card { background: #111927; border: 1px solid #1e2d3d; border-radius: 8px;
            padding: 1rem; position: relative; }
        .motif-card h3 { color: #e2e8f0; font-size: 0.85rem; margin-bottom: 0.5rem; }
        .motif-card .meta { color: #7f8c9b; font-size: 0.75rem; margin-bottom: 0.75rem; }
        .motif-card svg { background: #0d1117; border-radius: 4px; width: 100%; }
        .badge { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 2px 6px;
            border-radius: 3px; margin-right: 4px; }
        .badge-direct { background: #3a2a1a; color: #f59e0b; }
        .badge-simple { background: #1a3a2a; color: #4ade80; }
        .badge-underground { background: #2a1a3a; color: #a78bfa; }
        .badge-split { background: #1a2a3a; color: #60a5fa; }
        .badge-merged { background: #3a1a2a; color: #f472b6; }
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8);
            z-index: 100; justify-content: center; align-items: center; }
        .modal-overlay.active { display: flex; }
        .modal-content { background: #111927; border: 1px solid #1e3a5f; border-radius: 12px;
            padding: 1.5rem; max-width: 90vw; max-height: 90vh; position: relative; }
        .modal-content h3 { color: #e2e8f0; font-size: 1.1rem; margin-bottom: 0.5rem; }
        .modal-content .meta { color: #7f8c9b; font-size: 0.85rem; margin-bottom: 1rem; }
        .modal-content svg { background: #0d1117; border-radius: 6px; width: 100%; max-height: 70vh; }
        .modal-close { position: absolute; top: 0.75rem; right: 0.75rem; background: #1e2d3d;
            border: 1px solid #2d3d4d; color: #c8d6e5; font-size: 1.2rem; width: 28px; height: 28px;
            border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .modal-close:hover { background: #2d3d4d; }
        .card-actions { position: absolute; top: 0.5rem; right: 0.5rem; display: flex; gap: 4px; z-index: 1; }
        .card-btn { background: #1e2d3d; border: 1px solid #2d3d4d; color: #7f8c9b; font-size: 0.7rem;
            padding: 3px 8px; border-radius: 4px; cursor: pointer; transition: all 0.15s; }
        .card-btn:hover { background: #2d3d4d; color: #e2e8f0; }
        .no-motifs { text-align: center; padding: 2rem; color: #7f8c9b; font-size: 0.9rem; }
        .bp-svg-container { background: #0d1117; border: 1px solid #1e2d3d; border-radius: 8px;
            padding: 1rem; margin-bottom: 1.5rem; overflow: auto; text-align: center; }
        .bp-svg-container svg { max-width: 100%; border-radius: 4px; }
        .bp-entity-count { color: #7f8c9b; font-size: 0.75rem; margin-top: 0.5rem; }
        #loading { text-align: center; padding: 3rem; color: #7f8c9b; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Blueprint Detail</h1>
        <p id="bp-subtitle"></p>
    </div>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/blueprints/browse">Blueprints</a>
        <a href="/motifs/browse">Motifs</a>
    </div>
    <div class="container">
        <div id="loading">Loading blueprint...</div>
        <div id="content" style="display:none">
            <div id="info-panel" class="info-panel"></div>
            <h2 class="section-title">Blueprint Layout</h2>
            <div id="blueprint-svg" class="bp-svg-container"></div>
            <h2 class="section-title">Motifs in this Blueprint</h2>
            <div id="motif-grid" class="motif-grid"></div>
            <div id="no-motifs" class="no-motifs" style="display:none">No motifs found for this blueprint.</div>
        </div>
    </div>
    <div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>
    <script>
        const ENTITY_SIZES = {
            'assembling-machine-1': [3,3], 'assembling-machine-2': [3,3], 'assembling-machine-3': [3,3],
            'chemical-plant': [3,3], 'oil-refinery': [5,5], 'electric-furnace': [3,3],
            'stone-furnace': [2,2], 'steel-furnace': [2,2], 'lab': [3,3],
            'big-electric-pole': [2,2], 'substation': [2,2],
            'small-electric-pole': [1,1], 'medium-electric-pole': [1,1],
            'splitter': [2,1], 'fast-splitter': [2,1], 'express-splitter': [2,1],
            'rocket-silo': [9,9], 'centrifuge': [3,3], 'beacon': [3,3],
        };
        function getColor(name) {
            if (name.includes('assembling') || name.includes('chemical') || name.includes('refinery')) return '#60a5fa';
            if (name.includes('furnace')) return '#4ade80';
            if (name.includes('pole') || name.includes('substation')) return '#fbbf24';
            if (name.includes('inserter')) return '#f472b6';
            if (name.includes('splitter')) return '#a78bfa';
            if (name.includes('belt') || name.includes('underground')) return '#fbbf24';
            if (name.includes('chest')) return '#94a3b8';
            return '#64748b';
        }
        function getSize(name) { return ENTITY_SIZES[name] || [1, 1]; }
        function renderMotifSVG(entities, tile) {
            if (!entities || !entities.length) return '<svg viewBox="0 0 100 50"></svg>';
            const TILE = tile || 20;
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            for (const e of entities) {
                const [w, h] = getSize(e.entity_type);
                minX = Math.min(minX, e.x - w/2); minY = Math.min(minY, e.y - h/2);
                maxX = Math.max(maxX, e.x + w/2); maxY = Math.max(maxY, e.y + h/2);
            }
            const pad = 1; minX -= pad; minY -= pad; maxX += pad; maxY += pad;
            const svgW = (maxX - minX) * TILE, svgH = (maxY - minY) * TILE;
            let rects = '';
            for (const e of entities) {
                const [w, h] = getSize(e.entity_type);
                const px = (e.x - w/2 - minX) * TILE, py = (e.y - h/2 - minY) * TILE;
                const color = getColor(e.entity_type);
                rects += `<rect x="${px}" y="${py}" width="${w*TILE-2}" height="${h*TILE-2}" rx="2" fill="${color}" opacity="0.85"><title>${e.entity_type}</title></rect>`;
            }
            return `<svg viewBox="0 0 ${svgW} ${svgH}" height="${Math.min(svgH, 200)}">${rects}</svg>`;
        }
        function renderBlueprintSVG(decodedJson) {
            const bp = decodedJson?.blueprint;
            if (!bp || !bp.entities || !bp.entities.length) return '<div class="no-motifs">No entity data available</div>';
            const entities = bp.entities;
            const TILE = 8;
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            for (const e of entities) {
                const [w, h] = getSize(e.name);
                const ex = e.position.x, ey = e.position.y;
                minX = Math.min(minX, ex - w/2); minY = Math.min(minY, ey - h/2);
                maxX = Math.max(maxX, ex + w/2); maxY = Math.max(maxY, ey + h/2);
            }
            const pad = 1; minX -= pad; minY -= pad; maxX += pad; maxY += pad;
            const svgW = (maxX - minX) * TILE, svgH = (maxY - minY) * TILE;
            let rects = '';
            for (const e of entities) {
                const [w, h] = getSize(e.name);
                const px = (e.position.x - w/2 - minX) * TILE;
                const py = (e.position.y - h/2 - minY) * TILE;
                const color = getColor(e.name);
                rects += `<rect x="${px}" y="${py}" width="${w*TILE-1}" height="${h*TILE-1}" rx="1" fill="${color}" opacity="0.85"><title>${e.name} (${e.position.x}, ${e.position.y})</title></rect>`;
            }
            const maxH = Math.min(svgH, 500);
            return `<svg viewBox="0 0 ${svgW} ${svgH}" height="${maxH}" style="background:#0a0e17">${rects}</svg>`
                + `<div class="bp-entity-count">${entities.length} entities</div>`;
        }
        function badgeClass(cat) { return 'badge badge-' + (cat || 'simple').toLowerCase(); }

        const bpId = window.location.pathname.split('/').pop();
        let _motifDetails = [];

        async function loadBlueprint() {
            try {
                // Fetch blueprint detail and motifs in parallel
                const [bpResp, motifsResp] = await Promise.all([
                    fetch('/v1/blueprints/' + bpId),
                    fetch('/v1/blueprints/' + bpId + '/motifs'),
                ]);
                const bpJson = await bpResp.json();
                const motifsJson = await motifsResp.json();
                const bp = bpJson.data;
                const motifLinks = motifsJson.data || [];

                if (!bp) { document.getElementById('loading').textContent = 'Blueprint not found.'; return; }

                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                document.getElementById('bp-subtitle').textContent = bp.id;

                // Info panel
                const cg = bp.summary?.crafting_graph || {};
                const flags = bp.flags || [];
                let flagsHtml = flags.map(f =>
                    `<span class="flag-tag flag-${f.severity}">${f.flag}</span>`
                ).join(' ');
                let productsHtml = (cg.final_products || []).map(p =>
                    `<span class="tag tag-product">${p}</span>`
                ).join('');
                let inputsHtml = (cg.raw_inputs || []).map(r =>
                    `<span class="tag tag-input">${r}</span>`
                ).join('');
                let intermediatesHtml = (cg.intermediates || []).map(i =>
                    `<span class="tag tag-intermediate">${i}</span>`
                ).join('');

                document.getElementById('info-panel').innerHTML = `
                    <h2>Blueprint ${bp.id.slice(0, 12)}...</h2>
                    <div class="info-row">
                        <div><div class="info-label">Version</div><div class="info-value">${bp.game_version || 'unknown'}</div></div>
                        <div><div class="info-label">Source</div><div class="info-value">${bp.source_site || 'unknown'}</div></div>
                        <div><div class="info-label">Scraped</div><div class="info-value">${bp.scraped_at ? new Date(bp.scraped_at).toLocaleDateString() : 'unknown'}</div></div>
                        <div><div class="info-label">Self-Contained</div><div class="info-value">${cg.is_self_contained ? 'Yes' : 'No'}</div></div>
                        <div><div class="info-label">Has Cycle</div><div class="info-value">${cg.has_cycle ? 'Yes' : 'No'}</div></div>
                    </div>
                    ${flagsHtml ? '<div style="margin-top:0.5rem">' + flagsHtml + '</div>' : ''}
                    ${productsHtml ? '<div style="margin-top:0.75rem"><span class="info-label">Final Products</span><br>' + productsHtml + '</div>' : ''}
                    ${inputsHtml ? '<div style="margin-top:0.5rem"><span class="info-label">Raw Inputs</span><br>' + inputsHtml + '</div>' : ''}
                    ${intermediatesHtml ? '<div style="margin-top:0.5rem"><span class="info-label">Intermediates</span><br>' + intermediatesHtml + '</div>' : ''}
                    ${bp.source_url ? '<div style="margin-top:0.75rem"><a href="' + bp.source_url + '" target="_blank" style="color:#60a5fa;font-size:0.8rem;">View Source</a></div>' : ''}
                `;

                // Render blueprint SVG
                document.getElementById('blueprint-svg').innerHTML = renderBlueprintSVG(bp.decoded_json);

                // Fetch full motif details for rendering
                if (motifLinks.length === 0) {
                    document.getElementById('no-motifs').style.display = 'block';
                    return;
                }

                const motifIds = [...new Set(motifLinks.map(l => l.motif_id))];
                const motifFetches = motifIds.map(id => fetch('/v1/motifs/' + id).then(r => r.json()));
                const motifResults = await Promise.all(motifFetches);
                const motifMap = {};
                for (const r of motifResults) {
                    if (r.data) motifMap[r.data.id] = r.data;
                }

                _motifDetails = motifIds.map(id => motifMap[id]).filter(Boolean);
                const grid = document.getElementById('motif-grid');
                for (let i = 0; i < _motifDetails.length; i++) {
                    const m = _motifDetails[i];
                    const count = motifLinks.filter(l => l.motif_id === m.id).length;
                    const card = document.createElement('div');
                    card.className = 'motif-card';
                    card.innerHTML = `
                        <div class="card-actions">
                            <button class="card-btn" onclick="expandMotif(${i})">Expand</button>
                        </div>
                        <h3><span class="${badgeClass(m.category)}">${m.category || 'SIMPLE'}</span>
                            ${m.canonical_hash ? m.canonical_hash.slice(0, 12) : ''}...</h3>
                        <div class="meta">${count > 1 ? count + 'x in this blueprint &middot; ' : ''}${m.occurrence_count || 0} total occurrences
                            &middot; ${m.entity_count || 0} entities</div>
                        ${renderMotifSVG(m.canonical_entities)}`;
                    grid.appendChild(card);
                }
            } catch (err) {
                document.getElementById('loading').textContent = 'Failed to load: ' + err.message;
            }
        }
        function expandMotif(idx) {
            const m = _motifDetails[idx];
            if (!m) return;
            document.getElementById('modal-body').innerHTML = `
                <h3><span class="${badgeClass(m.category)}">${m.category || 'SIMPLE'}</span>
                    ${m.canonical_hash || ''}</h3>
                <div class="meta">${m.occurrence_count || 0} occurrences &middot; ${m.entity_count || 0} entities &middot; ID: ${m.id}</div>
                ${renderMotifSVG(m.canonical_entities, 80)}`;
            document.getElementById('modal').classList.add('active');
        }
        function closeModal() { document.getElementById('modal').classList.remove('active'); }
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        loadBlueprint();
    </script>
</body>
</html>"""


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content=envelope(None, error="Rate limit exceeded. Try again later."),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=envelope(None, error="Internal server error"),
    )
