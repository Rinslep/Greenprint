"""Typer CLI entry points for Greenprint."""

from pathlib import Path

import typer

app = typer.Typer(name="greenprint", help="Factorio Blueprint Analyser")


@app.command()
def scrape(
    source: str = typer.Option(..., help="Source: factorioprints, reddit, forums"),
    limit: int = typer.Option(100, help="Max blueprints to scrape"),
):
    """Scrape blueprints from a community source."""
    from scraper import FactorioPrintsScraper, ForumsScraper, RedditScraper
    from storage.database import init_db, get_session
    from pipeline.orchestrator import process_string

    init_db()

    scrapers = {
        "factorioprints": FactorioPrintsScraper,
        "reddit": RedditScraper,
        "forums": ForumsScraper,
    }
    if source not in scrapers:
        typer.echo(f"Unknown source: {source}. Choose from: {', '.join(scrapers)}")
        raise typer.Exit(1)

    scraper = scrapers[source](limit=limit)

    def on_new(raw, source_url, source_site, author_raw):
        with get_session() as session:
            process_string(session, raw, source_url, source_site, author_raw)

    scraper._on_new_blueprint = on_new
    scraper.run()
    typer.echo(f"Scraped {scraper._processed_count} blueprints from {source}")


@app.command()
def ingest(
    file: Path = typer.Option(..., help="Path to file with blueprint strings (one per line)"),
):
    """Ingest blueprint strings from a file."""
    from storage.database import init_db, get_session
    from pipeline.orchestrator import process_string

    init_db()
    count = 0

    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            with get_session() as session:
                result = process_string(session, line, source_site="file_import")
                if result.success:
                    count += 1

    typer.echo(f"Ingested {count} blueprints from {file}")


@app.command()
def analyse(
    id: str = typer.Option(None, help="Blueprint ID to analyse"),
    all: bool = typer.Option(False, "--all", help="Re-analyse all blueprints"),
):
    """Run analysis on stored blueprints."""
    from storage.database import init_db, get_session
    import storage

    init_db()

    with get_session() as session:
        if id:
            bp = storage.get_blueprint(session, id)
            if bp:
                typer.echo(f"Blueprint {id}: {bp.game_version or 'unknown version'}")
                if bp.flags:
                    for flag in bp.flags:
                        typer.echo(f"  [{flag.get('severity')}] {flag.get('flag')}")
            else:
                typer.echo(f"Blueprint {id} not found")
        elif all:
            bps, total = storage.list_blueprints(session, limit=10000)
            typer.echo(f"Total blueprints: {total}")
        else:
            typer.echo("Specify --id or --all")


@app.command()
def review():
    """Print unresolved review queue items."""
    from storage.database import init_db, get_session
    import storage

    init_db()

    with get_session() as session:
        items, total = storage.list_review_queue(session)
        typer.echo(f"Unresolved review items: {total}")
        for item in items:
            typer.echo(
                f"  [{item.id[:8]}] blueprint={item.blueprint_id[:8]} "
                f"entity={item.entity_number}"
            )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
):
    """Start the FastAPI server."""
    import uvicorn
    uvicorn.run("api.main:app", host=host, port=port, reload=True)


@app.command()
def stats():
    """Print dataset statistics."""
    from storage.database import init_db, get_session
    import storage

    init_db()

    with get_session() as session:
        _, bp_total = storage.list_blueprints(session, limit=0)
        _, motif_total = storage.list_motifs(session, limit=0)
        items, review_total = storage.list_review_queue(session)

        typer.echo(f"Blueprints: {bp_total}")
        typer.echo(f"Motifs: {motif_total}")
        typer.echo(f"Unresolved reviews: {review_total}")


if __name__ == "__main__":
    app()
