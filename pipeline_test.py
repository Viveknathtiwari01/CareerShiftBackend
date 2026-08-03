import time
import json
import traceback
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import services
from services import (
    role_understanding,
    competency_discovery,
    competency_structuring,
    competency_validation,
    competency_explanation
)

console = Console()

def print_section(title: str, input_data: Any, output_data: Any = None, error: str = None):
    console.print(f"\n[bold cyan]{'='*42}[/bold cyan]")
    console.print(f"[bold cyan]{title.upper()}[/bold cyan]")
    console.print(f"[bold cyan]{'='*42}[/bold cyan]")
    
    console.print("\n[bold yellow]INPUT[/bold yellow]")
    console.print(json.dumps(input_data, indent=2))
    
    if error:
        console.print("\n[bold red]ERROR[/bold red]")
        console.print(f"[red]{error}[/red]")
    elif output_data is not None:
        console.print("\n[bold green]OUTPUT[/bold green]")
        console.print(json.dumps(output_data, indent=2))

def run_pipeline():
    # 1. Sample User Profile
    user_profile = {
        "job_title": "Lead HRIS Analyst",
        "industry": "Professional & Business Services",
        "business_function": "Business Process Outsourcing",
        "domain": "Human Resources Process Outsourcing",
        "specialization": "HRIS Implementation & Management",
        "technical_skills": [
            "HRIS Implementation",
            "HR Data Management"
        ],
        "experience_years": 5
    }

    pipeline_output = {
        "input_profile": user_profile
    }

    # Tracking for dashboard
    dashboard_data = [
        {"name": "RoleUnderstandingService", "status": "PENDING", "time": 0.0},
        {"name": "CompetencyDiscoveryService", "status": "PENDING", "time": 0.0},
        {"name": "CompetencyStructuringService", "status": "PENDING", "time": 0.0},
        {"name": "CompetencyValidationService", "status": "PENDING", "time": 0.0},
        {"name": "CompetencyExplanationService", "status": "PENDING", "time": 0.0}
    ]

    total_start_time = time.time()
    
    # --------------------------------------------------
    # STEP 2: Role Understanding
    # --------------------------------------------------
    role_understanding_output = None
    try:
        start_time = time.time()
        role_understanding_output = role_understanding.run(user_profile)
        elapsed = time.time() - start_time
        
        dashboard_data[0]["status"] = "PASS"
        dashboard_data[0]["time"] = elapsed
        pipeline_output["role_understanding"] = role_understanding_output
        print_section("ROLE UNDERSTANDING", user_profile, role_understanding_output)
    except Exception as e:
        dashboard_data[0]["status"] = "FAIL"
        dashboard_data[0]["time"] = time.time() - start_time
        print_section("ROLE UNDERSTANDING", user_profile, error=traceback.format_exc())

    # --------------------------------------------------
    # STEP 3: Competency Discovery
    # --------------------------------------------------
    discovery_output = None
    if role_understanding_output:
        # Input for engine 2 is just the profession and functional areas
        discovery_input = {
            "profession": role_understanding_output.get("profession"),
            "functional_areas": role_understanding_output.get("functional_areas")
        }
        try:
            start_time = time.time()
            discovery_output = competency_discovery.run(discovery_input)
            elapsed = time.time() - start_time
            
            dashboard_data[1]["status"] = "PASS"
            dashboard_data[1]["time"] = elapsed
            pipeline_output["competency_discovery"] = discovery_output
            print_section("COMPETENCY DISCOVERY", discovery_input, discovery_output)
        except Exception as e:
            dashboard_data[1]["status"] = "FAIL"
            dashboard_data[1]["time"] = time.time() - start_time
            print_section("COMPETENCY DISCOVERY", discovery_input, error=traceback.format_exc())

    # --------------------------------------------------
    # STEP 4: Competency Structuring
    # --------------------------------------------------
    structuring_output = None
    if role_understanding_output and discovery_output:
        structuring_input = {
            "profession": role_understanding_output.get("profession"),
            "role_family": role_understanding_output.get("role_family"),
            "purpose": role_understanding_output.get("purpose"),
            "competencies": discovery_output
        }
        try:
            start_time = time.time()
            structuring_output = competency_structuring.run(structuring_input)
            elapsed = time.time() - start_time
            
            dashboard_data[2]["status"] = "PASS"
            dashboard_data[2]["time"] = elapsed
            pipeline_output["competency_structuring"] = structuring_output
            print_section("COMPETENCY STRUCTURING", structuring_input, structuring_output)
        except Exception as e:
            dashboard_data[2]["status"] = "FAIL"
            dashboard_data[2]["time"] = time.time() - start_time
            print_section("COMPETENCY STRUCTURING", structuring_input, error=traceback.format_exc())

    # --------------------------------------------------
    # STEP 5: Competency Validation
    # --------------------------------------------------
    validation_output = None
    if role_understanding_output and structuring_output:
        validation_input = {
            "profession": role_understanding_output.get("profession"),
            "purpose": role_understanding_output.get("purpose"),
            "functional_areas": role_understanding_output.get("functional_areas"),
            "competencies": structuring_output
        }
        try:
            start_time = time.time()
            validation_output = competency_validation.run(validation_input)
            elapsed = time.time() - start_time
            
            dashboard_data[3]["status"] = "PASS"
            dashboard_data[3]["time"] = elapsed
            pipeline_output["competency_validation"] = validation_output
            print_section("COMPETENCY VALIDATION", validation_input, validation_output)
        except Exception as e:
            dashboard_data[3]["status"] = "FAIL"
            dashboard_data[3]["time"] = time.time() - start_time
            print_section("COMPETENCY VALIDATION", validation_input, error=traceback.format_exc())

    # --------------------------------------------------
    # STEP 6: Competency Explanation
    # --------------------------------------------------
    explanation_output = None
    if role_understanding_output and validation_output:
        explanation_input = {
            "profession": role_understanding_output.get("profession"),
            "purpose": role_understanding_output.get("purpose"),
            "validated_competencies": validation_output.get("validated_competencies", [])
        }
        try:
            start_time = time.time()
            explanation_output = competency_explanation.run(explanation_input)
            elapsed = time.time() - start_time
            
            dashboard_data[4]["status"] = "PASS"
            dashboard_data[4]["time"] = elapsed
            pipeline_output["competency_explanation"] = explanation_output
            print_section("COMPETENCY EXPLANATION", explanation_input, explanation_output)
        except Exception as e:
            dashboard_data[4]["status"] = "FAIL"
            dashboard_data[4]["time"] = time.time() - start_time
            print_section("COMPETENCY EXPLANATION", explanation_input, error=traceback.format_exc())

    total_time = time.time() - total_start_time

    # --------------------------------------------------
    # STEP 7: Print pipeline summary
    # --------------------------------------------------
    console.print(f"\n[bold cyan]{'='*42}[/bold cyan]")
    console.print("[bold cyan]PIPELINE COMPLETE[/bold cyan]")
    console.print(f"[bold cyan]{'='*42}[/bold cyan]\n")
    
    for item in dashboard_data:
        icon = "[green]✓[/green]" if item["status"] == "PASS" else ("[red]✗[/red]" if item["status"] == "FAIL" else "[dim]○[/dim]")
        # Strip 'Service' from name for the checklist as requested
        friendly_name = item["name"].replace("Service", "")
        # Add spaces before capital letters
        friendly_name = ''.join([' ' + char if char.isupper() else char for char in friendly_name]).strip()
        console.print(f"{friendly_name} {icon}")

    # --------------------------------------------------
    # STEP 8: Save output
    # --------------------------------------------------
    with open("pipeline_output.json", "w", encoding="utf-8") as f:
        json.dump(pipeline_output, f, indent=4)
        
    # --------------------------------------------------
    # Dashboard
    # --------------------------------------------------
    console.print(f"\n[bold cyan]{'='*52}[/bold cyan]")
    console.print("[bold cyan]CAREERSHIFT AI PIPELINE REPORT[/bold cyan]")
    console.print(f"[bold cyan]{'='*52}[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Service", style="cyan", width=30)
    table.add_column("Status", width=10)
    table.add_column("Time", justify="right", width=10)
    
    for item in dashboard_data:
        status_color = "green" if item["status"] == "PASS" else ("red" if item["status"] == "FAIL" else "dim")
        table.add_row(
            item["name"], 
            f"[{status_color}]{item['status']}[/{status_color}]", 
            f"{item['time']:.1f}s" if item["status"] != "PENDING" else "-"
        )
        
    console.print(table)
    console.print(f"\n[dim]{'-'*52}[/dim]")
    console.print(f"Total Execution Time: [bold]{total_time:.1f} seconds[/bold]")
    console.print(f"[dim]{'-'*52}[/dim]")
    console.print("Output File: [bold]pipeline_output.json[/bold]")
    console.print(f"[bold cyan]{'='*52}[/bold cyan]\n")

if __name__ == "__main__":
    run_pipeline()
