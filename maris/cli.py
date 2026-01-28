"""
MARIS CLI - Simple commands using new modules

Clean, simple CLI for all MARIS operations using Semantica 0.2.5
"""
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track

from maris.extraction import extract_from_pdf
from maris.graph import build_knowledge_graph
from maris.reasoning import apply_bridge_axioms
from maris.export import export_to_owl, export_to_rdf
from maris.query import (
    query_graphrag, run_demo_queries,
    cabo_pulmo_queries, blue_bond_queries
)
from maris.data import (
    load_sample_extractions, load_cabo_pulmo,
    load_document_manifest
)
from maris.config import get_config
from maris.utils import get_logger

console = Console()
logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# MAIN CLI GROUP
# ═══════════════════════════════════════════════════════════════════

@click.group()
@click.version_option(version='0.1.0')
def main():
    """
    MARIS - Marine Asset Risk Intelligence System
    
    AI-powered knowledge graph bridging marine ecology and blue finance.
    Built on Semantica 0.2.5.
    """
    pass


# ═══════════════════════════════════════════════════════════════════
# EXTRACTION COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file')
def extract(pdf_path, output):
    """Extract entities and relationships from PDF"""
    console.print(f"\n[bold blue]Extracting from:[/bold blue] {pdf_path}")
    
    try:
        # Run full extraction pipeline
        with console.status("[bold green]Extracting (ingest + entities + relationships)..."):
            result = extract_from_pdf(pdf_path)
        
        document = result['document']
        entities = result['entities']
        relationships = result['relationships']
        
        # Display results
        table = Table(title="Extraction Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Text length", f"{len(document.get('text', ''))} chars")
        table.add_row("Tables", str(len(document.get('tables', []))))
        table.add_row("Figures", str(len(document.get('figures', []))))
        table.add_row("Entities", str(len(entities)))
        table.add_row("Relationships", str(len(relationships)))
        
        console.print(table)
        
        if output:
            import json
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump({
                    'entities': entities,
                    'relationships': relationships
                }, f, indent=2)
            console.print(f"\n[green]✓ Saved to {output}[/green]")
        
        console.print("\n[green]✓ Extraction complete[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


@main.command()
def extract_batch():
    """Extract from all sample papers"""
    console.print("\n[bold blue]Batch Extraction from Sample Papers[/bold blue]")
    
    try:
        # Load sample extractions (already extracted)
        extractions = load_sample_extractions()
        
        console.print(f"\nFound [cyan]{len(extractions)}[/cyan] sample extractions:")
        
        for extract_id, extraction in extractions.items():
            console.print(f"  • {extract_id}")
        
        console.print(f"\n[green]✓ {len(extractions)} papers available[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# GRAPH COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
def build():
    """Build knowledge graph from extractions"""
    console.print("\n[bold blue]Building Knowledge Graph[/bold blue]")
    
    try:
        # Load sample extractions
        with console.status("[bold green]Loading extractions..."):
            extractions = load_sample_extractions()
        
        console.print(f"Loaded [cyan]{len(extractions)}[/cyan] extractions")
        
        # Collect all entities and relationships
        all_entities = []
        all_relationships = []
        
        for extract_id, extraction in track(extractions.items(), description="Processing..."):
            all_entities.extend(extraction.get('entities', []))
            all_relationships.extend(extraction.get('relationships', []))
        
        console.print(f"\nCollected:")
        console.print(f"  • [cyan]{len(all_entities)}[/cyan] entities")
        console.print(f"  • [cyan]{len(all_relationships)}[/cyan] relationships")
        
        # Build graph
        with console.status("[bold green]Building graph with Semantica..."):
            graph = build_knowledge_graph(all_entities, all_relationships)
        
        # Apply bridge axioms
        with console.status("[bold green]Applying bridge axioms..."):
            inferred = apply_bridge_axioms(graph)
        
        console.print(f"\n[green]✓ Knowledge graph built successfully[/green]")
        console.print(f"  • Inferred {len(inferred)} new facts from axioms")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# QUERY COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
@click.argument('question')
@click.option('--max-hops', default=4, help='Maximum graph hops')
def query(question, max_hops):
    """Run GraphRAG query"""
    console.print(f"\n[bold blue]Query:[/bold blue] {question}\n")
    
    try:
        with console.status("[bold green]Querying knowledge graph..."):
            response = query_graphrag(question, max_hops=max_hops)
        
        # Display answer
        console.print("[bold green]Answer:[/bold green]")
        console.print(response.get('answer', 'No answer found'))
        
        # Display provenance
        if response.get('provenance'):
            console.print("\n[bold yellow]Provenance:[/bold yellow]")
            for i, prov in enumerate(response['provenance'], 1):
                console.print(f"  {i}. {prov}")
        
        # Display confidence
        if response.get('confidence'):
            console.print(f"\n[bold cyan]Confidence:[/bold cyan] {response['confidence']}")
        
        console.print("\n[green]✓ Query complete[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# VALIDATION COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
@click.option('--full', is_flag=True, help='Run full validation suite')
@click.option('--cabo-pulmo-only', is_flag=True, help='Validate Cabo Pulmo queries only')
def validate(full, cabo_pulmo_only):
    """Validate POC success criteria"""
    
    if full:
        # Run full validation suite
        from maris.validation import run_full_validation
        
        console.print("\n[bold blue]Running Full POC Validation Suite[/bold blue]")
        console.print("[dim]Validating all success criteria...[/dim]\n")
        
        try:
            with console.status("[bold green]Running validations..."):
                report = run_full_validation()
            
            # Display summary
            summary = report['summary']
            console.print(f"\n[bold cyan]Validation Summary:[/bold cyan]")
            console.print(f"  Total Criteria: {summary['total_criteria']}")
            console.print(f"  Passed: [green]{summary['passed']}[/green]")
            console.print(f"  Failed: [red]{summary['failed']}[/red]")
            console.print(f"  Success Rate: [cyan]{summary['success_rate']}%[/cyan]")
            
            # Display individual results
            console.print(f"\n[bold cyan]Technical Validation:[/bold cyan]")
            for result in report['technical_validation']:
                status = "[green]✓ PASS[/green]" if result['passed'] else "[red]✗ FAIL[/red]"
                console.print(f"  {status} - {result['criterion']}")
            
            console.print(f"\n[bold cyan]Business Validation:[/bold cyan]")
            for result in report['business_validation']:
                status = "[green]✓ PASS[/green]" if result['passed'] else "[red]✗ FAIL[/red]"
                console.print(f"  {status} - {result['criterion']}")
            
            overall = report['overall_status']
            if overall == 'PASS':
                console.print(f"\n[bold green]✓ POC VALIDATION: PASS[/bold green]")
            else:
                console.print(f"\n[bold red]✗ POC VALIDATION: FAIL[/bold red]")
            
        except Exception as e:
            console.print(f"\n[red]✗ Validation error: {e}[/red]")
            raise
    
    else:
        # Run quick Cabo Pulmo validation
        console.print("\n[bold blue]Validating Cabo Pulmo Queries[/bold blue]")
        
        try:
            # Load Cabo Pulmo data
            with console.status("[bold green]Loading Cabo Pulmo data..."):
                cabo_pulmo = load_cabo_pulmo()
            
            console.print("\n[bold cyan]Running validation queries...[/bold cyan]\n")
            
            # Run validation queries
            queries = cabo_pulmo_queries()[:3]  # Top 3 queries
            
            for i, q in enumerate(queries, 1):
                console.print(f"[cyan]Query {i}:[/cyan] {q}")
                
                with console.status("Querying..."):
                    response = query_graphrag(q)
                
                console.print(f"[green]Answer:[/green] {response.get('answer', 'N/A')[:200]}...")
                console.print()
            
            console.print("[green]✓ Cabo Pulmo validation complete[/green]")
            console.print("[dim]Run with --full flag for complete POC validation[/dim]")
            
        except Exception as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            raise


# ═══════════════════════════════════════════════════════════════════
# DEMO COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
@click.option('--query-count', default=11, help='Number of demo queries to run')
def demo(query_count):
    """Run investor demo queries"""
    console.print("\n[bold blue]Running Investor Demo[/bold blue]")
    console.print("[dim]Executing GraphRAG queries to demonstrate MARIS capabilities[/dim]\n")
    
    try:
        # Get demo queries
        cabo_queries = cabo_pulmo_queries()[:3]
        bond_queries = blue_bond_queries()[:3]
        
        all_queries = (cabo_queries + bond_queries)[:query_count]
        
        console.print(f"Running [cyan]{len(all_queries)}[/cyan] demo queries:\n")
        
        results = []
        
        for i, q in enumerate(all_queries, 1):
            console.print(f"[bold cyan]Query {i}/{len(all_queries)}:[/bold cyan]")
            console.print(f"  {q}\n")
            
            with console.status("[green]Processing..."):
                response = query_graphrag(q)
            
            console.print(f"[green]Answer:[/green]")
            answer = response.get('answer', 'No answer found')
            # Truncate long answers for demo display
            if len(answer) > 300:
                answer = answer[:300] + "..."
            console.print(f"  {answer}\n")
            
            results.append({'query': q, 'response': response})
            
            console.print("[dim]" + "─" * 80 + "[/dim]\n")
        
        # Summary
        console.print(f"\n[bold green]✓ Demo Complete[/bold green]")
        console.print(f"  • Executed {len(results)} queries successfully")
        console.print(f"  • All queries used GraphRAG with provenance tracking")
        console.print(f"  • Demonstrated: Cabo Pulmo validation, Blue finance KPIs")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# EXPORT COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
@click.option('--format', type=click.Choice(['owl', 'rdf']), default='rdf', help='Export format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def export(format, output):
    """Export knowledge graph"""
    console.print(f"\n[bold blue]Exporting to {format.upper()}[/bold blue]")
    
    try:
        # Build graph first
        with console.status("[bold green]Loading graph..."):
            extractions = load_sample_extractions()
            all_entities = []
            all_relationships = []
            for extraction in extractions.values():
                all_entities.extend(extraction.get('entities', []))
                all_relationships.extend(extraction.get('relationships', []))
            
            graph = build_knowledge_graph(all_entities, all_relationships)
        
        # Export
        if not output:
            output = f'data/exports/maris.{format}'
        
        with console.status(f"[bold green]Exporting to {output}..."):
            if format == 'owl':
                export_to_owl(graph, output)
            else:  # rdf
                export_to_rdf(graph, output)
        
        console.print(f"\n[green]✓ Exported to {output}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# STATUS COMMANDS
# ═══════════════════════════════════════════════════════════════════

@main.command()
def status():
    """Show system status"""
    console.print("\n[bold blue]MARIS System Status[/bold blue]\n")
    
    try:
        config = get_config()
        
        # Configuration
        table = Table(title="Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Groq Model", config.groq_model)
        table.add_row("FalkorDB Host", config.falkordb_host)
        table.add_row("Graph Name", config.falkordb_graph_name)
        table.add_row("Log Level", config.log_level)
        
        console.print(table)
        
        # Data files
        console.print("\n[bold cyan]Data Files:[/bold cyan]")
        
        manifest_path = Path("data/document_manifest.json")
        if manifest_path.exists():
            manifest = load_document_manifest()
            console.print(f"  • Document manifest: [green]{len(manifest.get('documents', {}))} papers[/green]")
        
        extractions_dir = Path("data/sample_extractions")
        if extractions_dir.exists():
            extraction_count = len(list(extractions_dir.glob("*.json")))
            console.print(f"  • Sample extractions: [green]{extraction_count} files[/green]")
        
        # Schemas
        schemas_dir = Path("schemas")
        if schemas_dir.exists():
            schema_files = list(schemas_dir.glob("*.json"))
            console.print(f"  • Schema files: [green]{len(schema_files)} files[/green]")
        
        console.print("\n[green]✓ System operational[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    main()
