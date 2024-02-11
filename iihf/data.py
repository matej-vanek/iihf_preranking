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


def load_data(path: str) -> pd.DataFrame:
    """Load data of participants, events and placements"""
    raw_data = pd.read_excel(path, sheet_name=None, engine="odf")
    events = {}
    for sheet_name, sheet_data in raw_data.items():
        if sheet_name == "participants":
            load_participants_sheet(sheet_data)
        else:
            events = load_event(events, sheet_name, sheet_data)

    return process_events(events)


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
        placement_dict[participant] = Placement(row["rank"])
    events[event] = placement_dict
    return events


def process_events(events: EventsType) -> pd.DataFrame:
    """Group events into superevents and produce final dataframe"""
    superevent_data = {}
    for year in {event.year for event in events}:
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

    return pd.concat(superevent_data, axis=1)


data = load_data("iihf/data.ods")
print(data.to_string())
