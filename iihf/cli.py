"""Minimal CLI for IIHF ranking tool."""

import argparse
from pathlib import Path

from iihf.data import load_data


def main():
    """Show IIHF rankings."""
    parser = argparse.ArgumentParser(description="Show IIHF rankings")
    parser.add_argument(
        "--data-file", "-d",
        type=Path,
        default="iihf/data.ods",
        help="Path to the data file (ODS format)"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        required=True,
        help="Specific year to show ranking for"
    )
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=20,
        help="Number of top teams to display"
    )
    
    args = parser.parse_args()
    
    try:
        # Load data
        data = load_data(str(args.data_file))
        
        # Find the superevent for the year
        superevent = None
        for col in data.columns:
            if col.year == args.year:
                superevent = col
                break
        
        if superevent is None:
            print(f"No ranking data available for year {args.year}")
            return
        
        # Get ranking data
        year_data = data[superevent]
        rankings = []
        
        for participant, placement in year_data.items():
            if placement.four_year_rank != float('inf'):
                rankings.append((participant, placement))
        
        # Sort by rank
        rankings.sort(key=lambda x: x[1].four_year_rank)
        
        # Display top teams
        print(f"IIHF World Ranking {args.year}")
        print("Rank | Team | Points")
        print("-" * 30)
        
        for participant, placement in rankings[:args.top]:
            print(f"{placement.four_year_rank:4d} | {participant.name_en:15s} | {placement.four_year_points}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main() 