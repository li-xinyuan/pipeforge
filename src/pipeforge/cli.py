import sys

import click

from pipeforge.core.engine import PipelineEngine


@click.group()
@click.version_option(version="0.1.0", prog_name="pipeforge")
def main():
    """PipeForge — CLI data pipeline framework."""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--param", "-p", "params", multiple=True, help="Runtime parameter in key=value format")
@click.option("--cleanup", is_flag=True, help="Remove temporary database after execution")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def run(config_path, params, cleanup, verbose):
    """Execute a pipeline from a YAML configuration file."""
    try:
        engine = PipelineEngine(config_path)
    except Exception as e:
        click.echo(f"Config error: {e}", err=True)
        sys.exit(1)

    required = engine.required_params()
    provided = {}
    for p in params:
        if "=" in p:
            key, value = p.split("=", 1)
            provided[key.strip()] = value.strip()

    missing = [r for r in required if r.key not in provided]
    if missing:
        click.echo(f"Pipeline: {engine.config.scene.name}")
        click.echo(f"Description: {engine.config.scene.description or 'N/A'}")
        click.echo()
        for r in missing:
            click.echo(f"  [{r.label}]")
            value = click.prompt(f"  Enter file path for '{r.label}' ({r.key})", type=str)
            provided[r.key] = value

    if verbose:
        click.echo(f"Executing pipeline: {engine.config.scene.name}")

    try:
        result = engine.execute(params=provided, cleanup=cleanup)
        _print_result(result)
    except Exception as e:
        click.echo(f"Pipeline error: {e}", err=True)
        sys.exit(1)


def _print_result(result):
    click.echo()
    click.echo("=== Pipeline Complete ===")
    for name, stats in result.inputs.items():
        click.echo(f"  Input [{name}]: {stats.rows_loaded} rows ({stats.elapsed_ms}ms)")
    for stats in result.processors:
        created = ", ".join(stats.tables_created) if stats.tables_created else "none"
        click.echo(f"  Processor [{stats.name}]: created tables: {created} ({stats.elapsed_ms}ms)")
    if result.output:
        click.echo(f"  Output: {result.output.rows_written} rows → {result.output.file_path} ({result.output.elapsed_ms}ms)")
