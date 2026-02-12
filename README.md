# MLHD2
 Helldivers 2 Mission Log Manager

Downloads
Helldivers 2 Operation Logger
https://github.com/Alreapha/MLHD2/tree/main

Python 3.10.6
https://www.python.org/downloads/release/python-3106/

pip 22.2.1 (Any Version Should Work)
https://pypi.org/project/pip/22.2.1/

Dependencies
Open Terminal
cd into HD2 Operation Logger directory (where the location of your download is for the program) Alternatively you can right click your file explorer window and select "Open in Terminal"
Run pip install -r .\requirements.txt
Double Click main.py to run HD2 Operation Logger

config.config
DISCORD_CLIENT_ID
You shouldn't ever have to edit this client ID, however it's here in case you do need it.

Excel Location
PROD is the main name of your spreadsheet where you can see all of your mission logs in one place on your device
TEST is not important and you shouldn't need to touch this unless you're exploring the insides of the program yourself or are guided as a tester

Webhooks
PROD is the main webhook that will link to our server, if you wish you can create your own webhook link and have it also upload to your own server by:
https://discord.com/our-link,https://discord.com/your-link
TEST is not important and you shouldn't need to touch this unless you're exploring the insides of the program yourself or are guided as a tester

EnemyIcons, DifficultyIcons, Stars
These will only be important if you add your own Webhook link as the emojis in the embed may not function correctly in your own server

SystemColors
You do not need to touch these at all, these are references only

If you know how, you can make a .bat file for easier use instead of running the main.py, and you can then turn this into a desktop shortcut to treat it like an .exe
Due to current restrictions, we're unable to make this an exe ourselves at this time


## Overview
Utility for recording, aggregating, and sharing in‑game mission run data. It captures results, enriches them (enemy type, difficulty, performance metrics), stores them locally (spreadsheet) and optionally relays structured embeds to one or more Discord channels via webhooks.

## Goals
- Centralize personal or group mission history.
- Provide quick performance at-a-glance (stars, difficulty, factions, outcomes).
- Enable lightweight team collaboration through automated Discord posts.
- Maintain exportable structured data for external analysis.

## Key Capabilities
- Local log persistence in a primary workbook (production sheet).
- Optional secondary/testing sheet for experimentation.
- Automated Discord embed generation (supports multiple webhooks).
- Icon + color mapping for enemies, difficulty tiers, and rating stars.
- Minimal local configuration (single config file).
- Runs with a standard Python interpreter (no compiled binary required).

## How It Works (Conceptual Flow)
1. User launches the script.
2. Mission completion data is gathered / parsed.
3. Data normalized and appended to the production sheet.
4. Embed payload constructed (icons, colors, fields).
5. Payload dispatched to each configured webhook URL.
6. Local assets (icon references, colors) provide consistent styling.

## Quick Start (After Dependencies Installed)
1. Adjust configuration file only if custom behavior is required (custom asset references).
2. Launch the main script (double click or run via interpreter).
3. Perform missions; each completion appends a new structured entry.
4. Verify Discord channel receives embeds (if a custom webhook was added).

## Configuration Concepts
- Client identifier: Leave default unless instructed otherwise.
- Workbook names: One primary sheet for real logs; optional secondary sheet for safe testing.
- Webhook list: Comma-separated URLs; first treated as primary, subsequent ones receive the same payload.
- Asset sections (icons, colors): Provide stable look; alter only if hosting in a server lacking the original emojis.
- Style/color mappings: Pure reference values; do not modify unless re-theming.

## Adding A Personal Discord Channel
1. Create a new webhook in the target channel.
2. Insert the URL after the existing primary, separated by a comma.
3. Restart the application so the list is re-read.

Example format (conceptual):
https://discord.com/primary,...additional webhook URLs...

## Spreadsheet Guidance
- Keep the production sheet name unchanged for seamless operation.
- Avoid manual edits to header rows (could break parsing/order assumptions).
- For analysis, copy data into a separate workbook before heavy manipulation.

## Automation Tips
- (Optional) Create a small launcher script or batch file invoking: python main.py
- Place a shortcut to the launcher on the desktop for faster access.

## Troubleshooting
- No Discord posts: Re-check webhook list syntax (no stray spaces), internet access, and that the URLs are valid.
- Missing icons/emojis: Server lacks required custom assets; either upload equivalents or simplify embed fields.
- Spreadsheet not updating: Confirm write permissions and that the file is not open in exclusive-lock mode.
- Import errors: Re-install requirements with the package manager and ensure the correct Python version is active in PATH.

## Data & Privacy
All logging occurs locally first; outbound data is limited to what is included in the webhook embed. Avoid adding personal identifiers if privacy is a concern.

## Contributing
Report issues or propose enhancements via the repository issue tracker. Provide:
- Environment (OS, Python version)
- Steps to reproduce
- Expected vs actual behavior
- Relevant stack trace (if any)

## Disclaimer
Not affiliated with the game publisher. Use at own risk. Respect any applicable game terms of service.

## License
Refer to the repository for license details.

## Summary
A lightweight, configurable mission logging and Discord dissemination tool focusing on data organization, shareability, and minimal user friction. Configure once, then launch and play.

## Developer Quality Gates
- Install dev tooling: `pip install -r requirements-dev.txt`
- Run lint/type/tests:
	- `ruff check .`
	- `ruff format --check .`
	- `mypy`
	- `pytest -q tests`
- Optional local hooks: `pre-commit install`

## Build and Release Docs
- Build/distribution flow: `docs/BUILD_AND_DISTRIBUTION.md`
- Reproducible release checklist: `docs/RELEASE_CHECKLIST.md`

## Diagnostics Dump (Optional)
Issue-report diagnostics can be generated using:

`from core.data.diagnostics import generate_diagnostics_dump; print(generate_diagnostics_dump())`
