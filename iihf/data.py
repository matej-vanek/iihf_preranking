import math
from typing import TypeAlias

import pandas as pd

from iihf.objects import Championship, Event, EventType, OlympicGames, Participant, Placement, process_placement_dicts

EventsType: TypeAlias = dict[Event, dict[Participant, Placement]]

EVENT_TYPE_MAPPING = {
    "DC": EventType.DEVELOPMENT_CUP,
    "EC": EventType.EUROPEAN_CHAMPIONSHIP,
    "SOG": EventType.SUMMER_OLYMPIC_GAMES,
    "TTT": EventType.THAYER_TRUTT_TROPHY,
    "WC": EventType.WORLD_CHAMPIONSHIP,
    "WOG": EventType.WINTER_OLYMPIC_GAMES,
}

LIMITS = {OlympicGames: 1, Championship: 4}
LIMIT_YEARS = 4


def load_data(path: str) -> pd.DataFrame:
    """Load data of participants, events and placements"""
    raw_data = pd.read_excel(path, sheet_name=None, engine="odf")
    events = {}
    for sheet_name, sheet_data in raw_data.items():
        if sheet_name == "participants":
            load_participants_sheet(sheet_data)
        else:
            events = load_event(events, sheet_name, sheet_data)

    processed_events = process_events(events)
    processed_data = process_four_years(processed_events)
    return processed_data


def load_participants_sheet(sheet_data: pd.DataFrame) -> None:
    """Load participants from their sheet"""
    for _, row in sheet_data.iterrows():
        Participant(row["code"], row["name_en"], row["name_cs"], row["parent"] or None)


def load_event(events: EventsType, sheet_name: str, sheet_data: pd.DataFrame) -> EventsType:
    """Load event and its placements from sheet"""
    year, event_type_key = tuple(sheet_name.split("_", maxsplit=1))
    event_type = EVENT_TYPE_MAPPING.get(event_type_key)
    event = Event(int(year), event_type)

    placement_dict = {}
    for _, row in sheet_data.iterrows():
        participant = Participant.get_participant(row["participant"])
        if participant in placement_dict:
            raise ValueError(f"duplicate placement for {participant} in {event}")
        if not pd.isnull(participant.parent):
            participant = Participant.get_participant(participant.parent)
        placement_dict[participant] = Placement(
            original_participant_code=row["participant"],
            superevent_rank=row["rank"],
            superevent_points=row.get("points"),
        )
    events[event] = placement_dict
    return events


def process_events(events: EventsType) -> pd.DataFrame:
    """Group events into superevents and produce final dataframe"""
    superevent_data = {}
    for year in sorted({event.year for event in events}):
        for superevent_type in (OlympicGames, Championship):
            matching_events = [
                (event, participant_placements)
                for event, participant_placements in events.items()
                if event.year == year and event.type_ in superevent_type.event_types
            ]
            matching_events = sorted(matching_events, key=lambda e_pp: e_pp[0].type_.value)
            if not matching_events:
                continue
            superevent = superevent_type(year)
            final_placement_dict = process_placement_dicts(
                [placement_dict for _event, placement_dict in matching_events]
            )

            superevent_data[superevent] = pd.Series(final_placement_dict.values(), index=final_placement_dict.keys())

    superevent_data = pd.concat(superevent_data, axis=1)

    return superevent_data


def process_four_years(data: pd.DataFrame) -> pd.DataFrame:
    """Fill points and rank for the ranking period"""
    for superevent_idx, (superevent, superevent_data) in enumerate(list(data.items())):
        processed_superevents = {OlympicGames: 0, Championship: 0}

        for backward in range(min(superevent_idx + 1, 5)):
            older_superevent, _older_superevent_data = list(list(data.items()))[superevent_idx - backward]
            if processed_superevents[type(older_superevent)] >= LIMITS[type(older_superevent)]:
                continue
            if superevent.year - older_superevent.year > LIMIT_YEARS:
                break

            processed_superevents[type(older_superevent)] += 1
            coef = max(0, 1 - 0.25 * older_superevent.whole_years_behind(superevent))

            for participant, older_placement in data[older_superevent].items():
                if pd.isnull(superevent_data[participant]):
                    superevent_data[participant] = Placement(None, math.inf)
                if pd.isnull(older_placement):
                    continue
                superevent_data[participant].four_year_points += int(coef * older_placement.superevent_points)

            if all(
                processed_count == LIMITS[superevent_type]
                for superevent_type, processed_count in processed_superevents.items()
            ):
                break

    for superevent in data:
        superevent_placements = [plac for plac in data[superevent].values if not pd.isnull(plac)]
        superevent_placements = sorted(superevent_placements, key=lambda plac: plac.get_four_year_rank_key)
        for i, placement in enumerate(superevent_placements):
            placement.four_year_rank = i + 1

    return data
