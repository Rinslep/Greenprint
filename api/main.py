"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.dependencies import envelope
from api.v1 import v1_router

limiter = Limiter(key_func=get_remote_address)


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
            <a class="docs-link" href="/docs">Swagger UI</a>
            <span>&middot;</span>
            <a class="docs-link" href="/redoc" style="background:#3b82f6;">ReDoc</a>
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
