"""Minimal CLI for IIHF ranking tool."""

import argparse
from pathlib import Path

from iihf.data import load_data
from iihf.objects import Participant


def get_historical_team_name(series_participant, placement):
    """Get the historically accurate team name for the given placement, using event participant if available."""
    # If there's an event participant code, use that for the name
    if placement.event_participant_code:
        event_participant = Participant.get_participant(placement.event_participant_code)
        if event_participant:
            return event_participant.name_en
    
    # Fall back to the series participant name
    return series_participant.name_en


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
            team_name = get_historical_team_name(participant, placement)
            print(f"{placement.four_year_rank:4d} | {team_name:15s} | {placement.four_year_points}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main() 