"""IIHF Ranking Flow Diagram Generator"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import patches
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

from iihf.data import load_data
from iihf.objects import Championship, OlympicGames, Participant


class RankingDiagramGenerator:
    """Generates IIHF ranking flow diagrams with flags and connecting lines"""

    def __init__(self, data_path: str = "iihf/data.ods", flags_dir: str = "iihf/flags"):
        self.data_path = data_path
        self.flags_dir = flags_dir
        self.data = None
        self.flag_cache = {}
        self._load_data()
        self._load_flag_mapping()

    def _load_data(self):
        """Load the IIHF data"""
        self.data = load_data(self.data_path)

    def _load_flag_mapping(self):
        """Create mapping of flag files to their year ranges"""
        self.flag_files = {}

        # Get all PNG files in flags directory
        flag_pattern = os.path.join(self.flags_dir, "*.png")
        flag_files = glob.glob(flag_pattern)

        for flag_file in flag_files:
            filename = os.path.basename(flag_file)
            name_without_ext = os.path.splitext(filename)[0]

            # Check if it's a year-specific flag
            if "_" in name_without_ext and name_without_ext.count("_") >= 2:
                # Format: name_year_from_year_to
                parts = name_without_ext.split("_")
                if len(parts) >= 3:
                    try:
                        year_from = int(parts[-2])
                        year_to = int(parts[-1])
                        base_name = "_".join(parts[:-2])
                        self.flag_files[(base_name, year_from, year_to)] = flag_file
                    except ValueError:
                        # Not a year-specific flag, treat as default
                        self.flag_files[(name_without_ext, None, None)] = flag_file
            else:
                # Default flag
                self.flag_files[(name_without_ext, None, None)] = flag_file

    def _get_flag_path(self, participant_name: str, year: int) -> str:
        """Get the appropriate flag path for a participant and year"""
        # First try to find year-specific flag
        year_specific_matches = []
        for (name, year_from, year_to), flag_path in self.flag_files.items():
            if name == participant_name and year_from is not None and year_to is not None:
                if year_from <= year <= year_to:
                    year_specific_matches.append(flag_path)

        if len(year_specific_matches) == 1:
            return year_specific_matches[0]
        if len(year_specific_matches) > 1:
            raise ValueError(
                f"Multiple year-specific flags match for {participant_name} in {year}: {year_specific_matches}"
            )

        # Try to find default flag
        default_flag = self.flag_files.get((participant_name, None, None))
        if default_flag:
            return default_flag

        raise ValueError(f"No flag found for participant '{participant_name}' in year {year}")

    def _load_and_resize_flag(self, flag_path: str, target_width: float, target_height: float) -> Image.Image:
        """Load and resize flag to target dimensions with 3:2 aspect ratio"""
        if flag_path in self.flag_cache:
            return self.flag_cache[flag_path]

        with Image.open(flag_path) as img:
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate dimensions maintaining 3:2 aspect ratio
            flag_ratio = 3 / 2
            current_ratio = img.width / img.height

            if current_ratio > flag_ratio:
                # Image is wider than 3:2, fit to height
                new_height = max(1, int(target_height))
                new_width = max(1, int(new_height * flag_ratio))
            else:
                # Image is taller than 3:2, fit to width
                new_width = max(1, int(target_width))
                new_height = max(1, int(new_width / flag_ratio))

            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.flag_cache[flag_path] = resized_img
            return resized_img

    def _make_flag_lighter(self, flag_img: Image.Image) -> Image.Image:
        """Make flag colors three times lighter by blending with white"""
        # Create a white image of the same size
        white_img = Image.new("RGB", flag_img.size, (255, 255, 255))

        # Blend the flag with white (25% flag, 75% white)
        lighter_flag = Image.blend(flag_img, white_img, 0.75)

        return lighter_flag

    def _should_use_lighter_colors(self, participant_name: str, superevent, placement, base_use_lighter: bool) -> bool:
        """Determine if a flag should use lighter colors based on special bleaching rules"""
        use_lighter_colors = base_use_lighter

        # Russia and Belarus in years 2022-2026
        if participant_name in ["Russia", "Belarus"]:
            if (isinstance(superevent, OlympicGames) and 2023 <= superevent.year <= 2026) or (
                isinstance(superevent, Championship) and 2022 <= superevent.year <= 2026
            ):
                use_lighter_colors = True

        # cancelled 2020 championships
        if superevent.year == 2020:
            use_lighter_colors = True

        # cancelled 2021 division championships
        if superevent.year == 2021 and placement.superevent_rank >= 17:
            use_lighter_colors = True

        return use_lighter_colors

    def _setup_diagram_layout(self, num_superevents, top_positions):
        """Setup the diagram layout and return layout parameters"""
        # Get the most recent superevents
        superevents = sorted(self.data.columns, key=lambda x: (x.year, x.order_in_year))
        if len(superevents) > num_superevents:
            superevents = superevents[-num_superevents:]

        # Get all participants that appear in top positions
        top_participants = set()
        for superevent in superevents:
            superevent_data = self.data[superevent]
            for participant, placement in superevent_data.items():
                if not pd.isna(placement) and placement.four_year_rank <= top_positions:
                    top_participants.add(participant)

        # --- Layout parameters ---
        num_cols = len(superevents)
        num_rows = top_positions

        # Make flags much larger to fill the image
        flag_width = 45.0
        flag_height = flag_width * (2 / 3)  # 3:2 aspect ratio

        # Apply correct spacing: 25% of flag width horizontally, 100% of flag height vertically
        horizontal_spacing = flag_width * 0.25
        vertical_spacing = flag_height

        # Calculate total dimensions
        total_width = num_cols * flag_width + (num_cols - 1) * horizontal_spacing
        total_height = num_rows * flag_height + (num_rows - 1) * vertical_spacing

        # Create figure with size proportional to content
        # Each column should be the same width, each row the same height
        # Calculate figure size based on the number of columns and rows
        # Use the same scale factor as the default 20x10 diagram
        default_cols = 20
        default_rows = 10
        default_fig_width = 20
        default_fig_height = 12

        # Calculate scale factors from default
        col_width_inches = default_fig_width / default_cols
        row_height_inches = default_fig_height / default_rows

        # Apply same scale to current dimensions
        fig_width = num_cols * col_width_inches
        fig_height = num_rows * row_height_inches

        _, ax = plt.subplots(figsize=(fig_width, fig_height))

        # Set axis limits - properly center the content
        ax.set_xlim(-flag_width / 2, total_width - flag_width / 2)
        ax.set_ylim(total_height - flag_height / 2, -flag_height / 2)  # Reverse y-axis: best at top

        return (
            superevents,
            top_participants,
            num_cols,
            num_rows,
            flag_width,
            flag_height,
            horizontal_spacing,
            vertical_spacing,
            total_width,
            total_height,
            ax,
        )

    def _setup_background_and_grid(
        self, ax, superevents, num_rows, flag_width, flag_height, horizontal_spacing, vertical_spacing, total_height
    ):
        """Setup background colors and grid lines"""
        # Set background colors for columns
        for col_idx, superevent in enumerate(superevents):
            if isinstance(superevent, OlympicGames):
                bg_color = "#f0f0f0"  # Darker grey for Olympic columns
            else:
                bg_color = "#e0e0e0"  # Darker grey for non-Olympic columns

            # Calculate column position - align background with flag boundaries
            # Flags are centered at col_x, with padding and borders
            col_x = col_idx * (flag_width + horizontal_spacing)
            # Account for flag padding (0.1) and borders
            flag_padding = flag_width * 0.0  # pad=0 means no padding
            border_width = 1  # linewidth=1

            rect = patches.Rectangle(
                (col_x - flag_width / 2 - horizontal_spacing / 2, -flag_height / 2 - flag_padding - border_width),
                flag_width + horizontal_spacing + 2 * flag_padding + 2 * border_width,
                total_height + flag_height + 2 * flag_padding + 2 * border_width,
                facecolor=bg_color,
                edgecolor="none",
                zorder=0,  # Remove edge lines
            )
            ax.add_patch(rect)

        # Add thin grey horizontal lines to help track ranks
        for row_idx in range(num_rows):
            y_pos = row_idx * (flag_height + vertical_spacing)
            ax.axhline(y=y_pos, color="#888888", linewidth=1.0, alpha=0.7, zorder=0, xmin=0, xmax=1)

    def _setup_labels_and_title(
        self, ax, superevents, num_cols, num_rows, flag_width, flag_height, horizontal_spacing, vertical_spacing
    ):
        """Setup axis labels and title"""
        # Set labels: superevent tags above diagram
        xticks = [i * (flag_width + horizontal_spacing) for i in range(num_cols)]
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{s.year}{'O' if isinstance(s, OlympicGames) else ''}" for s in superevents], fontsize=12)
        ax.xaxis.set_label_position("top")
        ax.xaxis.tick_top()

        # Set y labels: 1 (top) to N (bottom)
        yticks = [i * (flag_height + vertical_spacing) for i in range(num_rows)]
        ax.set_yticks(yticks)
        ax.set_yticklabels(range(1, num_rows + 1), fontsize=12)

        # Add position tags on the right side as well
        ax2 = ax.twinx()
        ax2.set_yticks(yticks)
        ax2.set_yticklabels(range(1, num_rows + 1), fontsize=12)
        # Ensure the same y-axis limits and direction as the primary axis
        ax2.set_ylim(ax.get_ylim())
        ax2.spines["top"].set_visible(False)
        ax2.spines["bottom"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.grid(False)

        # Set title above everything
        plt.title("Reconstructed IIHF ranking", fontsize=18, fontweight="bold", pad=40)

        # Remove axis spines
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Remove grid
        ax.grid(False)

    def generate_diagram(
        self,
        output_path: str = "iihf/Reconstructed IIHF ranking.png",
        num_superevents: int = 20,
        top_positions: int = 10,
    ) -> None:
        """Generate the ranking flow diagram"""
        # Setup layout and get parameters
        (
            superevents,
            top_participants,
            num_cols,
            num_rows,
            flag_width,
            flag_height,
            horizontal_spacing,
            vertical_spacing,
            _total_width,
            total_height,
            ax,
        ) = self._setup_diagram_layout(num_superevents, top_positions)

        # Setup background and grid
        self._setup_background_and_grid(
            ax, superevents, num_rows, flag_width, flag_height, horizontal_spacing, vertical_spacing, total_height
        )

        # Draw connecting lines first (behind flags)
        self._draw_connecting_lines(
            ax,
            superevents,
            top_participants,
            top_positions,
            flag_width,
            flag_height,
            horizontal_spacing,
            vertical_spacing,
        )

        # Draw flags
        self._draw_flags(
            ax,
            superevents,
            top_participants,
            top_positions,
            flag_width,
            flag_height,
            horizontal_spacing,
            vertical_spacing,
        )

        # Setup labels and title
        self._setup_labels_and_title(
            ax, superevents, num_cols, num_rows, flag_width, flag_height, horizontal_spacing, vertical_spacing
        )

        # Adjust layout and save
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

    def _draw_connecting_lines(
        self,
        ax,
        superevents,
        top_participants,
        top_positions,
        flag_width,
        flag_height,
        horizontal_spacing,
        vertical_spacing,
    ):
        """Draw lines connecting flags for the same participant across superevents"""
        for participant in top_participants:
            line_points = []

            # Collect all points for this participant (including those outside displayed range)
            for col_idx, superevent in enumerate(superevents):
                superevent_data = self.data[superevent]
                if participant in superevent_data:
                    placement = superevent_data[participant]
                    if not pd.isna(placement) and placement.four_year_rank != float("inf"):
                        # Calculate flag center position
                        x = col_idx * (flag_width + horizontal_spacing)
                        y = (placement.four_year_rank - 1) * (flag_height + vertical_spacing)
                        line_points.append((col_idx, x, y, placement.four_year_rank, superevent.year))

            # Draw lines with new logic
            if len(line_points) > 1:
                line_color = participant.line_color
                if pd.isna(line_color) or not line_color:
                    line_color = "black"
                for i in range(len(line_points) - 1):
                    col1, x1, y1, rank1, year1 = line_points[i]
                    col2, x2, y2, rank2, year2 = line_points[i + 1]

                    # Connect if the superevents are consecutive (no gaps)
                    if col2 - col1 == 1:
                        # Determine line style based on year gap
                        year_gap = year2 - year1
                        if year_gap <= 4:
                            linestyle = "solid"
                        else:
                            linestyle = "dotted"

                        # Check if we should draw this line segment
                        should_draw = True

                        # If both ranks are outside displayed range, don't draw
                        if rank1 > top_positions and rank2 > top_positions:
                            should_draw = False

                        if should_draw:
                            # Calculate line endpoints - use actual positions
                            start_x, start_y = x1, y1
                            end_x, end_y = x2, y2

                            # If rank1 is outside displayed range, start at the boundary
                            if rank1 > top_positions:
                                # Calculate the actual trajectory direction
                                dx = end_x - start_x
                                dy = end_y - start_y

                                # Find where this line intersects the boundary
                                boundary_y = (top_positions - 1) * (flag_height + vertical_spacing) + flag_height / 2

                                # Calculate the intersection point
                                if dy != 0:  # Avoid division by zero
                                    t = (boundary_y - start_y) / dy
                                    if 0 <= t <= 1:  # Only if intersection is within the line segment
                                        start_x = start_x + t * dx
                                        start_y = boundary_y

                            # If rank2 is outside displayed range, end at the boundary
                            # but maintain the direction by interpolating the line
                            if rank2 > top_positions:
                                # Calculate the actual trajectory direction
                                dx = end_x - start_x
                                dy = end_y - start_y

                                # Find where this line intersects the boundary
                                boundary_y = (top_positions - 1) * (flag_height + vertical_spacing) + flag_height / 2

                                # Calculate the intersection point
                                if dy != 0:  # Avoid division by zero
                                    t = (boundary_y - start_y) / dy
                                    if 0 <= t <= 1:  # Only if intersection is within the line segment
                                        end_x = start_x + t * dx
                                        end_y = boundary_y

                            ax.plot(
                                [start_x, end_x],
                                [start_y, end_y],
                                color=line_color,
                                linewidth=4,
                                linestyle=linestyle,
                                zorder=1,
                            )

    def _process_single_flag(
        self,
        ax,
        col_idx,
        superevent,
        participant,
        placement,
        top_positions,
        flag_width,
        flag_height,
        horizontal_spacing,
        vertical_spacing,
        superevents,
    ):
        """Process and draw a single flag"""
        # Check if this is a new participant (didn't have valid four-year ranking in previous superevent)
        is_new_participant = False
        if col_idx > 0:
            prev_superevent = superevents[col_idx - 1]
            prev_superevent_data = self.data[prev_superevent]
            if participant in prev_superevent_data:
                prev_placement = prev_superevent_data[participant]
                # Check if participant had no valid four-year ranking in previous superevent
                if (
                    pd.isna(prev_placement)
                    or prev_placement.four_year_rank == float("inf")
                    or prev_placement.four_year_rank > top_positions
                ):
                    is_new_participant = True
            else:
                # Participant wasn't in previous superevent at all
                is_new_participant = True
        else:
            # First superevent in the diagram, so it's a new participant
            is_new_participant = True

        # Get event participant for flag selection
        event_participant = None
        if placement.event_participant_code:
            event_participant = Participant.get_participant(placement.event_participant_code)

        try:
            # Get flag path
            if event_participant:
                # Use event participant's flag
                flag_path = self._get_flag_path(event_participant.name_en, superevent.year)
                base_use_lighter_colors = False
            else:
                # Use series participant's flag with lighter colors
                flag_path = self._get_flag_path(participant.name_en, superevent.year)
                base_use_lighter_colors = True

            # Get participant name for bleaching rules
            participant_name = event_participant.name_en if event_participant else participant.name_en

            # Apply special bleaching rules
            use_lighter_colors = self._should_use_lighter_colors(
                participant_name, superevent, placement, base_use_lighter_colors
            )

            # Load and resize flag
            flag_img = self._load_and_resize_flag(flag_path, flag_width, flag_height)

            # Apply lighter colors if needed
            if use_lighter_colors:
                flag_img = self._make_flag_lighter(flag_img)

            # Calculate position based on series participant's four-year ranking
            x = col_idx * (flag_width + horizontal_spacing)
            y = (placement.four_year_rank - 1) * (flag_height + vertical_spacing)

            # Determine border properties based on whether this is a new participant
            if is_new_participant:
                border_color = "white"
                border_width = 8
            else:
                border_color = "black"
                border_width = 1

            # Create offset image
            im = OffsetImage(flag_img, zoom=1.0)
            ab = AnnotationBbox(
                im,
                (x, y),
                frameon=True,
                bboxprops={"edgecolor": border_color, "linewidth": border_width},
                pad=0,
            )
            ax.add_artist(ab)

        except Exception as e:
            print(
                f"Error processing flag for {event_participant.name_en if event_participant else participant.name_en} in {superevent.year}: {e}"
            )
            raise

    def _draw_flags(
        self,
        ax,
        superevents,
        top_participants,
        top_positions,
        flag_width,
        flag_height,
        horizontal_spacing,
        vertical_spacing,
    ):
        """Draw flags for each placement"""
        for col_idx, superevent in enumerate(superevents):
            superevent_data = self.data[superevent]

            for participant, placement in superevent_data.items():
                if participant not in top_participants:
                    continue

                # Check if series participant has a valid four-year ranking
                if (
                    pd.isna(placement)
                    or placement.four_year_rank == float("inf")
                    or placement.four_year_rank > top_positions
                ):
                    continue

                # Process and draw the flag
                self._process_single_flag(
                    ax,
                    col_idx,
                    superevent,
                    participant,
                    placement,
                    top_positions,
                    flag_width,
                    flag_height,
                    horizontal_spacing,
                    vertical_spacing,
                    superevents,
                )


def main():
    """Main function to generate the ranking diagram"""
    # Load data first to determine maximum values
    data = load_data("iihf/data.ods")

    # Default values
    num_superevents = 20
    top_positions = 10

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "all":
            # Use all available superevents
            num_superevents = len(data.columns)
        else:
            try:
                num_superevents = int(sys.argv[1])
            except ValueError:
                print(f"Invalid number of superevents: {sys.argv[1]}")
                return

    if len(sys.argv) > 2:
        if sys.argv[2].lower() == "all":
            # Determine the maximum number of positions in the data
            max_rank = 0
            for col in data.columns:
                for placement in data[col].values:
                    if not pd.isna(placement) and hasattr(placement, "four_year_rank"):
                        if placement.four_year_rank and placement.four_year_rank != float("inf"):
                            max_rank = max(max_rank, int(placement.four_year_rank))
            top_positions = max_rank
        else:
            try:
                top_positions = int(sys.argv[2])
            except ValueError:
                print(f"Invalid number of top positions: {sys.argv[2]}")
                return

    print(f"Generating diagram with {num_superevents} superevents and top {top_positions} positions...")

    generator = RankingDiagramGenerator()
    generator.generate_diagram(
        output_path="iihf/Reconstructed IIHF ranking.png", num_superevents=num_superevents, top_positions=top_positions
    )


if __name__ == "__main__":
    main()
